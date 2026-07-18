#!/usr/bin/env node
'use strict';

const crypto = require('crypto');
const fs = require('fs');
const path = require('path');

const CHART_TYPES = new Set(['interval', 'line', 'point', 'area', 'pie']);
const STATUS = new Set(['neutral', 'good', 'warning', 'critical']);
const QUESTION_STATUS = new Set(['answered', 'partial', 'unanswered']);
const COVERAGE_STATUS = new Set(['covered', 'partial', 'unanswered']);
const TABLE_FORMATS = new Set(['text', 'number', 'percent', 'currency', 'date']);

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
  const out = { spec: '', output: '', cardsOutput: '' };
  for (let i = 2; i < argv.length; i += 1) {
    const token = argv[i];
    if (token === '--spec') out.spec = argv[++i] || '';
    else if (token === '--output') out.output = argv[++i] || '';
    else if (token === '--cards-output') out.cardsOutput = argv[++i] || '';
    else if (token === '--help' || token === '-h') {
      process.stdout.write('Использование: build_dashboard.js --spec FILE --output FILE [--cards-output FILE]\n');
      process.exit(0);
    } else fail(`неизвестный аргумент ${token}`);
  }
  if (!out.spec || !out.output) fail('обязательны --spec и --output');
  const roots = runtimeRoots();
  const outputCandidate = path.isAbsolute(out.output) ? out.output : path.resolve(roots.state, out.output);
  const cardsOutputCandidate = out.cardsOutput
    ? (path.isAbsolute(out.cardsOutput) ? out.cardsOutput : path.resolve(roots.state, out.cardsOutput))
    : '';
  return {
    spec: confinedPath(roots.data, out.spec, 'spec'),
    output: confinedPath(roots.state, outputCandidate, 'output'),
    cardsOutput: cardsOutputCandidate ? confinedPath(roots.state, cardsOutputCandidate, 'cards-output') : '',
  };
}

function readJson(filename) {
  try { return JSON.parse(fs.readFileSync(filename, 'utf8')); }
  catch (error) { fail(`не удалось прочитать JSON ${filename}: ${error.message}`); }
}

function text(value, label, min = 1, max = 2000) {
  const output = String(value == null ? '' : value).trim();
  if (output.length < min || output.length > max) fail(`${label}: недопустимая длина`);
  return output;
}

function stringArray(value, label, min = 0, max = 100) {
  if (!Array.isArray(value) || value.length < min || value.length > max) fail(`${label}: ожидался массив`);
  return value.map((item, index) => text(item, `${label}[${index}]`, 1, 256));
}

function comparisonText(value) {
  return String(value == null ? '' : value)
    .normalize('NFKC')
    .toLocaleLowerCase('ru-RU')
    .replace(/ё/g, 'е')
    .replace(/[^\p{L}\p{N}]+/gu, ' ')
    .trim()
    .replace(/\s+/g, ' ');
}

function tokenSimilarity(left, right) {
  const a = new Set(comparisonText(left).split(' ').filter(Boolean));
  const b = new Set(comparisonText(right).split(' ').filter(Boolean));
  if (a.size < 4 || b.size < 4) return 0;
  let common = 0;
  for (const token of a) if (b.has(token)) common += 1;
  return common / new Set([...a, ...b]).size;
}

function isDuplicateCopy(left, right) {
  const a = comparisonText(left);
  const b = comparisonText(right);
  if (!a || !b) return false;
  if (a === b) return true;
  const shorter = a.length <= b.length ? a : b;
  const longer = a.length <= b.length ? b : a;
  if (shorter.length >= 24 && longer.includes(shorter) && shorter.length / longer.length >= 0.72) return true;
  return tokenSimilarity(a, b) >= 0.82;
}

function assertDistinctCopy(left, right, leftLabel, rightLabel) {
  if (isDuplicateCopy(left, right)) {
    fail(`${leftLabel} и ${rightLabel} повторяют одну формулировку; второе поле должно добавлять новую мысль`);
  }
}

function findG2Bundle() {
  let entry;
  try { entry = require.resolve('@antv/g2'); }
  catch (_) { fail('не найдена изолированная зависимость @antv/g2'); }
  let current = path.dirname(entry);
  while (current !== path.dirname(current)) {
    const packageJson = path.join(current, 'package.json');
    if (fs.existsSync(packageJson)) {
      try {
        const pkg = JSON.parse(fs.readFileSync(packageJson, 'utf8'));
        if (pkg.name === '@antv/g2') break;
      } catch (_) { /* continue */ }
    }
    current = path.dirname(current);
  }
  const candidates = [path.join(current, 'dist', 'g2.min.js'), path.join(current, 'dist', 'g2.js')];
  const bundle = candidates.find((candidate) => fs.existsSync(candidate));
  if (!bundle) fail('в пакете @antv/g2 не найден UMD bundle');
  return fs.readFileSync(bundle, 'utf8').replace(/<\/script/gi, '<\\/script');
}

