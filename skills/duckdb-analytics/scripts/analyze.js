#!/usr/bin/env node
'use strict';

const crypto = require('crypto');
const fs = require('fs');
const path = require('path');
let DuckDBConnection;
try { ({ DuckDBConnection } = require('@duckdb/node-api')); }
catch (error) {
  process.stderr.write(`Ошибка: изолированная зависимость @duckdb/node-api недоступна: ${error.message}\n`);
  process.exit(2);
}

const FORMATS = new Set(['csv', 'tsv', 'json', 'jsonl', 'parquet']);
const REMOTE_HOSTS = new Set(['huggingface.co', 'www.huggingface.co', 'datasets-server.huggingface.co']);
const NUMERIC_TYPE = /^(TINYINT|SMALLINT|INTEGER|BIGINT|HUGEINT|UTINYINT|USMALLINT|UINTEGER|UBIGINT|FLOAT|DOUBLE|DECIMAL)/i;
const FORBIDDEN_SQL = /\b(ALTER|ATTACH|CALL|CHECKPOINT|COMMENT|COPY|CREATE|DELETE|DETACH|DROP|EXPORT|IMPORT|INSERT|INSTALL|LOAD|MERGE|PRAGMA|REPLACE|SET|UPDATE|USE|VACUUM|read_csv|read_csv_auto|read_json|read_json_auto|read_ndjson|read_parquet|read_text|read_blob|glob|query|query_table|getenv)\b/i;

function fail(message, code = 2) {
  process.stderr.write(`Ошибка: ${message}\n`);
  process.exit(code);
}

function runtimeRoots() {
  const raw = String(process.env.OUROBOROS_SKILL_STATE_DIR || '').trim();
  if (!raw) fail('OUROBOROS_SKILL_STATE_DIR не задан; запускайте entry через skill_exec');
  const state = path.resolve(raw);
  return { state, data: path.resolve(state, '..', '..', '..') };
}

function confinedPath(root, candidate, label) {
  const resolved = path.resolve(candidate);
  const relative = path.relative(root, resolved);
  if (!relative || relative === '..' || relative.startsWith(`..${path.sep}`) || path.isAbsolute(relative)) {
    fail(`${label} должен находиться внутри разрешённого каталога Ouroboros`);
  }
  return resolved;
}

function parseArgs(argv) {
  let request = '';
  for (let i = 2; i < argv.length; i += 1) {
    if (argv[i] === '--request') request = argv[++i] || '';
    else if (argv[i] === '--help' || argv[i] === '-h') {
      process.stdout.write('Использование: analyze.js --request /absolute/request.json\n');
      process.exit(0);
    } else fail(`неизвестный аргумент ${argv[i]}`);
  }
  if (!request) fail('обязателен параметр --request');
  return confinedPath(runtimeRoots().data, request, 'request');
}

function readJson(filename) {
  let value;
  try { value = JSON.parse(fs.readFileSync(filename, 'utf8')); }
  catch (error) { fail(`не удалось прочитать JSON ${filename}: ${error.message}`); }
  return value;
}

function quoteIdentifier(value) {
  return `"${String(value).replace(/"/g, '""')}"`;
}

function quoteString(value) {
  return `'${String(value).replace(/'/g, "''")}'`;
}

function normalizedSource(source, requestDir, dataRoot) {
  if (!source || typeof source !== 'object') fail('каждый source должен быть объектом');
  const sourceId = String(source.source_id || '').trim();
  if (!/^[A-Za-z][A-Za-z0-9_]{0,62}$/.test(sourceId)) {
    fail(`некорректный source_id: ${sourceId || '<пусто>'}`);
  }
  const format = String(source.format || '').toLowerCase();
  if (!FORMATS.has(format)) fail(`источник ${sourceId}: формат ${format || '<пусто>'} не поддерживается`);
  const rawLocation = String(source.location || '').trim();
  if (!rawLocation) fail(`источник ${sourceId}: не указан location`);
  let location;
  let remote = false;
  if (/^https?:\/\//i.test(rawLocation)) {
    let url;
    try { url = new URL(rawLocation); } catch (_) { fail(`источник ${sourceId}: некорректный URL`); }
    if (url.protocol !== 'https:' || !REMOTE_HOSTS.has(url.hostname.toLowerCase())) {
      fail(`источник ${sourceId}: удалённые чтения разрешены только с официальных HTTPS-хостов Hugging Face`);
    }
    location = url.toString();
    remote = true;
  } else {
    location = confinedPath(dataRoot, path.resolve(requestDir, rawLocation), `источник ${sourceId}`);
    if (!fs.existsSync(location) || !fs.statSync(location).isFile()) fail(`источник ${sourceId}: файл не найден`);
  }
  return { source_id: sourceId, format, location, remote };
}

function readerExpression(source) {
  const location = quoteString(source.location);
  if (source.format === 'parquet') return `read_parquet(${location}, union_by_name=true)`;
  if (source.format === 'csv') return `read_csv_auto(${location}, header=true, sample_size=-1)`;
  if (source.format === 'tsv') return `read_csv_auto(${location}, header=true, delim='\\t', sample_size=-1)`;
  if (source.format === 'jsonl') return `read_json_auto(${location}, format='newline_delimited')`;
  return `read_json_auto(${location})`;
}

