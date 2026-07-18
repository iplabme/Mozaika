(() => {
  'use strict';

  const DEFAULT_TASK_PREFIX = 'Обнови регулярный отчёт по новым данным: пересчитай показатели, сравни их с историей и выдели аномалии и важные моменты.';
  const FIXED_TASK_SUFFIX = 'Подготовь проверенный управляемый HTML-дашборд, итоговую HTML-презентацию по недельному шаблону и последним шагом редактируемый PPTX.';
  const CONFIG = {
    route: '/api/extensions/mozaika/scenario/weekly/start',
    pickerRoute: '/api/extensions/mozaika/scenario/local/pick',
    presetsRoute: '/api/extensions/mozaika/scenario/weekly-task-presets',
    title: 'Данные для рутинного отчёта',
    lead: 'Добавьте выгрузки, шаблон, URL или папку — источники можно смешивать.',
    taskLabel: 'Описание задачи',
    defaultTask: `${DEFAULT_TASK_PREFIX} ${FIXED_TASK_SUFFIX}`,
    startLabel: 'Обновить отчёт',
    taskField: 'weekly_brief',
  };
  const MAX_SOURCES = 50;
  const MAX_FILES = 500;
  const MAX_PROMPT_CHARS = 8000;
  const VISIBLE_SOURCES = 6;
  const root = document.getElementById('root');
  const sources = [];
  let nextId = 1;

  root.innerHTML = `
    <style>
      * { box-sizing: border-box; }
      html, body { margin: 0; background: #faf9f5; color: #141413; font: 13px/1.35 -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; }
      button, input, textarea { font: inherit; }
      main { min-height: 286px; padding: 12px 14px; }
      .top { display: flex; align-items: flex-start; justify-content: space-between; gap: 12px; }
      h2 { margin: 0; font-size: 18px; line-height: 24px; }
      .lead { margin: 2px 0 8px; color: #5e5d59; }
      .add-wrap { position: relative; flex: 0 0 auto; }
      .add { display: inline-flex; align-items: center; justify-content: center; width: 34px; height: 34px; padding: 0 0 2px; border: 1px solid #388f76; border-radius: 50%; background: #388f76; color: #fff; font-size: 25px; line-height: 1; cursor: pointer; }
      .add:hover, .add:focus-visible { background: #59b295; outline: 2px solid #388f76; outline-offset: 2px; }
      .menu { position: absolute; z-index: 20; top: 40px; right: 0; min-width: 174px; padding: 5px; border: 1px solid #d7d3ca; border-radius: 11px; background: #f0eee6; box-shadow: 0 14px 34px #14141324; }
      .menu[hidden] { display: none; }
      .menu button { width: 100%; padding: 9px 10px; border: 0; border-radius: 7px; background: transparent; color: #141413; text-align: left; cursor: pointer; }
      .menu button:hover { background: #e8f0ed; }
      .drop { display: flex; align-items: center; justify-content: center; min-height: 40px; padding: 7px 12px; border: 1.5px dashed #8b8a85; border-radius: 10px; background: #fff; color: #5e5d59; text-align: center; transition: .15s ease; }
      .drop.over { border-color: #388f76; background: #e8f0ed; color: #141413; }
      .sources { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 5px; min-height: 36px; margin: 7px 0; }
      .source { display: flex; align-items: center; min-width: 0; gap: 6px; height: 31px; padding: 5px 7px; border: 1px solid #dedbd3; border-radius: 8px; background: #fff; }
      .source-icon { flex: 0 0 auto; font-size: 15px; }
      .source-name { min-width: 0; flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
      .source-meta { color: #5e5d59; font-size: 11px; white-space: nowrap; }
      .remove { flex: 0 0 auto; border: 0; padding: 0 2px; background: transparent; color: #9f2d2d; cursor: pointer; font-size: 17px; line-height: 18px; }
      .empty { grid-column: 1 / -1; display: flex; align-items: center; height: 31px; color: #77756f; }
      .more { cursor: pointer; color: #388f76; }
      .task-row { display: grid; grid-template-columns: minmax(0, 1fr) auto; gap: 10px; align-items: end; }
      .task-field { display: grid; gap: 5px; min-width: 0; }
      label { display: grid; gap: 3px; color: #141413; }
      textarea { width: 100%; height: 78px; min-height: 78px; max-height: 78px; resize: none; border: 1px solid #c9c6bd; border-radius: 9px; padding: 9px 11px; background: #fff; color: #141413; }
      textarea:focus, input:focus { border-color: #388f76; outline: 1px solid #388f76; }
      .presets-wrap { position: relative; z-index: 60; justify-self: start; }
      .presets-pill { height: 24px; border: 0; border-radius: 999px; padding: 0 10px; background: #141413; color: #fff; font-size: 11px; font-weight: 650; cursor: pointer; }
      .presets-pill:hover { background: #32312f; }
      .presets-pill:focus-visible { background: #141413; outline: none; box-shadow: 0 0 0 2px #14141338; }
      .presets-pill:disabled { opacity: .45; cursor: wait; }
      .presets-menu { position: absolute; z-index: 100; left: 0; bottom: calc(100% + 12px); width: min(410px, calc(100vw - 48px)); padding: 8px; border: 1px solid #aaa59a; border-radius: 13px; background: #fff; box-shadow: 0 24px 64px #14141338, 0 4px 14px #1414131f; }
      .presets-menu::after { content: ""; position: absolute; left: 18px; top: 100%; border: 7px solid transparent; border-top-color: #fff; filter: drop-shadow(0 1px 0 #aaa59a); }
      .presets-menu[hidden] { display: none; }
      .presets-menu button { display: block; width: 100%; border: 0; border-radius: 7px; padding: 9px 10px; background: transparent; color: #141413; text-align: left; cursor: pointer; }
      .presets-menu button:hover, .presets-menu button:focus-visible { background: #f0eee6; outline: none; }
      .start { height: 38px; min-width: 142px; border: 0; border-radius: 10px; padding: 0 14px; background: #141413; color: #fff; font-weight: 700; cursor: pointer; }
      .start:disabled { opacity: .55; cursor: wait; }
      .footer { display: flex; align-items: center; justify-content: flex-end; min-height: 20px; margin-top: 4px; }
      .status { min-height: 18px; color: #5e5d59; text-align: right; }
      .status.error { color: #9f2d2d; }
      .status.ok { color: #388f76; }
      dialog { width: min(520px, calc(100% - 28px)); border: 1px solid #d7d3ca; border-radius: 13px; padding: 14px; background: #faf9f5; color: #141413; box-shadow: 0 18px 50px #14141338; }
      dialog::backdrop { background: #14141366; }
      dialog h3 { margin: 0 0 10px; font-size: 16px; }
      dialog input { width: 100%; border: 1px solid #c9c6bd; border-radius: 9px; padding: 9px 10px; background: #fff; color: #141413; }
      .dialog-actions { display: flex; justify-content: flex-end; flex-wrap: wrap; gap: 8px; margin-top: 12px; }
      .secondary { border: 1px solid #c9c6bd; border-radius: 8px; padding: 8px 11px; background: #f0eee6; color: #141413; cursor: pointer; }
      .primary { border: 0; border-radius: 8px; padding: 8px 11px; background: #141413; color: #fff; font-weight: 700; cursor: pointer; }
      .manage-list { display: grid; gap: 6px; max-height: 230px; overflow: auto; }
      @media (max-width: 650px) {
        .sources { grid-template-columns: repeat(2, minmax(0, 1fr)); }
        .task-row { grid-template-columns: 1fr; }
        .start { width: 100%; }
        main { min-height: 360px; }
      }
    </style>
    <main>
      <div class="top">
        <div><h2>${CONFIG.title}</h2><p class="lead">${CONFIG.lead}</p></div>
        <div class="add-wrap">
          <button id="add" class="add" type="button" aria-label="Добавить источник" aria-expanded="false">+</button>
          <div id="add-menu" class="menu" hidden>
            <button id="add-url" type="button">🔗 URL</button>
            <button id="add-local" type="button">📎 Файл или папка</button>
          </div>
        </div>
      </div>
      <input id="file-input" type="file" multiple hidden>
      <input id="folder-input" type="file" webkitdirectory directory multiple hidden>
      <div id="drop" class="drop">Перетащите файлы или папку сюда</div>
      <div id="source-list" class="sources"></div>
      <div class="task-row">
        <div class="task-field">
          <label>${CONFIG.taskLabel}<textarea id="task" maxlength="${MAX_PROMPT_CHARS}">${CONFIG.defaultTask}</textarea></label>
          <div class="presets-wrap">
            <button id="task-presets" class="presets-pill" type="button" aria-haspopup="menu" aria-expanded="false" disabled>варианты задания</button>
            <div id="task-presets-menu" class="presets-menu" role="menu" hidden></div>
          </div>
        </div>
        <button id="start" class="start" type="button">${CONFIG.startLabel}</button>
      </div>
      <div class="footer">
        <span id="status" class="status" aria-live="polite"></span>
      </div>
    </main>
    <dialog id="url-dialog">
      <form method="dialog" id="url-form">
        <h3>Добавить URL</h3>
        <input id="url-value" type="url" inputmode="url" placeholder="https://…" autocomplete="off">
        <div class="dialog-actions"><button id="cancel-url" class="secondary" type="button">Отмена</button><button id="confirm-url" class="primary" type="submit" value="default">Добавить</button></div>
      </form>
    </dialog>
    <dialog id="local-dialog">
      <h3>Что добавить?</h3>
      <div class="dialog-actions"><button id="choose-files" class="primary" type="button">Выбрать файлы</button><button id="choose-folder" class="primary" type="button">Выбрать папку</button><button id="cancel-local" class="secondary" type="button">Отмена</button></div>
    </dialog>
    <dialog id="manage-dialog">
      <h3>Все входные источники</h3>
      <div id="manage-list" class="manage-list"></div>
      <div class="dialog-actions"><button id="close-manage" class="primary" type="button">Готово</button></div>
    </dialog>`;

  const addButton = document.getElementById('add');
  const addMenu = document.getElementById('add-menu');
  const addUrl = document.getElementById('add-url');
  const addLocal = document.getElementById('add-local');
  const fileInput = document.getElementById('file-input');
  const folderInput = document.getElementById('folder-input');
  const drop = document.getElementById('drop');
  const list = document.getElementById('source-list');
  const task = document.getElementById('task');
  const presetsButton = document.getElementById('task-presets');
  const presetsMenu = document.getElementById('task-presets-menu');
  const start = document.getElementById('start');
  const status = document.getElementById('status');
  const urlDialog = document.getElementById('url-dialog');
  const urlForm = document.getElementById('url-form');
  const urlValue = document.getElementById('url-value');
  const localDialog = document.getElementById('local-dialog');
  const manageDialog = document.getElementById('manage-dialog');
  const manageList = document.getElementById('manage-list');
  let taskPresets = {
    fixed_suffix: FIXED_TASK_SUFFIX,
    items: [],
  };
  let selectDefaultOnFocus = true;

  function closePresetsMenu() {
    presetsMenu.hidden = true;
    presetsButton.setAttribute('aria-expanded', 'false');
  }

  function applyTaskPreset(prefix) {
    task.value = `${String(prefix || '').trim()} ${taskPresets.fixed_suffix}`.trim();
    selectDefaultOnFocus = false;
    closePresetsMenu();
    task.focus();
  }

  function renderTaskPresets() {
    presetsMenu.replaceChildren();
    taskPresets.items.forEach((preset) => {
      const option = document.createElement('button');
      option.type = 'button';
      option.setAttribute('role', 'menuitem');
      option.textContent = preset.label;
      option.addEventListener('click', () => applyTaskPreset(preset.prefix));
      presetsMenu.append(option);
    });
    presetsButton.disabled = taskPresets.items.length === 0;
  }

  async function loadTaskPresets() {
    try {
      const response = await fetch(CONFIG.presetsRoute, { headers: { Accept: 'application/json' } });
      const data = await response.json();
      if (!response.ok || !data.ok || !data.presets) throw new Error(data.error || `HTTP ${response.status}`);
      const loaded = data.presets;
      if (!Array.isArray(loaded.items) || !loaded.items.length || !String(loaded.fixed_suffix || '').startsWith('Подготовь')) throw new Error('Настройки вариантов задания некорректны.');
      const previousDefault = `${DEFAULT_TASK_PREFIX} ${FIXED_TASK_SUFFIX}`;
      taskPresets = loaded;
      presetsButton.textContent = loaded.button_label || 'варианты задания';
      if (task.value === previousDefault) task.value = `${loaded.default_prefix} ${loaded.fixed_suffix}`;
      renderTaskPresets();
    } catch (error) {
      presetsButton.disabled = true;
      presetsButton.title = error.message || String(error);
    }
  }

  const formatSize = (bytes) => bytes < 1024 * 1024
    ? `${Math.max(1, Math.round(bytes / 1024))} КБ`
    : `${(bytes / (1024 * 1024)).toFixed(1)} МБ`;

  function setStatus(message, kind = '') {
    status.textContent = message;
    status.className = `status ${kind}`;
  }

  function openDialog(dialog) {
    if (typeof dialog.showModal === 'function') dialog.showModal();
    else dialog.setAttribute('open', '');
  }

  function closeDialog(dialog) {
    if (typeof dialog.close === 'function') dialog.close();
    else dialog.removeAttribute('open');
  }

  function sourceStats(source) {
    if (source.kind === 'url') return '';
    if (source.kind === 'local_path') return source.entryType === 'directory' ? 'Папка' : formatSize(source.size || 0);
    if (source.kind === 'file') return formatSize(source.file.size);
    return `${source.files.length} · ${formatSize(source.files.reduce((sum, item) => sum + item.file.size, 0))}`;
  }

  function sourceIcon(source) {
    if (source.kind === 'url') return '🔗';
    if (source.kind === 'directory' || (source.kind === 'local_path' && source.entryType === 'directory')) return '📁';
    return '📄';
  }

  function sourceName(source) {
    if (source.kind === 'url') return source.url;
    if (source.kind === 'file') return source.file.name;
    return source.name;
  }

  function makeSourceRow(source, removable = true) {
    const row = document.createElement('div');
    row.className = 'source';
    row.title = sourceName(source);
    const icon = document.createElement('span');
    icon.className = 'source-icon';
    icon.textContent = sourceIcon(source);
    const name = document.createElement('span');
    name.className = 'source-name';
    name.textContent = sourceName(source);
    const meta = document.createElement('span');
    meta.className = 'source-meta';
    meta.textContent = sourceStats(source);
    row.append(icon, name, meta);
    if (removable) {
      const remove = document.createElement('button');
      remove.type = 'button';
      remove.className = 'remove';
      remove.textContent = '×';
      remove.setAttribute('aria-label', `Убрать ${sourceName(source)}`);
      remove.addEventListener('click', () => removeSource(source.id));
      row.append(remove);
    }
    return row;
  }

  function renderSources() {
    list.replaceChildren();
    if (!sources.length) {
      const empty = document.createElement('div');
      empty.className = 'empty';
      empty.textContent = 'Источники ещё не добавлены';
      list.append(empty);
      return;
    }
    const visible = sources.length > VISIBLE_SOURCES ? sources.slice(0, VISIBLE_SOURCES - 1) : sources;
    visible.forEach((source) => list.append(makeSourceRow(source)));
    if (sources.length > VISIBLE_SOURCES) {
      const more = document.createElement('button');
      more.type = 'button';
      more.className = 'source more';
      more.textContent = `Ещё ${sources.length - visible.length}…`;
      more.addEventListener('click', showAllSources);
      list.append(more);
    }
  }

  function showAllSources() {
    manageList.replaceChildren(...sources.map((source) => makeSourceRow(source)));
    if (!manageDialog.open) openDialog(manageDialog);
  }

  function removeSource(id) {
    const index = sources.findIndex((item) => item.id === id);
    if (index >= 0) sources.splice(index, 1);
    renderSources();
    if (manageDialog.open) manageList.replaceChildren(...sources.map((source) => makeSourceRow(source)));
  }

  function allBrowserFiles() {
    return sources.flatMap((source) => source.kind === 'file'
      ? [source.file]
      : (source.kind === 'directory' ? source.files.map((item) => item.file) : []));
  }

  function addLocalPath(item) {
    canAdd(0);
    const path = String(item.path || '');
    const token = String(item.selection_token || '');
    if (!path || !token) throw new Error('Системный диалог не вернул подтверждённый путь.');
    const duplicate = sources.some((source) => source.kind === 'local_path' && source.path === path);
    if (!duplicate) sources.push({
      id: `source-${nextId++}`,
      kind: 'local_path',
      path,
      selectionToken: token,
      entryType: item.entry_type === 'directory' ? 'directory' : 'file',
      name: String(item.display_name || path.split(/[\\/]/).pop() || path),
      size: Number(item.size_bytes || 0),
    });
  }

  function canAdd(fileCount) {
    if (sources.length >= MAX_SOURCES) throw new Error(`Можно добавить не больше ${MAX_SOURCES} источников.`);
    const current = allBrowserFiles();
    if (current.length + fileCount > MAX_FILES) throw new Error(`Можно добавить не больше ${MAX_FILES} файлов.`);
  }

  function addFile(file) {
    canAdd(1);
    const duplicate = sources.some((item) => item.kind === 'file' && item.file.name === file.name && item.file.size === file.size && item.file.lastModified === file.lastModified);
    if (!duplicate) sources.push({ id: `source-${nextId++}`, kind: 'file', file });
  }

  function addDirectory(name, entries) {
    if (!entries.length) throw new Error(`${name}: папка не содержит доступных файлов.`);
    canAdd(entries.length);
    const signature = entries.map((item) => `${item.relativePath}:${item.file.size}`).sort().join('|');
    const duplicate = sources.some((item) => item.kind === 'directory' && item.name === name && item.signature === signature);
    if (!duplicate) sources.push({ id: `source-${nextId++}`, kind: 'directory', name, files: entries, signature });
  }

  function addUrlValue(value) {
    let parsed;
    try { parsed = new URL(String(value || '').trim()); } catch (_error) { throw new Error('Введите корректный URL.'); }
    if (!['http:', 'https:'].includes(parsed.protocol) || !parsed.host || parsed.username || parsed.password) throw new Error('Разрешены только http/https URL без логина и пароля.');
    const normalized = parsed.href;
    canAdd(0);
    if (!sources.some((item) => item.kind === 'url' && item.url === normalized)) sources.push({ id: `source-${nextId++}`, kind: 'url', url: normalized });
  }

  function addPickedFiles(fileList) {
    setStatus('');
    try {
      Array.from(fileList || []).forEach(addFile);
      renderSources();
    } catch (error) { setStatus(error.message || String(error), 'error'); }
  }

  function addPickedDirectory(fileList) {
    setStatus('');
    try {
      const groups = new Map();
      Array.from(fileList || []).forEach((file) => {
        const relativePath = file.webkitRelativePath || file.name;
        const rootName = relativePath.split('/')[0] || 'Папка';
        if (!groups.has(rootName)) groups.set(rootName, []);
        groups.get(rootName).push({ file, relativePath });
      });
      groups.forEach((entries, name) => addDirectory(name, entries));
      renderSources();
    } catch (error) { setStatus(error.message || String(error), 'error'); }
  }

  function readEntryFile(entry, relativePath) {
    return new Promise((resolve, reject) => entry.file((file) => resolve({ file, relativePath }), reject));
  }

  async function readDirectoryEntries(entry, prefix = '') {
    const reader = entry.createReader();
    const children = [];
    while (true) {
      const batch = await new Promise((resolve, reject) => reader.readEntries(resolve, reject));
      if (!batch.length) break;
      children.push(...batch);
    }
    const files = [];
    for (const child of children) {
      const relativePath = `${prefix}${child.name}`;
      if (child.isFile) files.push(await readEntryFile(child, relativePath));
      else if (child.isDirectory) files.push(...await readDirectoryEntries(child, `${relativePath}/`));
    }
    return files;
  }

  async function readDirectoryHandle(handle, prefix = '') {
    const files = [];
    for await (const [name, child] of handle.entries()) {
      const relativePath = `${prefix}${name}`;
      if (child.kind === 'file') files.push({ file: await child.getFile(), relativePath });
      else if (child.kind === 'directory') files.push(...await readDirectoryHandle(child, `${relativePath}/`));
    }
    return files;
  }

  async function chooseDirectory() {
    closeDialog(localDialog);
    setStatus('');
    await chooseLocalPaths('directory');
  }

  async function chooseLocalPaths(kind) {
    closeDialog(localDialog);
    setStatus(kind === 'directory' ? 'Открываю выбор папки…' : 'Открываю выбор файлов…');
    try {
      const response = await fetch(CONFIG.pickerRoute, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ kind }),
      });
      const data = await response.json();
      if (!response.ok || !data.ok) throw new Error(data.error || `HTTP ${response.status}`);
      if (data.cancelled) { setStatus(''); return; }
      (data.sources || []).forEach(addLocalPath);
      renderSources();
      setStatus('');
    } catch (error) {
      setStatus(error.message || String(error), 'error');
    }
  }

  async function addDropped(dataTransfer) {
    setStatus('Проверяю добавленные источники…');
    try {
      const items = Array.from((dataTransfer && dataTransfer.items) || []);
      const entries = items.map((item) => item.webkitGetAsEntry && item.webkitGetAsEntry()).filter(Boolean);
      if (!entries.length) {
        addPickedFiles(dataTransfer && dataTransfer.files);
        return;
      }
      for (const entry of entries) {
        if (entry.isFile) addFile((await readEntryFile(entry, entry.name)).file);
        else if (entry.isDirectory) addDirectory(entry.name, await readDirectoryEntries(entry, `${entry.name}/`));
      }
      renderSources();
      setStatus('');
    } catch (error) { setStatus(error.message || String(error), 'error'); }
  }

  function encodeFile(file, relativePath = '') {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onerror = () => reject(new Error(`Не удалось прочитать ${file.name}`));
      reader.onload = () => resolve({
        name: file.name,
        relative_path: relativePath || file.name,
        mime: file.type || 'application/octet-stream',
        size: file.size,
        data_base64: String(reader.result || '').split(',', 2)[1] || '',
      });
      reader.readAsDataURL(file);
    });
  }

  async function serializeSources() {
    const result = [];
    let done = 0;
    const total = allBrowserFiles().length;
    for (const source of sources) {
      if (source.kind === 'url') {
        result.push({ kind: 'url', url: source.url, display_name: source.url });
      } else if (source.kind === 'local_path') {
        result.push({
          kind: 'local_path',
          path: source.path,
          selection_token: source.selectionToken,
          entry_type: source.entryType,
          display_name: source.name,
        });
      } else if (source.kind === 'file') {
        setStatus(`Читаю файл ${++done} из ${total}…`);
        result.push({ kind: 'file', file: await encodeFile(source.file) });
      } else {
        const files = [];
        for (const item of source.files) {
          setStatus(`Читаю файл ${++done} из ${total}…`);
          files.push(await encodeFile(item.file, item.relativePath));
        }
        result.push({ kind: 'directory', name: source.name, files });
      }
    }
    return result;
  }

  addButton.addEventListener('click', () => {
    const next = addMenu.hidden;
    addMenu.hidden = !next;
    addButton.setAttribute('aria-expanded', String(next));
  });
  document.addEventListener('click', (event) => {
    if (!event.target.closest('.add-wrap')) { addMenu.hidden = true; addButton.setAttribute('aria-expanded', 'false'); }
    if (!event.target.closest('.presets-wrap')) closePresetsMenu();
  });
  presetsButton.addEventListener('click', () => {
    const next = presetsMenu.hidden;
    presetsMenu.hidden = !next;
    presetsButton.setAttribute('aria-expanded', String(next));
  });
  addUrl.addEventListener('click', () => { addMenu.hidden = true; addButton.setAttribute('aria-expanded', 'false'); urlValue.value = ''; openDialog(urlDialog); setTimeout(() => urlValue.focus(), 0); });
  addLocal.addEventListener('click', () => { addMenu.hidden = true; addButton.setAttribute('aria-expanded', 'false'); openDialog(localDialog); });
  document.getElementById('choose-files').addEventListener('click', () => { void chooseLocalPaths('file'); });
  document.getElementById('choose-folder').addEventListener('click', () => { void chooseDirectory(); });
  document.getElementById('cancel-url').addEventListener('click', () => closeDialog(urlDialog));
  document.getElementById('cancel-local').addEventListener('click', () => closeDialog(localDialog));
  document.getElementById('close-manage').addEventListener('click', () => closeDialog(manageDialog));
  fileInput.addEventListener('change', () => { addPickedFiles(fileInput.files); fileInput.value = ''; });
  folderInput.addEventListener('change', () => { addPickedDirectory(folderInput.files); folderInput.value = ''; });
  urlForm.addEventListener('submit', (event) => {
    event.preventDefault();
    try { addUrlValue(urlValue.value); renderSources(); closeDialog(urlDialog); setStatus(''); }
    catch (error) { setStatus(error.message || String(error), 'error'); urlValue.focus(); }
  });
  ['dragenter', 'dragover'].forEach((name) => drop.addEventListener(name, (event) => { event.preventDefault(); drop.classList.add('over'); }));
  ['dragleave', 'drop'].forEach((name) => drop.addEventListener(name, (event) => { event.preventDefault(); drop.classList.remove('over'); }));
  drop.addEventListener('drop', (event) => addDropped(event.dataTransfer));
  task.addEventListener('focus', () => { if (selectDefaultOnFocus) { task.select(); selectDefaultOnFocus = false; } });

  start.addEventListener('click', async () => {
    if (!sources.length) { setStatus('Добавьте URL, файл или папку.', 'error'); return; }
    start.disabled = true;
    try {
      const payload = { sources: await serializeSources() };
      payload[CONFIG.taskField] = task.value.trim();
      setStatus('Передаю задачу Ouroboros…');
      const response = await fetch(CONFIG.route, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      const data = await response.json();
      if (!response.ok || !data.ok) throw new Error(data.error || `HTTP ${response.status}`);
      const taskStatus = data.task_id ? ` Задача: ${data.task_id}.` : '';
      setStatus(`Запущено. Источников: ${data.source_count || sources.length}, файлов: ${data.file_count || 0}.${taskStatus}`, 'ok');
    } catch (error) {
      setStatus(error.message || String(error), 'error');
    } finally {
      start.disabled = false;
    }
  });

  renderSources();
  void loadTaskPresets();
})();
