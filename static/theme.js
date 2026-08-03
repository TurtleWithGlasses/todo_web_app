// Shared appearance picker for TaskFlow + Günlük İş Takibi.
// Two independent choices, both persisted in localStorage so they
// carry over across both pages:
//  - 'appTheme'  → accent color (data-theme attribute)
//  - 'appBgMode' → background brightness (data-bg attribute)
// 'classic' / 'dark' mean "no override" — each page's original
// built-in values apply.
(function () {
  const THEME_KEY = 'appTheme';
  const BG_KEY    = 'appBgMode';

  const THEMES = [
    { id: 'classic', name: 'Klasik',         accent: '#f59e0b', accent2: '#06b6d4' },
    { id: 'teal',    name: 'Teal Dream',     accent: '#06b6d4', accent2: '#10b981' },
    { id: 'sunset',  name: 'Sunset Amber',   accent: '#f59e0b', accent2: '#ef4444' },
    { id: 'violet',  name: 'Violet Nights',  accent: '#a78bfa', accent2: '#ec4899' },
    { id: 'emerald', name: 'Emerald Forest', accent: '#10b981', accent2: '#06b6d4' },
    { id: 'rose',    name: 'Rose Quartz',    accent: '#f43f5e', accent2: '#a78bfa' },
    { id: 'ocean',   name: 'Ocean Blue',     accent: '#3b82f6', accent2: '#10b981' },
  ];

  const BG_MODES = [
    { id: 'dark',       name: 'Koyu',      swatch: '#0f1419' },
    { id: 'mid-gray',   name: 'Orta Gri',  swatch: '#c7cdd4' },
    { id: 'light-gray', name: 'Açık Gri',  swatch: '#e5e9ee' },
    { id: 'pale-gray',  name: 'Gri Beyaz', swatch: '#f0f2f4' },
    { id: 'white',      name: 'Beyaz',     swatch: '#f6f7f9' },
  ];

  function getSavedTheme()  { return localStorage.getItem(THEME_KEY) || 'classic'; }
  function getSavedBgMode() { return localStorage.getItem(BG_KEY) || 'dark'; }

  function applyThemeAttr(id) {
    if (id === 'classic') document.documentElement.removeAttribute('data-theme');
    else document.documentElement.setAttribute('data-theme', id);
  }
  function applyBgAttr(id) {
    if (id === 'dark') document.documentElement.removeAttribute('data-bg');
    else document.documentElement.setAttribute('data-bg', id);
  }

  function applyTheme(id) {
    applyThemeAttr(id);
    localStorage.setItem(THEME_KEY, id);
    document.dispatchEvent(new CustomEvent('themechange', { detail: { theme: id } }));
  }
  function applyBgMode(id) {
    applyBgAttr(id);
    localStorage.setItem(BG_KEY, id);
    document.dispatchEvent(new CustomEvent('themechange', { detail: { bg: id } }));
  }

  // Keep in sync if changed from another tab
  window.addEventListener('storage', e => {
    if (e.key === THEME_KEY) applyThemeAttr(getSavedTheme());
    if (e.key === BG_KEY)    applyBgAttr(getSavedBgMode());
  });

  function mountThemePicker(containerId) {
    const container = document.getElementById(containerId);
    if (!container) return;

    container.classList.add('theme-picker-wrap');
    const currentTheme = getSavedTheme();
    const currentBg    = getSavedBgMode();

    const btn = document.createElement('button');
    btn.type = 'button';
    btn.className = 'theme-btn';
    btn.title = 'Görünümü özelleştir';
    btn.innerHTML = '<span class="theme-btn-dot"></span> Görünüm';

    const pop = document.createElement('div');
    pop.className = 'theme-popover';
    pop.innerHTML = `
      <div class="theme-section-label">Renk</div>
      ${THEMES.map(t => `
        <button type="button" class="theme-swatch-btn${t.id === currentTheme ? ' active' : ''}" data-theme-id="${t.id}">
          <span class="theme-swatch" style="background:linear-gradient(135deg, ${t.accent}, ${t.accent2})"></span>
          <span class="theme-swatch-label">${t.name}</span>
        </button>
      `).join('')}
      <div class="theme-section-label theme-section-label-2">Arka Plan</div>
      ${BG_MODES.map(m => `
        <button type="button" class="theme-swatch-btn${m.id === currentBg ? ' active' : ''}" data-bg-id="${m.id}">
          <span class="theme-swatch theme-swatch-square" style="background:${m.swatch}"></span>
          <span class="theme-swatch-label">${m.name}</span>
        </button>
      `).join('')}
    `;

    container.appendChild(btn);
    container.appendChild(pop);

    btn.addEventListener('click', e => {
      e.stopPropagation();
      pop.classList.toggle('open');
    });
    document.addEventListener('click', e => {
      if (!pop.contains(e.target) && e.target !== btn) pop.classList.remove('open');
    });
    document.addEventListener('keydown', e => {
      if (e.key === 'Escape') pop.classList.remove('open');
    });
    pop.querySelectorAll('[data-theme-id]').forEach(swBtn => {
      swBtn.addEventListener('click', () => {
        applyTheme(swBtn.dataset.themeId);
        pop.querySelectorAll('[data-theme-id]').forEach(b => b.classList.remove('active'));
        swBtn.classList.add('active');
      });
    });
    pop.querySelectorAll('[data-bg-id]').forEach(bgBtn => {
      bgBtn.addEventListener('click', () => {
        applyBgMode(bgBtn.dataset.bgId);
        pop.querySelectorAll('[data-bg-id]').forEach(b => b.classList.remove('active'));
        bgBtn.classList.add('active');
      });
    });
  }

  // Safety net in case the inline head snippet was skipped/blocked
  applyThemeAttr(getSavedTheme());
  applyBgAttr(getSavedBgMode());

  window.AppTheme = { THEMES, BG_MODES, getSavedTheme, getSavedBgMode, applyTheme, applyBgMode, mountThemePicker };
})();
