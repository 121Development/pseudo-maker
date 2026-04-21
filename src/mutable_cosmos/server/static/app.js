'use strict';

const $ = (sel) => document.querySelector(sel);
const $$ = (sel) => Array.from(document.querySelectorAll(sel));

// ---- Tabs ---------------------------------------------------------------

$$('.tab').forEach((tab) => {
  tab.addEventListener('click', () => {
    $$('.tab').forEach((t) => t.classList.toggle('active', t === tab));
    const target = tab.dataset.tab;
    $$('.panel').forEach((p) => p.classList.toggle('active', p.id === `panel-${target}`));
  });
});

function showStage(panelId, stageId) {
  $$(`#${panelId} .stage`).forEach((s) => s.classList.toggle('active', s.id === stageId));
}

// ---- Client-side validation --------------------------------------------

function luhnValid(digits) {
  if (!/^\d+$/.test(digits) || digits.length === 0) return false;
  let total = 0;
  const parity = digits.length % 2;
  for (let i = 0; i < digits.length; i++) {
    let n = parseInt(digits[i], 10);
    if (i % 2 === parity) {
      n *= 2;
      if (n > 9) n -= 9;
    }
    total += n;
  }
  return total % 10 === 0;
}

function validatePersonnummer(text) {
  const digits = text.replace(/[-+]/g, '');
  if (digits.length !== 10 && digits.length !== 12) return { ok: false, message: 'expected 10 or 12 digits' };
  const ten = digits.length === 12 ? digits.slice(2) : digits;
  if (!/^\d{10}$/.test(ten)) return { ok: false, message: 'non-digit characters' };
  return luhnValid(ten)
    ? { ok: true }
    : { ok: false, message: 'invalid Luhn checksum' };
}

function validateOrgnr(text) {
  const digits = text.replace(/[^\d]/g, '');
  if (digits.length !== 10) return { ok: false, message: 'expected 10 digits' };
  if (parseInt(digits[2], 10) < 2) return { ok: false, message: 'third digit must be ≥ 2' };
  return luhnValid(digits)
    ? { ok: true }
    : { ok: false, message: 'invalid Luhn checksum' };
}

function validateBankgiro(text) {
  const digits = text.replace(/[^\d]/g, '');
  if (digits.length < 7 || digits.length > 8) return { ok: false, message: 'expected 7–8 digits' };
  return luhnValid(digits)
    ? { ok: true }
    : { ok: false, message: 'invalid Luhn checksum' };
}

function validateIban(text) {
  const compact = text.replace(/\s+/g, '').toUpperCase();
  if (!/^[A-Z]{2}\d{2}[A-Z0-9]{11,30}$/.test(compact)) return { ok: false, message: 'bad IBAN format' };
  return { ok: true };
}

function validateCreditCard(text) {
  const digits = text.replace(/[^\d]/g, '');
  if (digits.length < 13 || digits.length > 19) return { ok: false, message: 'expected 13–19 digits' };
  return luhnValid(digits) ? { ok: true } : { ok: false, message: 'invalid Luhn checksum' };
}

function validateEmail(text) {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(text)
    ? { ok: true }
    : { ok: false, message: 'not a valid email' };
}

function validateForType(type, value) {
  if (!value || !value.trim()) return { ok: false, message: 'empty' };
  switch (type) {
    case 'PERSONNUMMER': return validatePersonnummer(value);
    case 'ORGNR':        return validateOrgnr(value);
    case 'BANKGIRO':
    case 'PLUSGIRO':     return validateBankgiro(value);
    case 'IBAN':         return validateIban(value);
    case 'CREDIT_CARD':  return validateCreditCard(value);
    case 'EMAIL':        return validateEmail(value);
    default:             return { ok: true };
  }
}

// ---- Clean flow ---------------------------------------------------------

const cleanState = {
  sessionId: null,
  entities: [],
  excluded: new Set(),
  customFakes: new Map(), // entity_id → user-chosen fake (string)
  currentFakes: new Map(), // entity_id → current fake (auto or custom), used for duplicate detection
};

function wireDropzone(zone, input, onFile) {
  zone.addEventListener('click', () => input.click());
  input.addEventListener('change', (e) => {
    if (e.target.files[0]) onFile(e.target.files[0]);
  });
  ['dragenter', 'dragover'].forEach((evt) =>
    zone.addEventListener(evt, (e) => { e.preventDefault(); zone.classList.add('dragover'); })
  );
  ['dragleave', 'drop'].forEach((evt) =>
    zone.addEventListener(evt, (e) => { e.preventDefault(); zone.classList.remove('dragover'); })
  );
  zone.addEventListener('drop', (e) => {
    e.preventDefault();
    if (e.dataTransfer.files[0]) onFile(e.dataTransfer.files[0]);
  });
}