function validateSpec(raw) {
  if (!raw || raw.contract_version !== 'mozaika-dashboard-spec/v1') fail('неверный contract_version');
  if (raw.surface_policy !== 'separate-dashboard-and-storytelling-cards') {
    fail('surface_policy должен требовать отдельные dashboard и storytelling-cards HTML');
  }
  const spec = {
    title: text(raw.title, 'title', 1, 180),
    subtitle: text(raw.subtitle || 'Проверенная аналитическая поверхность', 'subtitle', 1, 300),
    output_language: text(raw.output_language || 'ru', 'output_language', 2, 12),
    generated_at: text(raw.generated_at || new Date().toISOString(), 'generated_at', 1, 64),
    research_title_verbatim: raw.research_title_verbatim == null ? null : text(raw.research_title_verbatim, 'research_title_verbatim', 1, 180),
    research_questions: [], kpis: [], filters: [], charts: [], tables: [], insights: [], caveats: [], storytelling_cards: [], sources: [],
    customization: {},
    owner_question: '', recommended_option_id: '',
    surface_policy: raw.surface_policy,
  };
  if (spec.research_title_verbatim && !spec.title.includes(spec.research_title_verbatim)) {
    fail('title должен дословно содержать research_title_verbatim');
  }
  const researchQuestions = Array.isArray(raw.research_questions) ? raw.research_questions : [];
  if (researchQuestions.length > 30) fail('разрешено не более 30 исследовательских вопросов');
  spec.research_questions = researchQuestions.map((item, index) => ({
    text_verbatim: text(item.text_verbatim, `research_questions[${index}].text_verbatim`, 1, 500),
    finding: text(item.finding, `research_questions[${index}].finding`, 1, 1000),
    status: QUESTION_STATUS.has(item.status) ? item.status : fail(`research_questions[${index}].status не поддерживается`),
    claim_ids: stringArray(item.claim_ids || [], `research_questions[${index}].claim_ids`, 1, 60),
  }));
  const kpis = Array.isArray(raw.kpis) ? raw.kpis : [];
  if (kpis.length > 12) fail('разрешено не более 12 KPI');
  spec.kpis = kpis.map((item, index) => ({
    label: text(item.label, `kpis[${index}].label`, 1, 100),
    value: text(item.value, `kpis[${index}].value`, 1, 80),
    delta: item.delta == null ? '' : text(item.delta, `kpis[${index}].delta`, 1, 80),
    status: STATUS.has(item.status) ? item.status : 'neutral',
    claim_ids: stringArray(item.claim_ids || [], `kpis[${index}].claim_ids`, 1, 20),
  }));

  if (!Array.isArray(raw.filters) || raw.filters.length < 1 || raw.filters.length > 12) fail('filters должен содержать от 1 до 12 фильтров');
  const filterIds = new Set();
  spec.filters = raw.filters.map((item, index) => {
    const id = text(item.id, `filters[${index}].id`, 1, 64);
    if (!/^[A-Za-z][A-Za-z0-9_-]*$/.test(id) || filterIds.has(id)) fail(`некорректный или повторяющийся filter id: ${id}`);
    filterIds.add(id);
    return {
      id,
      label: text(item.label, `filters[${index}].label`, 1, 100),
      field: text(item.field, `filters[${index}].field`, 1, 128),
      all_label: text(item.all_label, `filters[${index}].all_label`, 1, 80),
    };
  });

  if (!Array.isArray(raw.charts) || raw.charts.length < 1 || raw.charts.length > 16) fail('charts должен содержать от 1 до 16 графиков');
  const ids = new Set();
  spec.charts = raw.charts.map((item, index) => {
    const id = text(item.id, `charts[${index}].id`, 1, 64);
    if (!/^[A-Za-z][A-Za-z0-9_-]*$/.test(id) || ids.has(id)) fail(`некорректный или повторяющийся chart id: ${id}`);
    ids.add(id);
    if (!CHART_TYPES.has(item.type)) fail(`charts[${index}].type не поддерживается`);
    if (!Array.isArray(item.data) || item.data.length === 0 || item.data.length > 100000) fail(`charts[${index}].data должен содержать от 1 до 100000 строк`);
    if (!item.encode || typeof item.encode !== 'object') fail(`charts[${index}].encode обязателен`);
    const encode = {};
    for (const key of ['x', 'y', 'color', 'size', 'shape']) {
      if (item.encode[key] != null) encode[key] = text(item.encode[key], `charts[${index}].encode.${key}`, 1, 128);
    }
    if (!encode.x || !encode.y) fail(`charts[${index}]: encode.x и encode.y обязательны`);
    return {
      id,
      type: item.type,
      title: text(item.title, `charts[${index}].title`, 1, 180),
      subtitle: item.subtitle ? text(item.subtitle, `charts[${index}].subtitle`, 1, 260) : '',
      data: item.data,
      encode,
      claim_ids: stringArray(item.claim_ids || [], `charts[${index}].claim_ids`, 1, 50),
      height: Number.isInteger(item.height) && item.height >= 240 && item.height <= 700 ? item.height : 360,
    };
  });

  if (!Array.isArray(raw.tables) || raw.tables.length < 1 || raw.tables.length > 12) fail('tables должен содержать от 1 до 12 таблиц');
  const tableIds = new Set();
  spec.tables = raw.tables.map((item, index) => {
    const id = text(item.id, `tables[${index}].id`, 1, 64);
    if (!/^[A-Za-z][A-Za-z0-9_-]*$/.test(id) || tableIds.has(id)) fail(`некорректный или повторяющийся table id: ${id}`);
    tableIds.add(id);
    if (!Array.isArray(item.columns) || item.columns.length < 2 || item.columns.length > 20) fail(`tables[${index}].columns должен содержать от 2 до 20 колонок`);
    if (!Array.isArray(item.rows) || item.rows.length < 1 || item.rows.length > 100000) fail(`tables[${index}].rows должен содержать от 1 до 100000 строк`);
    const columnKeys = new Set();
    const columns = item.columns.map((column, columnIndex) => {
      const key = text(column.key, `tables[${index}].columns[${columnIndex}].key`, 1, 128);
      if (columnKeys.has(key)) fail(`tables[${index}]: повторяющаяся колонка ${key}`);
      columnKeys.add(key);
      if (!TABLE_FORMATS.has(column.format)) fail(`tables[${index}].columns[${columnIndex}].format не поддерживается`);
      const currency = column.currency == null ? '' : text(column.currency, `tables[${index}].columns[${columnIndex}].currency`, 3, 3);
      if (currency && !/^[A-Z]{3}$/.test(currency)) fail(`tables[${index}].columns[${columnIndex}].currency должен быть ISO 4217`);
      return {
        key,
        label: text(column.label, `tables[${index}].columns[${columnIndex}].label`, 1, 100),
        format: column.format,
        sortable: column.sortable === true,
        align: ['left', 'right', 'center'].includes(column.align) ? column.align : (column.format === 'number' || column.format === 'percent' || column.format === 'currency' ? 'right' : 'left'),
        currency,
      };
    });
    return {
      id,
      title: text(item.title, `tables[${index}].title`, 1, 180),
      subtitle: item.subtitle ? text(item.subtitle, `tables[${index}].subtitle`, 1, 260) : '',
      columns,
      rows: item.rows,
      searchable: item.searchable === true,
      page_size: Number.isInteger(item.page_size) && item.page_size >= 5 && item.page_size <= 100 ? item.page_size : fail(`tables[${index}].page_size должен быть от 5 до 100`),
      claim_ids: stringArray(item.claim_ids || [], `tables[${index}].claim_ids`, 1, 60),
    };
  });
  for (const filter of spec.filters) {
    const usable = [...spec.charts, ...spec.tables].some((surface) => surface.data
      ? surface.data.some((row) => Object.prototype.hasOwnProperty.call(row, filter.field))
      : surface.rows.some((row) => Object.prototype.hasOwnProperty.call(row, filter.field)));
    if (!usable) fail(`фильтр ${filter.id} не связан ни с одним графиком или таблицей`);
  }
  const customization = raw.customization && typeof raw.customization === 'object' ? raw.customization : {};
  for (const key of ['allow_section_visibility', 'allow_density', 'allow_table_search', 'allow_reset']) {
    if (customization[key] !== true) fail(`customization.${key} должен быть true`);
  }
  spec.customization = {
    allow_section_visibility: true,
    allow_density: true,
    allow_table_search: true,
    allow_reset: true,
  };

  spec.insights = (Array.isArray(raw.insights) ? raw.insights : []).slice(0, 12).map((item, index) => ({
    title: text(item.title, `insights[${index}].title`, 1, 160),
    body: text(item.body, `insights[${index}].body`, 1, 600),
    severity: STATUS.has(item.severity) ? item.severity : 'neutral',
    claim_ids: stringArray(item.claim_ids || [], `insights[${index}].claim_ids`, 1, 50),
  }));
  spec.caveats = stringArray(raw.caveats || [], 'caveats', 0, 30);
  spec.sources = stringArray(raw.sources || [], 'sources', 1, 100);

  const cards = Array.isArray(raw.storytelling_cards) ? raw.storytelling_cards : [];
  if (cards.length !== 0 && (cards.length < 2 || cards.length > 3)) fail('storytelling_cards должен содержать 2–3 карточки');
  spec.storytelling_cards = cards.map((card, index) => {
    const normalized = {
      option_id: text(card.option_id, `storytelling_cards[${index}].option_id`, 1, 64),
      headline: text(card.headline, `storytelling_cards[${index}].headline`, 1, 180),
      core_message: text(card.core_message, `storytelling_cards[${index}].core_message`, 1, 500),
      why_it_matters: text(card.why_it_matters, `storytelling_cards[${index}].why_it_matters`, 1, 500),
      executive_takeaway: text(card.executive_takeaway, `storytelling_cards[${index}].executive_takeaway`, 1, 500),
      claim_ids: stringArray(card.claim_ids || [], `storytelling_cards[${index}].claim_ids`, 1, 60),
      story_beats: (Array.isArray(card.story_beats) ? card.story_beats : []).map((beat, beatIndex) => ({
        sequence: Number.isInteger(beat.sequence) ? beat.sequence : beatIndex + 1,
        title: text(beat.title, `storytelling_cards[${index}].story_beats[${beatIndex}].title`, 1, 120),
        message: text(beat.message, `storytelling_cards[${index}].story_beats[${beatIndex}].message`, 1, 400),
      })),
      requirements_coverage: [],
    };
    assertDistinctCopy(normalized.headline, normalized.core_message, `storytelling_cards[${index}].headline`, `storytelling_cards[${index}].core_message`);
    for (let beatIndex = 0; beatIndex < normalized.story_beats.length; beatIndex += 1) {
      const beat = normalized.story_beats[beatIndex];
      assertDistinctCopy(beat.title, beat.message, `storytelling_cards[${index}].story_beats[${beatIndex}].title`, `storytelling_cards[${index}].story_beats[${beatIndex}].message`);
      if (beatIndex > 0) {
        const previous = normalized.story_beats[beatIndex - 1];
        assertDistinctCopy(`${previous.title} ${previous.message}`, `${beat.title} ${beat.message}`, `storytelling_cards[${index}].story_beats[${beatIndex - 1}]`, `storytelling_cards[${index}].story_beats[${beatIndex}]`);
      }
    }
    const explicitCoverage = Array.isArray(card.requirements_coverage) ? card.requirements_coverage : [];
    if (explicitCoverage.length) {
      const questions = new Map(spec.research_questions.map((item) => [item.text_verbatim, item]));
      const seen = new Set();
      normalized.requirements_coverage = explicitCoverage.map((item, coverageIndex) => {
        const question = text(item.text_verbatim, `storytelling_cards[${index}].requirements_coverage[${coverageIndex}].text_verbatim`, 1, 500);
        if (!questions.has(question)) fail(`storytelling_cards[${index}].requirements_coverage содержит неизвестный или переписанный пункт: ${question}`);
        if (seen.has(question)) fail(`storytelling_cards[${index}].requirements_coverage повторяет пункт: ${question}`);
        seen.add(question);
        const status = COVERAGE_STATUS.has(item.status) ? item.status : fail(`storytelling_cards[${index}].requirements_coverage[${coverageIndex}].status не поддерживается`);
        return {
          text_verbatim: question,
          status,
          framing: text(item.framing, `storytelling_cards[${index}].requirements_coverage[${coverageIndex}].framing`, 3, 500),
          beat_sequences: Array.isArray(item.beat_sequences) ? item.beat_sequences.map((value) => Number(value)) : [],
        };
      });
      const missing = spec.research_questions.map((item) => item.text_verbatim).filter((item) => !seen.has(item));
      if (missing.length) fail(`storytelling_cards[${index}].requirements_coverage не покрывает пункты: ${missing.join('; ')}`);
    } else {
      normalized.requirements_coverage = spec.research_questions.map((item) => ({
        text_verbatim: item.text_verbatim,
        status: item.status === 'answered' ? 'covered' : item.status,
        framing: item.finding,
        beat_sequences: [],
      }));
    }
    return normalized;
  });
  for (const card of spec.storytelling_cards) if (card.story_beats.length < 3 || card.story_beats.length > 5) fail('каждая storytelling card должна содержать 3–5 beats');
  for (let index = 1; index < spec.storytelling_cards.length; index += 1) {
    assertDistinctCopy(spec.storytelling_cards[index - 1].headline, spec.storytelling_cards[index].headline, `storytelling_cards[${index - 1}].headline`, `storytelling_cards[${index}].headline`);
  }
  const optionIds = spec.storytelling_cards.map((card) => card.option_id);
  if (new Set(optionIds).size !== optionIds.length) fail('option_id карточек должны быть уникальны');
  for (const optionId of optionIds) if (!/^[A-Za-z][A-Za-z0-9_-]*$/.test(optionId)) fail(`некорректный option_id карточки: ${optionId}`);
  if (spec.storytelling_cards.length) {
    spec.owner_question = text(raw.owner_question, 'owner_question', 1, 300);
    spec.recommended_option_id = text(raw.recommended_option_id, 'recommended_option_id', 1, 64);
    if (!optionIds.includes(spec.recommended_option_id)) fail('recommended_option_id должен ссылаться на storytelling card');
    if (spec.research_title_verbatim) {
      for (const card of spec.storytelling_cards) {
        if (!card.headline.includes(spec.research_title_verbatim)) {
          fail('headline каждой storytelling card должен дословно содержать research_title_verbatim');
        }
      }
    }
  }
  return spec;
}

