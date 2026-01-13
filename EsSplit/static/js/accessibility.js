(function () {
    const STORAGE_KEY = 'fastsplit_font_scale';

    const clampScale = (value) => {
        const n = Number(value);
        if (!Number.isFinite(n)) return 1;
        return Math.min(1.15, Math.max(0.9, n));
    };

    const applyScale = (scale) => {
        const safe = clampScale(scale);
        document.documentElement.style.setProperty('--fastsplit-font-scale', String(safe));

        // Update button pressed state (if controls exist on this page)
        const buttons = document.querySelectorAll('[data-font-scale]');
        buttons.forEach((btn) => {
            const btnScale = clampScale(btn.getAttribute('data-font-scale'));
            btn.setAttribute('aria-pressed', String(btnScale === safe));
        });
    };

    const getSavedScale = () => {
        try {
            return localStorage.getItem(STORAGE_KEY);
        } catch (e) {
            return null;
        }
    };

    const saveScale = (scale) => {
        try {
            localStorage.setItem(STORAGE_KEY, String(clampScale(scale)));
        } catch (e) {
            // ignore
        }
    };

    document.addEventListener('DOMContentLoaded', () => {
        // Apply saved setting
        const saved = getSavedScale();
        if (saved) applyScale(saved);
        else applyScale(1);

        // Wire controls (if present)
        document.addEventListener('click', (e) => {
            const btn = e.target && e.target.closest ? e.target.closest('[data-font-scale]') : null;
            if (!btn) return;
            const scale = btn.getAttribute('data-font-scale');
            applyScale(scale);
            saveScale(scale);
        });

        // Back button: always go to login (via href)
        document.addEventListener('click', (e) => {
            const back = e.target && e.target.closest ? e.target.closest('[data-fastsplit-back]') : null;
            if (!back) return;
            e.preventDefault();

            const href = back.getAttribute('href') || '/';
            window.location.href = href;
        });
    });
})();
