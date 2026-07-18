#!/usr/bin/env node
'use strict';

const crypto = require('crypto');
const fs = require('fs');
const path = require('path');

function fail(message, code = 2) {
  process.stderr.write(`Ошибка: ${message}\n`);
  process.exit(code);
}

function parseArgs(argv) {
  const out = { url: '', dataset: '', revision: 'main', output: '', preflight: false };
  for (let i = 2; i < argv.length; i += 1) {
    const token = argv[i];
    const value = () => {
      if (i + 1 >= argv.length) fail(`для ${token} не указано значение`);
      i += 1;
      return argv[i];
    };
    if (token === '--url') out.url = value();
    else if (token === '--dataset') out.dataset = value();
    else if (token === '--revision') out.revision = value();
    else if (token === '--output') out.output = value();
    else if (token === '--preflight') out.preflight = true;
    else if (token === '--help' || token === '-h') {
      process.stdout.write('Использование: inventory.js (--url URL | --dataset ORG/NAME) [--output RELATIVE_FILE] [--revision REV] [--preflight]\n');
      process.exit(0);
    } else fail(`неизвестный аргумент ${token}`);
  }
  if ((!out.url && !out.dataset) || (out.url && out.dataset)) {
    fail('нужно указать ровно один параметр: --url или --dataset');
  }
  if (!out.preflight && !out.output) fail('обязателен параметр --output');
  if (!/^[A-Za-z0-9._~%+\/-]+$/.test(out.revision)) fail('недопустимая ревизия');
  return out;
}

function stateRoot() {
  const raw = String(process.env.OUROBOROS_SKILL_STATE_DIR || '').trim();
  if (!raw) fail('OUROBOROS_SKILL_STATE_DIR не задан; запускайте entry через skill_exec');
  return path.resolve(raw);
}

function confinedOutput(raw) {
  const root = stateRoot();
  const output = path.isAbsolute(raw) ? path.resolve(raw) : path.resolve(root, raw);
  const relative = path.relative(root, output);
  if (!relative || relative === '..' || relative.startsWith(`..${path.sep}`) || path.isAbsolute(relative)) {
    fail('output должен находиться внутри каталога состояния скилла');
  }
  return output;
}

function parseDatasetUrl(raw) {
  let url;
  try { url = new URL(raw); } catch (_) { fail('некорректный URL'); }
  if (!['huggingface.co', 'www.huggingface.co'].includes(url.hostname.toLowerCase())) {
    fail('разрешены только ссылки huggingface.co');
  }
  if (url.protocol !== 'https:') fail('разрешён только HTTPS');
  const parts = url.pathname.split('/').filter(Boolean);
  if (parts[0] !== 'datasets' || parts.length < 3) {
    fail('ожидалась ссылка вида https://huggingface.co/datasets/<org>/<name>');
  }
  const dataset = `${decodeURIComponent(parts[1])}/${decodeURIComponent(parts[2])}`;
  let revision = 'main';
  if (parts[3] === 'tree' && parts[4]) revision = decodeURIComponent(parts.slice(4).join('/'));
  return { dataset, revision };
}

function validateDatasetId(value) {
  const dataset = String(value || '').trim();
  if (!/^[A-Za-z0-9._-]+\/[A-Za-z0-9._-]+$/.test(dataset)) fail('некорректный id датасета');
  return dataset;
}

async function fetchJson(url, label) {
  const response = await fetch(url, {
    redirect: 'follow',
    headers: { Accept: 'application/json', 'User-Agent': 'Mozaika-HF-Inventory/1.0' },
    signal: AbortSignal.timeout(60000),
  });
  if (!response.ok) {
    const detail = (await response.text()).slice(0, 300).replace(/\s+/g, ' ');
    throw new Error(`${label}: HTTP ${response.status}${detail ? ` — ${detail}` : ''}`);
  }
  return response.json();
}

function normalizedSibling(entry, index) {
  const filename = String(entry.rfilename || entry.path || '').trim();
  return {
    child_id: `repo-${String(index + 1).padStart(4, '0')}`,
    kind: 'repository_file',
    path: filename,
    size_bytes: Number.isFinite(entry.size) ? entry.size : null,
    blob_id: entry.blobId || null,
    lfs_sha256: entry.lfs && entry.lfs.sha256 ? entry.lfs.sha256 : null,
  };
}