wireDropzone($('#dropzone-clean'), $('#file-clean'), uploadClean);

async function uploadClean(file) {
  showStage('panel-clean', 'clean-processing');
  try {
    const body = new FormData();
    body.append('file', file);
    const res = await fetch('/api/clean/upload', { method: 'POST', body });
    if (!res.ok) throw new Error(await res.text());
    const data = await res.json();
    cleanState.sessionId = data.session_id;
    cleanState.entities = data.entities;
    cleanState.excluded = new Set();
    cleanState.customFakes = new Map();
    cleanState.currentFakes = new Map(data.entities.map((e) => [e.id, e.fake]));
    renderEntities();
    showStage('panel-clean', 'clean-preview');
  } catch (err) {
    showCleanError(err);
  }
}

function renderEntities() {
  const body = $('#entity-body');
  body.innerHTML = '';
  $('#entity-count').textContent = `(${cleanState.entities.length})`;
  for (const e of cleanState.entities) {
    const tr = document.createElement('tr');
    tr.dataset.id = e.id;
    tr.dataset.type = e.type;
    tr.innerHTML = `
      <td class="col-check"><input type="checkbox" data-id="${e.id}" checked /></td>
      <td><span class="type-badge">${escapeHtml(e.type)}</span></td>
      <td class="col-original">${escapeHtml(e.original)}${e.aliases.length ? ` <span class="muted">(+${e.aliases.length} alias)</span>` : ''}</td>
      <td class="col-fake">
        <span class="fake-display" tabindex="0">${escapeHtml(e.fake)}</span>
        <span class="fake-warning" hidden></span>
      </td>
      <td class="col-count">${e.occurrences}</td>
    `;
    body.appendChild(tr);
  }
  body.querySelectorAll('input[type="checkbox"]').forEach((cb) => {
    cb.addEventListener('change', onCheckboxChange);
  });
  body.querySelectorAll('.fake-display').forEach((el) => {
    el.addEventListener('click', (e) => beginEdit(e.currentTarget.closest('tr')));
    el.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' || e.key === ' ') {
        e.preventDefault();
        beginEdit(e.currentTarget.closest('tr'));
      }
    });
  });
}

function onCheckboxChange(e) {
  const cb = e.currentTarget;
  const id = cb.dataset.id;
  const tr = cb.closest('tr');
  if (cb.checked) {
    cleanState.excluded.delete(id);
    tr.classList.remove('unchecked');
  } else {
    cleanState.excluded.add(id);
    tr.classList.add('unchecked');
  }
}

function beginEdit(tr) {
  if (!tr) return;
  if (tr.querySelector('.fake-input')) return; // already editing
  const cell = tr.querySelector('.col-fake');
  const display = cell.querySelector('.fake-display');
  const warn = cell.querySelector('.fake-warning');
  const current = display.textContent;
  const id = tr.dataset.id;
  const type = tr.dataset.type;

  const input = document.createElement('input');
  input.type = 'text';
  input.className = 'fake-input';
  input.value = current;
  input.setAttribute('spellcheck', 'false');
  input.setAttribute('autocomplete', 'off');

  display.hidden = true;
  warn.hidden = true;
  cell.insertBefore(input, warn);
  input.focus();
  input.select();

  const commit = () => {
    const newVal = input.value.trim();
    const entry = cleanState.entities.find((e) => e.id === id);
    if (!newVal) {
      // empty → revert
      input.remove();
      display.hidden = false;
      return;
    }
    if (newVal === entry.original) {
      input.remove();
      display.hidden = false;
      showWarn(warn, 'same as original — reverted');
      return;
    }
    // Duplicate detection against other rows' current fakes
    for (const [otherId, otherFake] of cleanState.currentFakes) {
      if (otherId !== id && otherFake === newVal) {
        showWarn(warn, `also used for ${otherId}`);
        break;
      }
    }
    // Soft format validation
    const v = validateForType(type, newVal);
    if (!v.ok) {
      showWarn(warn, v.message);
    }
    display.textContent = newVal;
    display.hidden = false;
    input.remove();
    if (newVal !== entry.fake) {
      cleanState.customFakes.set(id, newVal);
      tr.classList.add('edited');
    } else {
      cleanState.customFakes.delete(id);
      tr.classList.remove('edited');
    }
    cleanState.currentFakes.set(id, newVal);
  };

  const cancel = () => {
    input.remove();
    display.hidden = false;
    warn.hidden = true;
  };

  input.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') { e.preventDefault(); commit(); }
    else if (e.key === 'Escape') { e.preventDefault(); cancel(); }
  });
  input.addEventListener('blur', commit);
}

