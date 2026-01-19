(function () {
    const STORAGE_KEY = 'fastsplit_font_scale';
    const CONTRAST_KEY = 'fastsplit_high_contrast';

    // Apply contrast immediately (before DOMContentLoaded)
    try {
        const contrastEnabled = localStorage.getItem(CONTRAST_KEY) === 'true';
        if (contrastEnabled) {
            document.documentElement.classList.add('high-contrast');
            if (document.body) {
                document.body.classList.add('high-contrast');
            }
        }
    } catch (e) {
        // ignore
    }

    const clampScale = (value) => {
        const n = Number(value);
        if (!Number.isFinite(n)) return 1;
        return Math.min(1.5, Math.max(0.75, n));
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

    const getContrastMode = () => {
        try {
            return localStorage.getItem(CONTRAST_KEY) === 'true';
        } catch (e) {
            return false;
        }
    };

    const saveContrastMode = (enabled) => {
        try {
            localStorage.setItem(CONTRAST_KEY, String(enabled));
        } catch (e) {
            // ignore
        }
    };

    const applyContrastMode = (enabled) => {
        if (enabled) {
            document.documentElement.classList.add('high-contrast');
            document.body.classList.add('high-contrast');
        } else {
            document.documentElement.classList.remove('high-contrast');
            document.body.classList.remove('high-contrast');
        }

        // Update button state
        const contrastBtn = document.querySelector('[data-contrast-toggle]');
        if (contrastBtn) {
            contrastBtn.setAttribute('aria-pressed', String(enabled));
        }
    };

    document.addEventListener('DOMContentLoaded', () => {
        // Apply saved font scale
        const saved = getSavedScale();
        if (saved) applyScale(saved);
        else applyScale(1);

        // Apply saved contrast mode
        const contrastEnabled = getContrastMode();
        applyContrastMode(contrastEnabled);

        // Wire font controls (if present)
        document.addEventListener('click', (e) => {
            const btn = e.target && e.target.closest ? e.target.closest('[data-font-scale]') : null;
            if (!btn) return;
            const scale = btn.getAttribute('data-font-scale');
            applyScale(scale);
            saveScale(scale);
        });

        // Wire contrast toggle
        document.addEventListener('click', (e) => {
            const btn = e.target && e.target.closest ? e.target.closest('[data-contrast-toggle]') : null;
            if (!btn) return;
            const currentState = getContrastMode();
            const newState = !currentState;
            applyContrastMode(newState);
            saveContrastMode(newState);
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