function jsonForHtml(value) {
  return JSON.stringify(value).replace(/</g, '\\u003c').replace(/-->/g, '--\\u003e');
}

function buildHtml(spec, g2Bundle) {
  // Dashboard and owner-choice cards are different owner surfaces. Never put
  // card data into the dashboard payload, even though both outputs share one
  // validated source specification.
  const dashboardSpec = {
    title: spec.title,
    subtitle: spec.subtitle,
    output_language: spec.output_language,
    generated_at: spec.generated_at,
    surface_policy: spec.surface_policy,
    research_title_verbatim: spec.research_title_verbatim,
    research_questions: spec.research_questions.map(({ text_verbatim, finding, status }) => ({ text_verbatim, finding, status })),
    kpis: spec.kpis.map(({ label, value, delta, status }) => ({ label, value, delta, status })),
    charts: spec.charts.map(({ title, subtitle, type, data, encode, height }) => ({ title, subtitle, type, data, encode, height })),
    filters: spec.filters.map(({ label, field, all_label }) => ({ label, field, all_label })),
    tables: spec.tables.map(({ title, subtitle, columns, rows, searchable, page_size }) => ({ title, subtitle, columns, rows, searchable, page_size })),
    customization: spec.customization,
    insights: spec.insights.map(({ title, body, severity }) => ({ title, body, severity })),
    caveats: spec.caveats,
    sources: spec.sources,
  };
  const payload = jsonForHtml(dashboardSpec);
  return `<!doctype html>
<html lang="${spec.output_language}" data-mozaika-surface="dashboard-only"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>${spec.title.replace(/[<>&"]/g, '')}</title>
<style>
:root{color-scheme:light;--bg:#faf9f5;--panel:#fff;--ink:#141413;--muted:#5e5d59;--accent:#388f76;--accent-soft:#e8f0ed;--line:rgba(20,20,19,.18);--good:#388f76;--warning:#9b690a;--critical:#b4453e;--row:#f0eee6}*{box-sizing:border-box}html{scroll-behavior:smooth}body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.45 Inter,"Helvetica Neue",Arial,sans-serif}.shell{max-width:1480px;margin:auto;padding:clamp(20px,3vw,46px)}.hero{display:flex;justify-content:space-between;gap:24px;align-items:end;margin-bottom:24px}.eyebrow{font-size:12px;font-weight:800;letter-spacing:.12em;text-transform:uppercase;color:var(--accent)}h1{font:800 clamp(34px,4vw,60px)/1.05 Inter,"Helvetica Neue",Arial,sans-serif;margin:8px 0}h2,h3,p{margin-top:0}.meta{color:var(--muted);max-width:760px}.grid{display:grid;gap:16px}.kpis{grid-template-columns:repeat(auto-fit,minmax(190px,1fr));margin-bottom:16px}.kpi,.panel,.insight,.research-item,.controls{background:var(--panel);border:1px solid var(--line);border-radius:18px}.kpi{padding:18px}.kpi-label{font-size:12px;text-transform:uppercase;letter-spacing:.08em;color:var(--muted)}.kpi-value{font-size:34px;font-weight:800;margin:6px 0}.badge{display:inline-block;border-radius:999px;padding:4px 9px;font-size:12px;background:var(--row)}.good .badge{color:var(--good);background:var(--accent-soft)}.warning .badge{color:var(--warning);background:#fff1d6}.critical .badge{color:var(--critical);background:#fbe6e4}.controls{padding:18px;margin-bottom:18px;box-shadow:0 12px 30px rgba(20,20,19,.05)}.controls-head{display:flex;justify-content:space-between;gap:16px;align-items:center}.control-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(190px,1fr));gap:12px;margin-top:14px}.control label,.table-tools label{display:grid;gap:6px;font-size:12px;font-weight:750;color:var(--muted)}select,input[type=search]{width:100%;min-height:42px;border:1px solid var(--line);border-radius:11px;background:#fff;color:var(--ink);padding:9px 11px;font:inherit}button{border:1px solid var(--ink);border-radius:999px;background:var(--ink);color:#fff;padding:9px 14px;font:750 13px/1.2 inherit;cursor:pointer}button.secondary{background:#fff;color:var(--ink);border-color:var(--line)}button:focus-visible,select:focus-visible,input:focus-visible,summary:focus-visible{outline:3px solid var(--accent);outline-offset:3px}.targets{margin-top:5px;color:var(--muted);font-size:11px}.view-settings{margin-top:14px;padding-top:14px;border-top:1px solid var(--line)}summary{cursor:pointer;font-weight:800}.toggle-row{display:flex;flex-wrap:wrap;gap:14px;margin-top:12px}.toggle-row label{display:flex;gap:7px;align-items:center;font-size:13px}.charts{grid-template-columns:repeat(auto-fit,minmax(min(100%,480px),1fr))}.panel{padding:20px;min-width:0}.panel-head{display:flex;justify-content:space-between;gap:16px}.chart{width:100%;min-height:260px}.chart-error,.empty{margin:18px 0;padding:14px;border-radius:12px;color:var(--critical);background:#fbe6e4}.section-title{margin:34px 0 14px;font-size:13px;text-transform:uppercase;letter-spacing:.1em;color:var(--muted)}.tables{display:grid;gap:18px}.table-tools{display:flex;justify-content:space-between;align-items:end;gap:12px;margin:12px 0}.table-tools label:first-child{flex:1}.table-wrap{overflow:auto;border:1px solid var(--line);border-radius:12px}table{width:100%;border-collapse:collapse;min-width:640px}th,td{padding:12px 14px;border-bottom:1px solid var(--line);text-align:left;vertical-align:top}th{position:sticky;top:0;background:var(--row);z-index:1;font-size:12px;letter-spacing:.02em}th button{all:unset;display:flex;gap:6px;align-items:center;cursor:pointer;font-weight:800}th button:focus-visible{outline:3px solid var(--accent);outline-offset:2px}tbody tr:hover{background:var(--accent-soft)}.table-count{margin:10px 2px 0;color:var(--muted);font-size:12px}.research{grid-template-columns:repeat(auto-fit,minmax(280px,1fr))}.research-item{padding:18px;border-top:5px solid var(--line)}.research-item.answered{border-top-color:var(--good)}.research-item.partial{border-top-color:var(--warning)}.research-item.unanswered{border-top-color:var(--critical)}.research-status{font-size:12px;font-weight:800;color:var(--muted)}.insights{grid-template-columns:repeat(auto-fit,minmax(260px,1fr))}.insight{padding:18px;border-left:5px solid var(--line)}.insight.good{border-left-color:var(--good)}.insight.warning{border-left-color:var(--warning)}.insight.critical{border-left-color:var(--critical)}.caveats,.sources{padding:18px 22px;background:var(--row);border-radius:14px;color:#4e574f}.sources{font-size:12px;word-break:break-word}.compact .kpi,.compact .panel,.compact .insight,.compact .research-item{padding:12px}.compact th,.compact td{padding:7px 10px}.section[hidden]{display:none!important}noscript{display:block;padding:20px;background:#fff0d8}@media(max-width:700px){.shell{padding:18px}.hero,.controls-head,.table-tools{display:block}.charts{grid-template-columns:1fr}.panel{padding:14px}.controls-head button,.table-tools label{margin-top:10px}}@media(prefers-reduced-motion:reduce){html{scroll-behavior:auto}}
.panel{overflow:hidden}.chart{min-width:0;overflow:hidden}.chart canvas,.chart svg{display:block;max-width:100%!important}
</style><script>${g2Bundle}</script></head><body><div class="shell"><header class="hero"><div><div class="eyebrow">Mozaika · аналитическая панель</div><h1 id="title"></h1><p class="meta" id="subtitle"></p></div><div class="meta" id="date"></div></header><main><section class="grid kpis" id="kpis"></section><section class="grid charts" id="charts"></section><h2 class="section-title" id="insights-title">Проверенные наблюдения</h2><section class="grid insights" id="insights"></section><h2 class="section-title">Ограничения и оговорки</h2><section class="caveats" id="caveats"></section><h2 class="section-title">Источники</h2><section class="sources" id="sources"></section></main><noscript>Для отображения интерактивных графиков требуется JavaScript.</noscript></div>
<script>
const S=${payload};const ALL='__all__';const el=(tag,cls,txt)=>{const n=document.createElement(tag);if(cls)n.className=cls;if(txt!==undefined)n.textContent=txt;return n};const main=document.querySelector('main');document.getElementById('title').textContent=S.title;document.getElementById('subtitle').textContent=S.subtitle;document.getElementById('date').textContent='Сформировано: '+S.generated_at;
const sections={};const section=(name,title,node)=>{const wrap=el('section','section');wrap.dataset.section=name;if(title)wrap.append(el('h2','section-title',title));wrap.append(node);sections[name]=wrap;main.append(wrap);return wrap};main.innerHTML='';
const activeFilters={};const filterControls=[];const tableStates=S.tables.map(t=>({query:'',sortKey:'',sortDirection:1,pageSize:t.page_size}));let charts=[];
const hasField=(rows,field)=>rows.some(row=>Object.prototype.hasOwnProperty.call(row,field));const matching=(rows)=>rows.filter(row=>S.filters.every((filter,index)=>{const value=activeFilters[index];return value===ALL||!Object.prototype.hasOwnProperty.call(row,filter.field)||String(row[filter.field])===value}));
const targetNames=(filter)=>{const names=[];for(const chart of S.charts)if(hasField(chart.data,filter.field))names.push(chart.title);for(const table of S.tables)if(hasField(table.rows,filter.field))names.push(table.title);return names};
const controls=el('section','controls');const controlsHead=el('div','controls-head');const controlsTitle=el('div');controlsTitle.append(el('h2','', 'Управление данными'),el('p','meta','Фильтры изменяют связанные графики и таблицы. KPI остаются исходными, чтобы их смысл не менялся скрыто.'));const reset=el('button','secondary','Сбросить всё');controlsHead.append(controlsTitle,reset);controls.append(controlsHead);const controlGrid=el('div','control-grid');
for(const [index,filter] of S.filters.entries()){activeFilters[index]=ALL;const box=el('div','control');const label=el('label','',filter.label);const select=el('select');select.setAttribute('aria-label',filter.label);select.append(new Option(filter.all_label,ALL));const values=new Set();for(const chart of S.charts)for(const row of chart.data)if(row[filter.field]!=null)values.add(String(row[filter.field]));for(const table of S.tables)for(const row of table.rows)if(row[filter.field]!=null)values.add(String(row[filter.field]));for(const value of [...values].sort((a,b)=>a.localeCompare(b,S.output_language)))select.append(new Option(value,value));select.addEventListener('change',()=>{activeFilters[index]=select.value;refreshData()});filterControls.push(select);label.append(select);box.append(label,el('div','targets','Влияет на: '+targetNames(filter).join(' · ')));controlGrid.append(box)}controls.append(controlGrid);
const settings=el('details','view-settings');const summary=el('summary','', 'Настроить вид');settings.append(summary);const toggles=el('div','toggle-row');for(const [key,label] of [['kpis','Показатели'],['charts','Графики'],['tables','Таблицы'],['research','Вопросы исследования'],['insights','Наблюдения']]){const l=el('label');const input=document.createElement('input');input.type='checkbox';input.checked=true;input.dataset.target=key;input.addEventListener('change',()=>{if(sections[key])sections[key].hidden=!input.checked});l.append(input,document.createTextNode(label));toggles.append(l)}const densityLabel=el('label','', 'Плотность');const density=el('select');density.append(new Option('Обычная','comfortable'),new Option('Компактная','compact'));density.addEventListener('change',()=>document.body.classList.toggle('compact',density.value==='compact'));densityLabel.append(density);toggles.append(densityLabel);settings.append(toggles);controls.append(settings);main.append(controls);
const kpiGrid=el('div','grid kpis');for(const k of S.kpis){const c=el('article','kpi '+k.status);c.append(el('div','kpi-label',k.label),el('div','kpi-value',k.value));if(k.delta)c.append(el('span','badge',k.delta));kpiGrid.append(c)}section('kpis','',kpiGrid);
const chartGrid=el('div','grid charts');const chartContainers=[];for(const [index,cfg] of S.charts.entries()){const p=el('article','panel');const h=el('div','panel-head');const box=el('div');box.append(el('h2','',cfg.title));if(cfg.subtitle)box.append(el('p','meta',cfg.subtitle));h.append(box);const c=el('div','chart');c.id='chart-'+(index+1);c.style.height=cfg.height+'px';p.append(h,c);chartGrid.append(p);chartContainers.push(c)}section('charts','Графики',chartGrid);
const tableGrid=el('div','tables');const tableBodies=[];for(const [tableIndex,cfg] of S.tables.entries()){const p=el('article','panel');p.append(el('h2','',cfg.title));if(cfg.subtitle)p.append(el('p','meta',cfg.subtitle));const tools=el('div','table-tools');const searchLabel=el('label','', 'Поиск по таблице');const search=el('input');search.type='search';search.placeholder='Введите значение';search.addEventListener('input',()=>{tableStates[tableIndex].query=search.value;renderTable(tableIndex)});searchLabel.append(search);const sizeLabel=el('label','', 'Строк на странице');const size=el('select');for(const value of [10,25,50,100])if(value>=cfg.page_size||value===10)size.append(new Option(String(value),String(value)));if(![...size.options].some(o=>Number(o.value)===cfg.page_size))size.append(new Option(String(cfg.page_size),String(cfg.page_size)));size.value=String(cfg.page_size);size.addEventListener('change',()=>{tableStates[tableIndex].pageSize=Number(size.value);renderTable(tableIndex)});sizeLabel.append(size);tools.append(searchLabel,sizeLabel);p.append(tools);const wrap=el('div','table-wrap');const table=el('table');const thead=el('thead');const headRow=el('tr');for(const column of cfg.columns){const th=el('th');th.style.textAlign=column.align;if(column.sortable){const button=el('button','',column.label);button.dataset.sortKey=column.key;button.addEventListener('click',()=>{const state=tableStates[tableIndex];state.sortDirection=state.sortKey===column.key?-state.sortDirection:1;state.sortKey=column.key;renderTable(tableIndex)});th.append(button)}else th.textContent=column.label;headRow.append(th)}thead.append(headRow);const tbody=el('tbody');table.append(thead,tbody);wrap.append(table);const count=el('div','table-count');p.append(wrap,count);tableGrid.append(p);tableBodies.push({tbody,count,search,size})}section('tables','Данные в таблицах',tableGrid);
const researchGrid=el('div','grid research');const statusLabel={answered:'Исследовано',partial:'Исследовано частично',unanswered:'Недостаточно данных'};for(const item of S.research_questions){const card=el('article','research-item '+item.status);card.append(el('div','research-status',statusLabel[item.status]),el('h3','',item.text_verbatim),el('p','',item.finding));researchGrid.append(card)}if(S.research_questions.length)section('research',S.research_title_verbatim||'Вопросы исследования',researchGrid);
const insightGrid=el('div','grid insights');for(const i of S.insights){const c=el('article','insight '+i.severity);c.append(el('h3','',i.title),el('p','',i.body));insightGrid.append(c)}if(S.insights.length)section('insights','Проверенные наблюдения',insightGrid);
const cave=el('div','caveats');if(S.caveats.length){const ul=el('ul');for(const item of S.caveats)ul.append(el('li','',item));cave.append(ul)}else cave.textContent='Существенные ограничения не заявлены; проверьте это перед публикацией.';section('caveats','Ограничения и оговорки',cave);const src=el('div','sources');for(const item of S.sources)src.append(el('div','',item));section('sources','Источники',src);
const locale=S.output_language.toLowerCase().startsWith('ru')?'ru-RU':S.output_language;const formatValue=(value,column)=>{if(value==null)return '—';if(column.format==='number')return new Intl.NumberFormat(locale).format(Number(value));if(column.format==='percent')return new Intl.NumberFormat(locale,{style:'percent',maximumFractionDigits:2}).format(Number(value));if(column.format==='currency')return new Intl.NumberFormat(locale,{style:'currency',currency:column.currency||'RUB',maximumFractionDigits:2}).format(Number(value));if(column.format==='date'){const date=new Date(value);return Number.isNaN(date.getTime())?String(value):new Intl.DateTimeFormat(locale).format(date)}return String(value)};
function renderTable(index){const cfg=S.tables[index];const state=tableStates[index];let rows=matching(cfg.rows);const query=state.query.trim().toLocaleLowerCase(locale);if(query)rows=rows.filter(row=>cfg.columns.some(column=>String(row[column.key]??'').toLocaleLowerCase(locale).includes(query)));if(state.sortKey){rows=[...rows].sort((a,b)=>{const av=a[state.sortKey],bv=b[state.sortKey];if(av==null&&bv==null)return 0;if(av==null)return 1;if(bv==null)return -1;if(typeof av==='number'&&typeof bv==='number')return (av-bv)*state.sortDirection;return String(av).localeCompare(String(bv),locale,{numeric:true})*state.sortDirection})}const body=tableBodies[index].tbody;body.replaceChildren();for(const row of rows.slice(0,state.pageSize)){const tr=el('tr');for(const column of cfg.columns){const td=el('td','',formatValue(row[column.key],column));td.style.textAlign=column.align;tr.append(td)}body.append(tr)}if(!rows.length){const tr=el('tr');const td=el('td','empty','По выбранным условиям данных нет');td.colSpan=cfg.columns.length;tr.append(td);body.append(tr)}for(const button of body.parentElement.querySelectorAll('th button')){const active=button.dataset.sortKey===state.sortKey;button.setAttribute('aria-sort',active?(state.sortDirection===1?'ascending':'descending'):'none');button.textContent=button.textContent.replace(/ [↑↓]$/,'')+(active?(state.sortDirection===1?' ↑':' ↓'):'')}tableBodies[index].count.textContent='Показано '+Math.min(rows.length,state.pageSize)+' из '+rows.length}
async function renderCharts(){document.documentElement.dataset.mozaikaReady='updating';for(const chart of charts)if(chart&&typeof chart.destroy==='function')chart.destroy();charts=[];const jobs=[];for(const [index,cfg] of S.charts.entries()){const c=chartContainers[index];c.replaceChildren();const data=matching(cfg.data);if(!data.length){c.append(el('div','empty','По выбранным условиям данных нет'));continue}const chart=new G2.Chart({container:c,autoFit:true,height:cfg.height});charts.push(chart);const options={type:cfg.type==='pie'?'interval':cfg.type,data,encode:{...cfg.encode},axis:{x:{title:false},y:{title:false}},animate:false};if(cfg.type==='pie'){options.coordinate={type:'theta',outerRadius:.86};options.transform=[{type:'stackY'}];options.encode.color=cfg.encode.color||cfg.encode.x}chart.options(options);jobs.push(Promise.resolve(chart.render()).catch(error=>{c.append(el('div','chart-error','Не удалось построить график: '+(error&&error.message?error.message:String(error))));throw error}))}await Promise.all(jobs);document.documentElement.dataset.mozaikaReady='true'}
function refreshData(){for(let index=0;index<S.tables.length;index++)renderTable(index);renderCharts().catch(error=>{document.documentElement.dataset.mozaikaReady='error';document.documentElement.dataset.mozaikaError=error&&error.message?error.message:String(error);console.error('Mozaika: ошибка отрисовки графика',error)})}
reset.addEventListener('click',()=>{filterControls.forEach((select,index)=>{select.value=ALL;activeFilters[index]=ALL});tableStates.forEach((state,index)=>{state.query='';state.sortKey='';state.sortDirection=1;state.pageSize=S.tables[index].page_size;tableBodies[index].search.value='';tableBodies[index].size.value=String(state.pageSize)});document.body.classList.remove('compact');density.value='comfortable';for(const input of toggles.querySelectorAll('input[type=checkbox]')){input.checked=true;if(sections[input.dataset.target])sections[input.dataset.target].hidden=false}refreshData()});refreshData();
</script></body></html>`;
}