function normalizedParquet(entry, index) {
  const url = String(entry.url || '').trim();
  if (!url) return null;
  let parsed;
  try { parsed = new URL(url); } catch (_) { return null; }
  if (parsed.protocol !== 'https:' || !['huggingface.co', 'www.huggingface.co', 'datasets-server.huggingface.co'].includes(parsed.hostname.toLowerCase())) return null;
  return {
    child_id: `parquet-${String(index + 1).padStart(4, '0')}`,
    kind: 'parquet_conversion',
    config: entry.config || entry.subset || null,
    split: entry.split || null,
    url,
    filename: entry.filename || path.posix.basename(parsed.pathname),
    size_bytes: Number.isFinite(entry.size) ? entry.size : null,
  };
}

async function main() {
  const args = parseArgs(process.argv);
  const output = args.preflight ? null : confinedOutput(args.output);
  const fromUrl = args.url ? parseDatasetUrl(args.url) : null;
  const dataset = validateDatasetId(fromUrl ? fromUrl.dataset : args.dataset);
  const revision = fromUrl && args.revision === 'main' ? fromUrl.revision : args.revision;

  const encodedDataset = dataset.split('/').map(encodeURIComponent).join('/');
  const metadataUrl = revision === 'main'
    ? `https://huggingface.co/api/datasets/${encodedDataset}`
    : `https://huggingface.co/api/datasets/${encodedDataset}/revision/${encodeURIComponent(revision)}`;
  const parquetUrl = `https://datasets-server.huggingface.co/parquet?dataset=${encodeURIComponent(dataset)}`;

  if (args.preflight) {
    await fetchJson(metadataUrl, 'предварительная проверка Hub');
    process.stdout.write(`${JSON.stringify({ ok: true, preflight: true, dataset_id: dataset, revision })}\n`);
    return;
  }

  const metadata = await fetchJson(metadataUrl, 'метаданные Hub');
  let parquetPayload = { parquet_files: [], pending: [], failed: [] };
  let parquetStatus = 'available';
  try {
    parquetPayload = await fetchJson(parquetUrl, 'Parquet API');
  } catch (error) {
    parquetStatus = 'unavailable';
    parquetPayload = { parquet_files: [], pending: [], failed: [], error: error.message };
  }

  const siblings = (Array.isArray(metadata.siblings) ? metadata.siblings : [])
    .map(normalizedSibling)
    .filter((entry) => entry.path);
  const parquetFiles = (Array.isArray(parquetPayload.parquet_files) ? parquetPayload.parquet_files : [])
    .map(normalizedParquet)
    .filter((entry) => entry && entry.url);

  const inventory = {
    contract_version: 'mozaika-huggingface-inventory/v1',
    generated_at: new Date().toISOString(),
    source: {
      provider: 'huggingface',
      dataset_id: dataset,
      requested_revision: revision,
      resolved_commit_sha: metadata.sha || null,
      canonical_url: `https://huggingface.co/datasets/${dataset}/tree/${encodeURIComponent(revision)}`,
      private: Boolean(metadata.private),
      gated: metadata.gated || false,
    },
    coverage: {
      repository_files: siblings.length,
      parquet_children: parquetFiles.length,
      parquet_status: parquetStatus,
      parquet_pending: Array.isArray(parquetPayload.pending) ? parquetPayload.pending : [],
      parquet_failed: Array.isArray(parquetPayload.failed) ? parquetPayload.failed : [],
    },
    repository_files: siblings,
    parquet_children: parquetFiles,
    provenance: {
      metadata_api: metadataUrl,
      parquet_api: parquetUrl,
    },
  };

  fs.mkdirSync(path.dirname(output), { recursive: true });
  const bytes = Buffer.from(`${JSON.stringify(inventory, null, 2)}\n`, 'utf8');
  fs.writeFileSync(output, bytes, { flag: 'wx', mode: 0o600 });
  const sha256 = crypto.createHash('sha256').update(bytes).digest('hex');
  process.stdout.write(`${JSON.stringify({ ok: true, output, sha256, dataset_id: dataset, repository_files: siblings.length, parquet_children: parquetFiles.length })}\n`);
}

main().catch((error) => fail(error && error.message ? error.message : String(error), 1));