function showWarn(el, message) {
  el.textContent = `⚠ ${message}`;
  el.hidden = false;
}

$('#select-all').addEventListener('click', () => {
  cleanState.excluded.clear();
  $$('#entity-body input[type="checkbox"]').forEach((cb) => { cb.checked = true; cb.closest('tr').classList.remove('unchecked'); });
});
$('#select-none').addEventListener('click', () => {
  cleanState.excluded = new Set(cleanState.entities.map((e) => e.id));
  $$('#entity-body input[type="checkbox"]').forEach((cb) => { cb.checked = false; cb.closest('tr').classList.add('unchecked'); });
});

$('#finalize-btn').addEventListener('click', async () => {
  showStage('panel-clean', 'clean-processing');
  try {
    const body = new FormData();
    body.append('session_id', cleanState.sessionId);
    body.append('excluded_ids', Array.from(cleanState.excluded).join(','));
    if (cleanState.customFakes.size > 0) {
      body.append('custom_fakes', JSON.stringify(Object.fromEntries(cleanState.customFakes)));
    }
    const res = await fetch('/api/clean/finalize', { method: 'POST', body });
    if (!res.ok) throw new Error(await res.text());
    const data = await res.json();
    $('#download-cleaned').href = data.cleaned_url;
    $('#download-cleaned').setAttribute('download', data.cleaned_name);
    $('#download-cleaned').textContent = `📄 Download ${data.cleaned_name}`;
    $('#download-mapping').href = data.mapping_url;
    $('#download-mapping').setAttribute('download', data.mapping_name);
    $('#download-mapping').textContent = `🗝  Download ${data.mapping_name}`;
    const editCount = cleanState.customFakes.size;
    $('#clean-done-summary').textContent =
      `${data.kept_entity_count} entities substituted` +
      (editCount ? ` (${editCount} custom edit${editCount === 1 ? '' : 's'}).` : '.');
    showStage('panel-clean', 'clean-done');
  } catch (err) {
    showCleanError(err);
  }
});

$('#cancel-btn').addEventListener('click', resetCleanFlow);
$('#clean-again-btn').addEventListener('click', resetCleanFlow);
$('#clean-error-reset').addEventListener('click', resetCleanFlow);

function resetCleanFlow() {
  closeSession(cleanState.sessionId);
  cleanState.sessionId = null;
  cleanState.entities = [];
  cleanState.excluded = new Set();
  cleanState.customFakes = new Map();
  cleanState.currentFakes = new Map();
  $('#file-clean').value = '';
  showStage('panel-clean', 'clean-upload');
}

function showCleanError(err) {
  $('#clean-error-msg').textContent = (err && err.message) || String(err);
  showStage('panel-clean', 'clean-error');
}

// ---- Restore flow -------------------------------------------------------

const restoreState = { doc: null, mapping: null, sessionId: null };

function closeSession(sessionId) {
  if (!sessionId) return;
  try {
    navigator.sendBeacon(`/api/session/${sessionId}/close`);
  } catch (_) {
    fetch(`/api/session/${sessionId}/close`, { method: 'POST', keepalive: true }).catch(() => {});
  }
}

window.addEventListener('beforeunload', () => {
  closeSession(cleanState.sessionId);
  closeSession(restoreState.sessionId);
});

wireDropzone($('#dropzone-restore-doc'), $('#file-restore-doc'), (f) => {
  restoreState.doc = f;
  $('#restore-doc-name').textContent = f.name;
  $('#dropzone-restore-doc').classList.add('has-file');
  updateRestoreButton();
});
wireDropzone($('#dropzone-restore-mapping'), $('#file-restore-mapping'), (f) => {
  restoreState.mapping = f;
  $('#restore-mapping-name').textContent = f.name;
  $('#dropzone-restore-mapping').classList.add('has-file');
  updateRestoreButton();
});

function updateRestoreButton() {
  $('#restore-go').disabled = !(restoreState.doc && restoreState.mapping);
}