function buildStoryCardsHtml(spec) {
  const payload = jsonForHtml({
    title: spec.title,
    subtitle: spec.subtitle,
    output_language: spec.output_language,
    generated_at: spec.generated_at,
    owner_question: spec.owner_question,
    research_title_verbatim: spec.research_title_verbatim,
    storytelling_cards: spec.storytelling_cards.map((card) => ({
      headline: spec.research_title_verbatim
        ? card.headline.replace(spec.research_title_verbatim, '').replace(/^\s*[—–:\-]\s*/, '').trim() || card.headline
        : card.headline,
      core_message: card.core_message,
      why_it_matters: card.why_it_matters,
      executive_takeaway: card.executive_takeaway,
      story_beats: card.story_beats.map(({ title, message }) => ({ title, message })),
      requirements_coverage: card.requirements_coverage.map(({ text_verbatim, status, framing }) => ({ text_verbatim, status, framing })),
      recommended: card.option_id === spec.recommended_option_id,
    })),
    sources: spec.sources,
  });
  const russian = spec.output_language.toLowerCase().startsWith('ru');
  const labels = russian
    ? { eyebrow: 'Mozaika · выбор структуры рассказа', intro: 'Сравните варианты', why: 'Почему это важно', route: 'Как строится история', coverage: 'Как вариант раскроет ваш запрос', status: { covered: 'Будет раскрыто', partial: 'Будет раскрыто частично', unanswered: 'Недостаточно данных' }, takeaway: 'Что это значит для руководителя', recommended: 'Рекомендация Mozaika', choose: 'Сообщите агенту название близкой вам структуры рассказа.', sources: 'Источники', generated: 'Сформировано' }
    : { eyebrow: 'Mozaika · storyline choice', intro: 'Compare the options', why: 'Why it matters', route: 'How the story unfolds', coverage: 'How this option addresses your request', status: { covered: 'Covered', partial: 'Partially covered', unanswered: 'Insufficient data' }, takeaway: 'Executive implication', recommended: 'Mozaika recommendation', choose: 'Tell the agent the title of the narrative structure you prefer.', sources: 'Sources', generated: 'Generated' };
  return `<!doctype html>
<html lang="${spec.output_language}" data-mozaika-surface="storytelling-cards-only" data-mozaika-brandbook="mozaika-brandbook/v1"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>${labels.intro}: ${spec.title.replace(/[<>&"]/g, '')}</title>
<style>
:root{color-scheme:light;--mozaika-canvas:#faf9f5;--mozaika-ink:#141413;--mozaika-muted:#5e5d59;--mozaika-surface-warm:#f0eee6;--mozaika-surface-white:#ffffff;--mozaika-mint-soft:#e8f0ed;--mozaika-line:rgba(20,20,19,.18);--mozaika-green-700:#388f76;--mozaika-green-500:#59b295;--mozaika-lavender:#c9c4f5;--mozaika-rose:#d787a3;--mozaika-blue:#7fa9d2;--mozaika-lime:#d9f2a4;--mozaika-font-display:Inter,"Helvetica Neue",Arial,sans-serif;--mozaika-font-reading:Georgia,"Times New Roman",serif}*{box-sizing:border-box}html{scroll-behavior:smooth;background:var(--mozaika-canvas)}body{margin:0;background:var(--mozaika-canvas);color:var(--mozaika-ink);font:16px/1.5 var(--mozaika-font-display)}.shell{max-width:1480px;margin:auto;padding:clamp(22px,4vw,58px)}.eyebrow{color:var(--mozaika-green-700);font-size:12px;font-weight:800;letter-spacing:.13em;text-transform:uppercase}h1{font:800 clamp(38px,5vw,72px)/1.02 var(--mozaika-font-display);max-width:1050px;margin:12px 0 18px}.lead{max-width:850px;color:var(--mozaika-muted);font:18px/1.55 var(--mozaika-font-reading)}.question{margin:28px 0 34px;padding:20px 24px;border-top:1px solid var(--mozaika-line);border-bottom:1px solid var(--mozaika-line);background:var(--mozaika-mint-soft);font-size:clamp(19px,2vw,26px);font-weight:750}.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,390px),1fr));gap:0;border-top:1px solid var(--mozaika-line);border-bottom:1px solid var(--mozaika-line)}.story{scroll-margin-top:18px;display:flex;flex-direction:column;min-height:620px;padding:30px clamp(22px,2.4vw,38px);border-left:1px solid var(--mozaika-line);background:transparent;position:relative}.story:first-child{border-left:0}.story.recommended{background:linear-gradient(180deg,var(--mozaika-mint-soft),transparent 44%)}.topline{display:flex;justify-content:space-between;gap:12px;align-items:center}.option{color:var(--mozaika-green-700);font-size:13px;font-weight:850;letter-spacing:.12em;text-transform:uppercase}.badge{padding:5px 10px;border:1px solid var(--mozaika-green-700);border-radius:999px;background:var(--mozaika-surface-white);color:var(--mozaika-green-700);font-size:12px;font-weight:800}.study{margin-top:12px;color:var(--mozaika-green-700);font-size:12px;font-weight:800;letter-spacing:.07em;text-transform:uppercase}.story h2{font:750 clamp(27px,3vw,40px)/1.08 var(--mozaika-font-display);margin:10px 0 12px}.core{font:18px/1.5 var(--mozaika-font-reading)}.block{padding-top:18px;margin-top:18px;border-top:1px solid var(--mozaika-line)}.label{color:var(--mozaika-muted);font-size:12px;font-weight:800;letter-spacing:.08em;text-transform:uppercase}.beats{list-style:none;padding:0;margin:12px 0 0;counter-reset:beat}.beats li{counter-increment:beat;display:grid;grid-template-columns:34px 1fr;gap:10px;margin:13px 0}.beats li:before{content:counter(beat,decimal-leading-zero);color:var(--mozaika-green-700);font-weight:850}.beat-title{display:block}.beat-message{margin:3px 0 0;color:var(--mozaika-muted)}.coverage{padding-top:18px;margin-top:18px;border-top:1px solid var(--mozaika-line)}.coverage summary{cursor:pointer;font-weight:800}.coverage-list{display:grid;gap:10px;margin:12px 0 0;padding:0;list-style:none}.coverage-item{padding:12px 14px;background:var(--mozaika-surface-warm)}.coverage-question{font-weight:800}.coverage-framing{margin:4px 0;color:var(--mozaika-muted)}.coverage-status{color:var(--mozaika-green-700);font-size:12px;font-weight:800}.takeaway{margin-top:auto;padding:18px;border-left:4px solid var(--mozaika-green-700);background:var(--mozaika-surface-warm)}.claims{margin-top:14px;color:var(--mozaika-muted);font:12px/1.5 ui-monospace,SFMono-Regular,monospace;word-break:break-word}.jump{display:inline-flex;margin-top:16px;color:var(--mozaika-green-700);font-weight:750;text-underline-offset:4px}.jump:focus-visible{outline:3px solid var(--mozaika-green-700);outline-offset:4px}.footer{margin-top:34px;padding-top:22px;border-top:1px solid var(--mozaika-line);color:var(--mozaika-muted);font-size:13px}.sources{word-break:break-word}.skip{position:absolute;left:-9999px}.skip:focus{left:12px;top:12px;z-index:5;padding:10px;background:var(--mozaika-surface-white);color:var(--mozaika-ink);outline:3px solid var(--mozaika-green-700)}@media(max-width:900px){.story{border-left:0;border-top:1px solid var(--mozaika-line);min-height:0}.story:first-child{border-top:0}.cards{grid-template-columns:1fr}}@media(max-width:700px){.shell{padding:20px}.story{padding:24px 4px}}@media(prefers-reduced-motion:reduce){html{scroll-behavior:auto}}@media print{body{background:#fff;color:#111}.shell{max-width:none;padding:0}.story{break-inside:avoid;background:#fff;color:#111;border-color:#aaa;min-height:0}.lead,.label,.claims,.footer{color:#444}.question{background:#fff}.cards{display:block}.story{margin-bottom:14mm}}
</style></head><body><a class="skip" href="#cards">${labels.intro}</a><main class="shell"><header><div class="eyebrow">${labels.eyebrow}</div><h1 id="title"></h1><p class="lead" id="subtitle"></p><div class="question" id="question"></div></header><section class="cards" id="cards" aria-label="${labels.intro}"></section><footer class="footer"><strong>${labels.choose}</strong><div class="sources" id="sources"></div><div id="generated"></div></footer></main>
<script>
const S=${payload};const L=${jsonForHtml(labels)};const el=(tag,cls,txt)=>{const n=document.createElement(tag);if(cls)n.className=cls;if(txt!==undefined)n.textContent=txt;return n};document.getElementById('title').textContent=S.title;document.getElementById('subtitle').textContent=S.subtitle;document.getElementById('question').textContent=S.owner_question;for(const [idx,s] of S.storytelling_cards.entries()){const article=el('article','story'+(s.recommended?' recommended':''));const headingId='story-heading-'+(idx+1);article.setAttribute('aria-labelledby',headingId);if(s.recommended){const top=el('div','topline');top.append(el('span','badge',L.recommended));article.append(top)}if(S.research_title_verbatim)article.append(el('div','study',S.research_title_verbatim));const h=el('h2','',s.headline);h.id=headingId;article.append(h,el('p','core',s.core_message));const why=el('div','block');why.append(el('div','label',L.why),el('p','',s.why_it_matters));const route=el('div','block');route.append(el('div','label',L.route));const list=el('ol','beats');for(const beat of s.story_beats){const li=el('li');li.append(el('strong','beat-title',beat.title),el('p','beat-message',beat.message));list.append(li)}route.append(list);const coverage=el('details','coverage');const summary=el('summary','',L.coverage);coverage.append(summary);const coverageList=el('ul','coverage-list');for(const item of s.requirements_coverage){const li=el('li','coverage-item');li.append(el('div','coverage-question',item.text_verbatim),el('p','coverage-framing',item.framing),el('span','coverage-status',L.status[item.status]||item.status));coverageList.append(li)}coverage.append(coverageList);const takeaway=el('div','takeaway');takeaway.append(el('div','label',L.takeaway),el('div','',s.executive_takeaway));article.append(why,route,coverage,takeaway);document.getElementById('cards').append(article)}document.getElementById('sources').textContent=L.sources+': '+S.sources.join(' · ');document.getElementById('generated').textContent=L.generated+': '+S.generated_at;document.documentElement.dataset.mozaikaReady='true';
</script></body></html>`;
}

