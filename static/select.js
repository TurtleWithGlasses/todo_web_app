/* In-app dropdowns.
 *
 * A native <select> opens a list the browser draws itself, which CSS
 * cannot restyle, so it clashes with the app. Each <select> is replaced
 * on screen by a button that opens a list drawn in the app's style.
 *
 * The real <select> stays in the page, hidden, and remains the source
 * of truth: code that reads or sets .value, rebuilds the options with
 * innerHTML or listens for onchange keeps working unchanged. Picking an
 * option sets the select's value and fires input + change like a real
 * one. Selects added later (panels rendered with innerHTML) are picked
 * up automatically.
 */
(function () {
  const VALUE = Object.getOwnPropertyDescriptor(HTMLSelectElement.prototype, 'value');
  const INDEX = Object.getOwnPropertyDescriptor(HTMLSelectElement.prototype, 'selectedIndex');
  const ACCENT = 'var(--da, var(--accent, #6366f1))';
  const CHEVRON = '<svg class="ui-sel-chev" width="12" height="8" viewBox="0 0 12 8" aria-hidden="true">' +
                  '<path d="M1 1.5 6 6.5 11 1.5" fill="none" stroke="currentColor" stroke-width="2" ' +
                  'stroke-linecap="round" stroke-linejoin="round"/></svg>';

  const css = `
    .ui-sel {
      display: flex; align-items: center; justify-content: space-between; gap: 8px;
      text-align: left; cursor: pointer;
      font-weight: 400;                    /* a select's weight, not a button's */
      background-image: none !important;   /* the .d-fs chevron is drawn below instead */
      min-width: 0;
    }
    .ui-sel-text { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; min-width: 0; }
    .ui-sel-chev { flex-shrink: 0; color: var(--text-muted); transition: transform .15s, color .15s; }
    .ui-sel:hover .ui-sel-chev { color: var(--text-secondary); }
    .ui-sel.open { border-color: ${ACCENT} !important; }
    .ui-sel.open .ui-sel-chev { transform: rotate(180deg); color: ${ACCENT}; }
    .ui-sel:disabled { opacity: .5; cursor: default; }

    .ui-sel-pop {
      position: fixed; z-index: 1300;        /* above modals (1000) and the mobile drawer (1200) */
      background: var(--bg-secondary);
      border: 1px solid var(--border);
      border-radius: 12px;
      padding: 5px;
      box-shadow: 0 16px 44px rgba(0,0,0,.5);
      overflow-y: auto;
      opacity: 0; pointer-events: none;
      transform: translateY(-4px);
      transition: opacity .13s ease, transform .13s ease;
      font-family: 'Outfit', sans-serif;
    }
    .ui-sel-pop.open { opacity: 1; pointer-events: all; transform: translateY(0); }
    .ui-sel-opt {
      display: flex; align-items: center; gap: 8px;
      padding: 8px 10px; min-height: 36px;
      border-radius: 8px;
      font-size: .84rem; color: var(--text-secondary);
      cursor: pointer; user-select: none;
    }
    .ui-sel-opt .ui-sel-label { flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
    .ui-sel-opt.active { background: var(--bg-card-hover); color: var(--text-primary); }
    .ui-sel-opt.sel { color: ${ACCENT}; font-weight: 600; }
    .ui-sel-opt .ui-sel-tick { width: 14px; flex-shrink: 0; visibility: hidden; }
    .ui-sel-opt.sel .ui-sel-tick { visibility: visible; }
    .ui-sel-opt.disabled { opacity: .45; cursor: default; }
    .ui-sel-empty { padding: 10px; font-size: .8rem; color: var(--text-muted); }
  `;
  const style = document.createElement('style');
  style.textContent = css;
  document.head.appendChild(style);

  let pop = null, cur = null, active = -1, typed = '', typedAt = 0;

  function labelOf(sel) {
    const o = sel.options[INDEX.get.call(sel)];
    return o ? o.textContent.trim() : '';
  }

  function sync(sel) {
    const btn = sel._uiSel;
    if (!btn) return;
    btn.querySelector('.ui-sel-text').textContent = labelOf(sel) || ' ';
    btn.disabled = sel.disabled;
    btn.title = sel.title || labelOf(sel);
    if (cur === sel) render();
  }

  function enhance(sel) {
    if (sel._uiSel || sel.multiple || sel.size > 1 || sel.dataset.native !== undefined) return;
    const btn = document.createElement('button');
    btn.type = 'button';
    // Same classes as the select, so its sizing and spacing carry over
    btn.className = (sel.className ? sel.className + ' ' : '') + 'ui-sel';
    btn.setAttribute('aria-haspopup', 'listbox');
    btn.setAttribute('aria-expanded', 'false');
    btn.innerHTML = '<span class="ui-sel-text"></span>' + CHEVRON;
    sel.style.display = 'none';
    sel.parentNode.insertBefore(btn, sel);
    sel._uiSel = btn;

    // Assignments from code (sel.value = x, sel.selectedIndex = n) refresh the label
    Object.defineProperty(sel, 'value', {
      configurable: true,
      get() { return VALUE.get.call(this); },
      set(v) { VALUE.set.call(this, v); sync(this); },
    });
    Object.defineProperty(sel, 'selectedIndex', {
      configurable: true,
      get() { return INDEX.get.call(this); },
      set(v) { INDEX.set.call(this, v); sync(this); },
    });
    // Options rebuilt with innerHTML, or attributes toggled
    new MutationObserver(() => sync(sel))
      .observe(sel, { childList: true, subtree: true, attributes: true, characterData: true });

    btn.addEventListener('click', () => (cur === sel ? close() : open(sel)));
    btn.addEventListener('keydown', e => {
      if (['ArrowDown', 'ArrowUp', 'Enter', ' '].includes(e.key) && cur !== sel) {
        e.preventDefault(); open(sel);
      }
    });
    sync(sel);
  }

  function open(sel) {
    close();
    if (!pop) {
      pop = document.createElement('div');
      pop.className = 'ui-sel-pop';
      pop.setAttribute('role', 'listbox');
      document.body.appendChild(pop);
      pop.addEventListener('mousedown', e => e.preventDefault());   // keep focus on the button
      pop.addEventListener('click', e => {
        const o = e.target.closest('.ui-sel-opt');
        if (o && !o.classList.contains('disabled')) choose(+o.dataset.i);
      });
      pop.addEventListener('mousemove', e => {
        const o = e.target.closest('.ui-sel-opt');
        if (o && +o.dataset.i !== active && !o.classList.contains('disabled')) { active = +o.dataset.i; mark(); }
      });
    }
    cur = sel;
    active = INDEX.get.call(sel);
    sel._uiSel.classList.add('open');
    sel._uiSel.setAttribute('aria-expanded', 'true');
    render();
    place();
    pop.classList.add('open');
    scrollToActive();
  }

  function close(refocus) {
    if (!cur) return;
    pop.classList.remove('open');
    cur._uiSel.classList.remove('open');
    cur._uiSel.setAttribute('aria-expanded', 'false');
    if (refocus) cur._uiSel.focus({ preventScroll: true });
    cur = null;
  }

  function render() {
    const opts = [...cur.options];
    const si = INDEX.get.call(cur);
    pop.innerHTML = opts.length
      ? opts.map((o, i) => `
          <div class="ui-sel-opt${i === si ? ' sel' : ''}${i === active ? ' active' : ''}${o.disabled ? ' disabled' : ''}"
               role="option" data-i="${i}" aria-selected="${i === si}">
            <svg class="ui-sel-tick" width="14" height="10" viewBox="0 0 14 10" aria-hidden="true">
              <path d="M1.5 5.2 5.2 8.5 12.5 1.5" fill="none" stroke="currentColor" stroke-width="2"
                    stroke-linecap="round" stroke-linejoin="round"/></svg>
            <span class="ui-sel-label"></span>
          </div>`).join('')
      : '<div class="ui-sel-empty">Seçenek yok</div>';
    // Labels via textContent: option text is user data (task titles)
    pop.querySelectorAll('.ui-sel-label').forEach((el, i) => { el.textContent = opts[i].textContent.trim(); });
  }

  function mark() {
    pop.querySelectorAll('.ui-sel-opt').forEach(el => el.classList.toggle('active', +el.dataset.i === active));
  }

  function scrollToActive() {
    const el = pop.querySelector(`.ui-sel-opt[data-i="${active}"]`);
    if (el) el.scrollIntoView({ block: 'nearest' });
  }

  // Under the button, or above it when there is no room; never off screen
  function place() {
    const r = cur._uiSel.getBoundingClientRect(), m = 8;
    pop.style.maxHeight = '';
    pop.style.minWidth = r.width + 'px';
    pop.style.maxWidth = Math.max(r.width, Math.min(360, window.innerWidth - 2 * m)) + 'px';
    const below = window.innerHeight - r.bottom - m - 6;
    const above = r.top - m - 6;
    const want = Math.min(pop.scrollHeight, 300);
    const up = want > below && above > below;
    const room = Math.max(120, up ? above : below);
    pop.style.maxHeight = Math.min(300, room) + 'px';
    const h = pop.offsetHeight, w = pop.offsetWidth;
    let top = up ? r.top - 6 - h : r.bottom + 6;
    top = Math.max(m, Math.min(top, window.innerHeight - h - m));
    pop.style.top = top + 'px';
    pop.style.left = Math.max(m, Math.min(r.left, window.innerWidth - w - m)) + 'px';
  }

  function choose(i) {
    const sel = cur;
    const changed = INDEX.get.call(sel) !== i;
    INDEX.set.call(sel, i);
    sync(sel);
    close(true);
    if (changed) {
      sel.dispatchEvent(new Event('input',  { bubbles: true }));
      sel.dispatchEvent(new Event('change', { bubbles: true }));
    }
  }

  function step(dir) {
    const opts = cur.options;
    let i = active;
    for (let n = 0; n < opts.length; n++) {
      i = Math.max(0, Math.min(opts.length - 1, i + dir));
      if (!opts[i].disabled) break;
    }
    active = i; mark(); scrollToActive();
  }

  document.addEventListener('click', e => {
    if (!cur) return;
    if (e.target.closest('.ui-sel-pop') || cur._uiSel.contains(e.target)) return;
    close();
  });

  // Capture phase: Escape closes the list only, not the dialog under it
  // (the daily page's Escape handler closes every open modal).
  document.addEventListener('keydown', e => {
    if (!cur) return;
    const k = e.key;
    if (k === 'Escape') { e.preventDefault(); e.stopImmediatePropagation(); close(true); return; }
    if (k === 'Tab') { close(); return; }
    if (k === 'ArrowDown' || k === 'ArrowUp') { e.preventDefault(); e.stopImmediatePropagation(); step(k === 'ArrowDown' ? 1 : -1); return; }
    if (k === 'Home' || k === 'End') { e.preventDefault(); active = k === 'Home' ? -1 : cur.options.length; step(k === 'Home' ? 1 : -1); return; }
    if (k === 'Enter' || k === ' ') {
      e.preventDefault(); e.stopImmediatePropagation();
      if (active >= 0 && cur.options[active] && !cur.options[active].disabled) choose(active);
      return;
    }
    // Type to jump: matches the start of an option, Turkish-aware
    if (k.length === 1 && !e.ctrlKey && !e.metaKey && !e.altKey) {
      const now = Date.now();
      typed = (now - typedAt < 700 ? typed : '') + k.toLocaleLowerCase('tr');
      typedAt = now;
      const opts = [...cur.options];
      const hit = opts.findIndex(o => !o.disabled &&
        o.textContent.trim().replace(/^[^\p{L}\p{N}]+/u, '').toLocaleLowerCase('tr').startsWith(typed));
      if (hit >= 0) { active = hit; mark(); scrollToActive(); }
    }
  }, true);

  window.addEventListener('resize', () => cur && place());
  document.addEventListener('scroll', e => {
    if (!cur || (pop && pop.contains(e.target))) return;
    const r = cur._uiSel.getBoundingClientRect();
    if (r.bottom < 0 || r.top > window.innerHeight) close(); else place();
  }, true);

  function scan(root) {
    if (root.tagName === 'SELECT') enhance(root);
    else if (root.querySelectorAll) root.querySelectorAll('select').forEach(enhance);
  }
  function start() {
    scan(document.body);
    new MutationObserver(muts => muts.forEach(m => m.addedNodes.forEach(n => n.nodeType === 1 && scan(n))))
      .observe(document.body, { childList: true, subtree: true });
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', start);
  else start();
})();