function validateQuery(query, sourceIds) {
  if (!query || typeof query !== 'object') fail('каждый query должен быть объектом');
  const queryId = String(query.query_id || '').trim();
  if (!/^[A-Za-z][A-Za-z0-9_-]{0,63}$/.test(queryId)) fail(`некорректный query_id: ${queryId || '<пусто>'}`);
  const sql = String(query.sql || '').trim();
  if (!sql || sql.length > 50000) fail(`запрос ${queryId}: SQL пуст или слишком велик`);
  if (!/^(SELECT|WITH)\b/i.test(sql)) fail(`запрос ${queryId}: разрешены только SELECT или WITH`);
  if (sql.includes(';') || /--|\/\*/.test(sql)) fail(`запрос ${queryId}: комментарии и несколько statements запрещены`);
  if (FORBIDDEN_SQL.test(sql)) fail(`запрос ${queryId}: обнаружена запрещённая операция`);
  if (sourceIds.size === 0) fail(`запрос ${queryId}: нет зарегистрированных источников`);
  return { query_id: queryId, sql };
}

async function rows(connection, sql) {
  const reader = await connection.runAndReadAll(sql);
  return reader.getRowObjectsJson();
}

async function sourceFingerprint(source) {
  if (source.remote) return { sha256: null, size_bytes: null };
  const stat = fs.statSync(source.location);
  const hash = crypto.createHash('sha256');
  await new Promise((resolve, reject) => {
    const stream = fs.createReadStream(source.location);
    stream.on('data', (chunk) => hash.update(chunk));
    stream.on('end', resolve);
    stream.on('error', reject);
  });
  return { sha256: hash.digest('hex'), size_bytes: stat.size };
}

async function profileSource(connection, source) {
  const view = quoteIdentifier(source.source_id);
  const schema = await rows(connection, `DESCRIBE SELECT * FROM ${view}`);
  const countResult = await rows(connection, `SELECT COUNT(*)::BIGINT AS row_count FROM ${view}`);
  const duplicateResult = await rows(connection, `SELECT (COUNT(*) - (SELECT COUNT(*) FROM (SELECT DISTINCT * FROM ${view})))::BIGINT AS duplicate_rows FROM ${view}`);
  const columns = [];
  for (const item of schema) {
    const name = String(item.column_name);
    const type = String(item.column_type || 'UNKNOWN');
    const column = quoteIdentifier(name);
    const summary = await rows(connection, `SELECT COUNT(*)::BIGINT AS rows, COUNT(${column})::BIGINT AS non_null, COUNT(DISTINCT ${column})::BIGINT AS distinct_count FROM ${view}`);
    const base = summary[0] || {};
    const output = {
      name,
      type,
      rows: base.rows ?? null,
      non_null: base.non_null ?? null,
      null_count: base.rows != null && base.non_null != null ? String(BigInt(base.rows) - BigInt(base.non_null)) : null,
      distinct_count: base.distinct_count ?? null,
    };
    if (NUMERIC_TYPE.test(type)) {
      const numeric = await rows(connection, `SELECT MIN(${column}) AS min, MAX(${column}) AS max, AVG(${column}) AS mean, MEDIAN(${column}) AS median, STDDEV_SAMP(${column}) AS stddev FROM ${view}`);
      Object.assign(output, numeric[0] || {});
    }
    columns.push(output);
  }
  return {
    source_id: source.source_id,
    location: source.location,
    format: source.format,
    remote: source.remote,
    fingerprint: await sourceFingerprint(source),
    row_count: countResult[0] ? countResult[0].row_count : null,
    duplicate_rows: duplicateResult[0] ? duplicateResult[0].duplicate_rows : null,
    columns,
  };
}

async function main() {
  const roots = runtimeRoots();
  const requestPath = parseArgs(process.argv);
  const request = readJson(requestPath);
  if (!request || request.contract_version !== 'mozaika-duckdb-request/v1') fail('неверный contract_version');
  if (!Array.isArray(request.sources) || request.sources.length === 0 || request.sources.length > 200) {
    fail('sources должен содержать от 1 до 200 элементов');
  }
  const requestDir = path.dirname(requestPath);
  const sources = request.sources.map((source) => normalizedSource(source, requestDir, roots.data));
  const sourceIds = new Set(sources.map((source) => source.source_id));
  if (sourceIds.size !== sources.length) fail('source_id должны быть уникальны');
  const queries = Array.isArray(request.queries) ? request.queries.map((query) => validateQuery(query, sourceIds)) : [];
  if (queries.length > 50) fail('разрешено не более 50 запросов');

  if (!request.output) fail('обязателен output');
  const rawOutput = String(request.output);
  const output = confinedPath(roots.state, path.isAbsolute(rawOutput) ? rawOutput : path.resolve(roots.state, rawOutput), 'output');
  if (fs.existsSync(output)) fail(`выходной файл уже существует: ${output}`);
  fs.mkdirSync(path.dirname(output), { recursive: true });

  const connection = await DuckDBConnection.create();
  for (const source of sources) {
    await connection.run(`CREATE TEMP VIEW ${quoteIdentifier(source.source_id)} AS SELECT * FROM ${readerExpression(source)}`);
  }

  const profiles = [];
  for (const source of sources) profiles.push(await profileSource(connection, source));
  const queryResults = [];
  for (const query of queries) {
    const result = await rows(connection, query.sql);
    queryResults.push({ query_id: query.query_id, sql: query.sql, row_count: result.length, rows: result });
  }

  const payload = {
    contract_version: 'mozaika-duckdb-result/v1',
    generated_at: new Date().toISOString(),
    engine: { name: '@duckdb/node-api', language: 'node', python_used: false },
    profiles,
    query_results: queryResults,
  };
  const bytes = Buffer.from(`${JSON.stringify(payload, null, 2)}\n`, 'utf8');
  fs.writeFileSync(output, bytes, { flag: 'wx', mode: 0o600 });
  const sha256 = crypto.createHash('sha256').update(bytes).digest('hex');
  process.stdout.write(`${JSON.stringify({ ok: true, output, sha256, sources: profiles.length, queries: queryResults.length })}\n`);
}

main().catch((error) => fail(error && error.message ? error.message : String(error), 1));
