/* In-app replacements for confirm() and alert().
 *
 * The browser draws confirm()/alert() itself, so they cannot match the
 * app. These are drawn in the app's style instead. Unlike the native
 * ones they cannot pause the page, so they return a Promise and are
 * awaited:
 *
 *   if (!(await uiConfirm({ title, message, ok: 'Sil', danger: true }))) return;
 *   await uiAlert({ title, message });
 *
 * A plain string works too: uiConfirm('Emin misin?').
 */
(function () {
  const ACCENT = 'var(--da, var(--accent, #6366f1))';
  const css = `
    .ui-dlg-back {
      position: fixed; inset: 0; z-index: 1400;     /* above modals, drawer, pickers */
      background: rgba(0,0,0,.55);
      backdrop-filter: blur(3px);
      display: flex; align-items: center; justify-content: center;
      padding: 16px;
      opacity: 0; transition: opacity .15s ease;
    }
    .ui-dlg-back.open { opacity: 1; }
    .ui-dlg {
      width: 100%; max-width: 420px;
      background: var(--bg-secondary);
      border: 1px solid var(--border);
      border-radius: 18px;
      padding: 22px 22px 18px;
      box-shadow: 0 20px 60px rgba(0,0,0,.55);
      font-family: 'Outfit', sans-serif;
      transform: translateY(10px) scale(.97);
      transition: transform .18s ease;
    }
    .ui-dlg-back.open .ui-dlg { transform: translateY(0) scale(1); }
    .ui-dlg-title {
      display: flex; align-items: center; gap: 10px;
      font-size: 1.02rem; font-weight: 700; color: var(--text-primary);
      margin-bottom: 10px;
    }
    .ui-dlg-icon {
      width: 30px; height: 30px; flex-shrink: 0;
      display: flex; align-items: center; justify-content: center;
      border-radius: 50%; font-size: .95rem; font-weight: 700;
      background: color-mix(in srgb, ${ACCENT} 16%, transparent); color: ${ACCENT};
    }
    .ui-dlg.danger .ui-dlg-icon { background: rgba(239,68,68,.15); color: #ef4444; }
    .ui-dlg-msg {
      font-size: .87rem; line-height: 1.55; color: var(--text-secondary);
      white-space: pre-line; overflow-wrap: anywhere;
    }
    .ui-dlg-foot { display: flex; justify-content: flex-end; gap: 8px; margin-top: 20px; flex-wrap: wrap; }
    .ui-dlg-btn {
      min-height: 40px; padding: 9px 18px;
      border-radius: 10px; border: 1px solid var(--border);
      background: var(--bg-card); color: var(--text-secondary);
      font-family: 'Outfit', sans-serif; font-size: .86rem; font-weight: 600;
      cursor: pointer; transition: filter .15s, background .15s, color .15s;
    }
    .ui-dlg-btn:hover { color: var(--text-primary); background: var(--bg-card-hover); }
    .ui-dlg-btn.ok { background: ${ACCENT}; border-color: transparent; color: #fff; }
    .ui-dlg-btn.ok:hover { filter: brightness(1.1); color: #fff; background: ${ACCENT}; }
    .ui-dlg.danger .ui-dlg-btn.ok { background: #dc2626; }
    .ui-dlg.danger .ui-dlg-btn.ok:hover { background: #ef4444; }
    .ui-dlg-btn:focus-visible { outline: 2px solid ${ACCENT}; outline-offset: 2px; }
    @media (max-width: 480px) {
      .ui-dlg-foot { flex-direction: column-reverse; }
      .ui-dlg-btn { width: 100%; min-height: 44px; }
    }
  `;
  const style = document.createElement('style');
  style.textContent = css;
  document.head.appendChild(style);

  // One dialog at a time; later requests wait their turn
  let queue = Promise.resolve();
  let active = null;

  function show(kind, opts) {
    if (typeof opts === 'string') opts = { message: opts };
    const run = () => new Promise(resolve => {
      const back = document.createElement('div');
      back.className = 'ui-dlg-back';
      const dlg = document.createElement('div');
      dlg.className = 'ui-dlg' + (opts.danger ? ' danger' : '');
      dlg.setAttribute('role', kind === 'confirm' ? 'alertdialog' : 'dialog');
      dlg.setAttribute('aria-modal', 'true');
      const id = 'ui-dlg-' + Date.now();
      dlg.setAttribute('aria-labelledby', id + '-t');
      dlg.setAttribute('aria-describedby', id + '-m');
      const icon = opts.danger ? '!' : (kind === 'confirm' ? '?' : 'i');
      dlg.innerHTML = `
        <div class="ui-dlg-title" id="${id}-t"><span class="ui-dlg-icon" aria-hidden="true">${icon}</span><span></span></div>
        <div class="ui-dlg-msg" id="${id}-m"></div>
        <div class="ui-dlg-foot">
          ${kind === 'confirm' ? '<button type="button" class="ui-dlg-btn cancel"></button>' : ''}
          <button type="button" class="ui-dlg-btn ok"></button>
        </div>`;
      // textContent throughout: messages quote task titles
      dlg.querySelector('.ui-dlg-title span:last-child').textContent =
        opts.title || (kind === 'confirm' ? 'Onayla' : 'Bilgi');
      dlg.querySelector('.ui-dlg-msg').textContent = opts.message || '';
      const okBtn = dlg.querySelector('.ok');
      const cancelBtn = dlg.querySelector('.cancel');
      okBtn.textContent = opts.ok || (kind === 'confirm' ? 'Devam' : 'Tamam');
      if (cancelBtn) cancelBtn.textContent = opts.cancel || 'Vazgeç';

      back.appendChild(dlg);
      document.body.appendChild(back);
      const prevFocus = document.activeElement;

      const finish = result => {
        document.removeEventListener('keydown', onKey, true);
        back.classList.remove('open');
        setTimeout(() => back.remove(), 160);
        active = null;
        if (prevFocus && prevFocus.focus && document.contains(prevFocus)) prevFocus.focus({ preventScroll: true });
        resolve(result);
      };

      // Capture phase, and stopped there: the daily page binds Enter to
      // "save task" and Escape to "close every modal", and neither may
      // fire while this dialog is answering for them.
      const onKey = e => {
        if (e.key === 'Escape') { e.preventDefault(); e.stopImmediatePropagation(); finish(false); }
        else if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault(); e.stopImmediatePropagation();
          finish(document.activeElement === cancelBtn ? false : true);
        } else if (e.key === 'Tab') {
          // keep focus inside the dialog
          e.preventDefault(); e.stopImmediatePropagation();
          const btns = [cancelBtn, okBtn].filter(Boolean);
          const i = btns.indexOf(document.activeElement);
          btns[(i + (e.shiftKey ? -1 : 1) + btns.length) % btns.length].focus();
        } else {
          e.stopImmediatePropagation();
        }
      };
      document.addEventListener('keydown', onKey, true);
      okBtn.addEventListener('click', () => finish(true));
      if (cancelBtn) cancelBtn.addEventListener('click', () => finish(false));
      back.addEventListener('mousedown', e => { if (e.target === back) finish(kind === 'confirm' ? false : true); });

      active = back;
      requestAnimationFrame(() => back.classList.add('open'));
      // Destructive actions start on "Vazgeç", so a stray Enter cannot delete
      (opts.danger && cancelBtn ? cancelBtn : okBtn).focus({ preventScroll: true });
    });
    const p = queue.then(run);
    queue = p.catch(() => {});
    return p;
  }

  window.uiConfirm = opts => show('confirm', opts).then(Boolean);
  window.uiAlert   = opts => show('alert', opts).then(() => undefined);
})();