function assertSeparatedSurfaces(dashboardHtml, cardsHtml) {
  const forbiddenDashboardMarkers = [
    'id="stories"',
    'id="stories-title"',
    'S.storytelling_cards',
    '"storytelling_cards":',
    '"owner_question":',
    '"recommended_option_id":',
  ];
  for (const marker of forbiddenDashboardMarkers) {
    if (dashboardHtml.includes(marker)) fail(`dashboard содержит запрещённый маркер карточек: ${marker}`);
  }
  if (!dashboardHtml.includes('data-mozaika-surface="dashboard-only"')) {
    fail('dashboard не объявляет изолированную поверхность dashboard-only');
  }
  if (cardsHtml && !cardsHtml.includes('data-mozaika-surface="storytelling-cards-only"')) {
    fail('страница карточек не объявляет отдельную поверхность storytelling-cards-only');
  }
  if (cardsHtml) {
    const requiredBrandbookMarkers = [
      'data-mozaika-brandbook="mozaika-brandbook/v1"',
      '--mozaika-canvas:#faf9f5',
      '--mozaika-ink:#141413',
      '--mozaika-surface-warm:#f0eee6',
      '--mozaika-green-700:#388f76',
      '--mozaika-green-500:#59b295',
    ];
    for (const marker of requiredBrandbookMarkers) {
      if (!cardsHtml.includes(marker)) fail(`страница карточек не использует обязательный токен брендбука: ${marker}`);
    }
    for (const forbidden of ['#101512', '#18201b', '#202a23', '#21362b']) {
      if (cardsHtml.toLowerCase().includes(forbidden)) fail(`страница карточек содержит запрещённую тёмную тему: ${forbidden}`);
    }
    for (const serviceMarker of ['"option_id":', '"recommended_option_id":', '"claim_ids":']) {
      if (cardsHtml.includes(serviceMarker)) fail(`страница карточек содержит служебный идентификатор: ${serviceMarker}`);
    }
  }
}