$('#restore-go').addEventListener('click', async () => {
  showStage('panel-restore', 'restore-processing');
  try {
    const body = new FormData();
    body.append('document', restoreState.doc);
    body.append('mapping', restoreState.mapping);
    const res = await fetch('/api/restore', { method: 'POST', body });
    if (!res.ok) throw new Error(await res.text());
    const data = await res.json();
    restoreState.sessionId = data.session_id;
    $('#download-restored').href = data.restored_url;
    $('#download-restored').setAttribute('download', data.restored_name);
    $('#download-restored').textContent = `📄 Download ${data.restored_name}`;
    $('#download-audit').href = data.audit_url;
    $('#download-audit').setAttribute('download', data.audit_name);
    $('#download-audit').textContent = `📋 Download ${data.audit_name}`;
    renderRestoreReport(data.report);
    showStage('panel-restore', 'restore-done');
  } catch (err) {
    $('#restore-error-msg').textContent = (err && err.message) || String(err);
    showStage('panel-restore', 'restore-error');
  }
});

function renderRestoreReport(report) {
  const box = $('#restore-report');
  box.innerHTML = '';

  const exactTotal = report.exact.reduce((n, h) => n + (h.count || 1), 0);
  box.appendChild(reportSection(
    `✓ Restored exactly (${exactTotal} occurrence${exactTotal === 1 ? '' : 's'} across ${report.exact.length} entit${report.exact.length === 1 ? 'y' : 'ies'})`,
    'exact',
    report.exact,
    (h) => `
      <span class="type-badge">${escapeHtml(h.type || '')}</span>
      <span class="r-fake">${escapeHtml(h.fake)}</span>
      <span class="r-arrow">→</span>
      <span class="r-original">${escapeHtml(h.original)}</span>
      <span class="muted">×${h.count || 1}</span>`,
    report.exact.length > 0,
  ));

  if (report.fuzzy.length) {
    box.appendChild(reportSection(
      `≈ Fuzzy matches (${report.fuzzy.length}) — review recommended`,
      'fuzzy',
      report.fuzzy,
      (h) => `
        <span class="type-badge">${escapeHtml(h.type || '')}</span>
        <span class="r-fake">“${escapeHtml(h.matched_text)}”</span>
        <span class="r-arrow">→</span>
        <span class="r-original">${escapeHtml(h.original)}</span>
        <span class="muted">(score ${h.score}, expected “${escapeHtml(h.fake || '')}”)</span>`,
      true,
    ));
  }

  if (report.missing.length) {
    box.appendChild(reportSection(
      `✗ Not found in LLM output (${report.missing.length}) — the LLM may have dropped or rewrote these`,
      'missing',
      report.missing,
      (h) => `
        <span class="type-badge">${escapeHtml(h.type || '')}</span>
        <span class="r-fake">${escapeHtml(h.fake)}</span>
        <span class="r-arrow">—</span>
        <span class="r-original">(would have been ${escapeHtml(h.original)})</span>`,
      true,
    ));
  }
}

function reportSection(title, kind, items, renderItem, defaultOpen) {
  const details = document.createElement('details');
  details.className = `report-section ${kind}`;
  if (defaultOpen) details.open = true;
  const summary = document.createElement('summary');
  summary.textContent = title;
  details.appendChild(summary);
  if (items.length === 0) {
    const empty = document.createElement('p');
    empty.className = 'muted';
    empty.textContent = 'None.';
    details.appendChild(empty);
    return details;
  }
  const ul = document.createElement('ul');
  ul.className = 'report-list';
  for (const h of items) {
    const li = document.createElement('li');
    li.innerHTML = renderItem(h);
    ul.appendChild(li);
  }
  details.appendChild(ul);
  return details;
}

$('#restore-again-btn').addEventListener('click', resetRestoreFlow);
$('#restore-error-reset').addEventListener('click', resetRestoreFlow);

function resetRestoreFlow() {
  closeSession(restoreState.sessionId);
  restoreState.sessionId = null;
  restoreState.doc = null;
  restoreState.mapping = null;
  $('#file-restore-doc').value = '';
  $('#file-restore-mapping').value = '';
  $('#restore-doc-name').textContent = '.docx, .txt, or .md';
  $('#restore-mapping-name').textContent = '_MAPPING.json';
  $('#dropzone-restore-doc').classList.remove('has-file');
  $('#dropzone-restore-mapping').classList.remove('has-file');
  updateRestoreButton();
  showStage('panel-restore', 'restore-upload');
}

// ---- Utilities ----------------------------------------------------------

function escapeHtml(s) {
  return String(s)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}