function main() {
  const args = parseArgs(process.argv);
  if (!fs.existsSync(args.spec)) fail(`spec не найден: ${args.spec}`);
  if (fs.existsSync(args.output)) fail(`выходной файл уже существует: ${args.output}`);
  const spec = validateSpec(readJson(args.spec));
  if (spec.storytelling_cards.length && !args.cardsOutput) fail('для storytelling_cards обязателен --cards-output');
  if (!spec.storytelling_cards.length && args.cardsOutput) fail('--cards-output допустим только при наличии storytelling_cards');
  if (args.cardsOutput && fs.existsSync(args.cardsOutput)) fail(`выходной файл карточек уже существует: ${args.cardsOutput}`);
  const html = buildHtml(spec, findG2Bundle());
  const cardsHtml = args.cardsOutput ? buildStoryCardsHtml(spec) : '';
  assertSeparatedSurfaces(html, cardsHtml);
  fs.mkdirSync(path.dirname(args.output), { recursive: true });
  fs.writeFileSync(args.output, html, { flag: 'wx', mode: 0o600 });
  const sha256 = crypto.createHash('sha256').update(html).digest('hex');
  let cardsResult = null;
  if (args.cardsOutput) {
    fs.mkdirSync(path.dirname(args.cardsOutput), { recursive: true });
    fs.writeFileSync(args.cardsOutput, cardsHtml, { flag: 'wx', mode: 0o600 });
    cardsResult = { output: args.cardsOutput, sha256: crypto.createHash('sha256').update(cardsHtml).digest('hex'), schema: 'owner-choice-cards-html/v1' };
  }
  process.stdout.write(`${JSON.stringify({ ok: true, output: args.output, sha256, schema: 'dashboard-html-without-storytelling-cards/v1', surface: 'dashboard-only', cards_output: cardsResult, charts: spec.charts.length, storytelling_cards: spec.storytelling_cards.length })}\n`);
}

try { main(); } catch (error) { fail(error && error.message ? error.message : String(error), 1); }
