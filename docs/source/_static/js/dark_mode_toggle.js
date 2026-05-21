// Dark mode toggle functionality for Sphinx RTD theme
(function() {
    const DARK_MODE_KEY = 'sphinx-dark-mode';
    const html = document.documentElement;

    // Safe storage helpers — wrap localStorage access in try/catch
    function safeGetItem(key) {
        try {
            return localStorage.getItem(key);
        } catch (e) {
            return null;
        }
    }

    function safeSetItem(key, value) {
        try {
            localStorage.setItem(key, value);
            return true;
        } catch (e) {
            return false;
        }
    }

    // Determine initial dark mode state
    function getDarkModePreference() {
        // Check storage first (safe wrapper)
        const saved = safeGetItem(DARK_MODE_KEY);
        if (saved !== null) {
            return saved === 'true';
        }
        // Fall back to system preference
        return window.matchMedia('(prefers-color-scheme: dark)').matches;
    }

    // Apply dark mode class to document
    function applyDarkMode(isDark) {
        if (isDark) {
            html.classList.add('dark-mode');
        } else {
            html.classList.remove('dark-mode');
        }
        safeSetItem(DARK_MODE_KEY, isDark);
    }

    // Initialize dark mode on page load
    function initDarkMode() {
        const isDarkMode = getDarkModePreference();
        applyDarkMode(isDarkMode);
    }

    // Create and insert toggle button
    function createToggleButton() {
        const button = document.createElement('button');
        button.id = 'dark-mode-toggle';
        button.className = 'dark-mode-toggle';
        button.setAttribute('aria-label', 'Toggle dark mode');
        button.setAttribute('title', 'Toggle dark mode');
        button.innerHTML = html.classList.contains('dark-mode') ? '☀️' : '🌙';
        
        button.addEventListener('click', function(e) {
            e.preventDefault();
            const isDarkMode = html.classList.contains('dark-mode');
            applyDarkMode(!isDarkMode);
            button.innerHTML = !isDarkMode ? '☀️' : '🌙';
        });

        return button;
    }

    // Insert toggle button into page
    function insertToggleButton() {
        // Remove existing button if present
        const existing = document.getElementById('dark-mode-toggle');
        if (existing) {
            existing.remove();
        }

        const button = createToggleButton();
        document.body.appendChild(button);
    }

    // Listen for system preference changes
    if (window.matchMedia) {
        window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', function(e) {
            if (safeGetItem(DARK_MODE_KEY) === null) {
                applyDarkMode(e.matches);
            }
        });
    }

    // Initialize when DOM is ready
    function ready() {
        initDarkMode();
        insertToggleButton();
    }

    if (document.readyState !== 'loading') {
        ready();
    } else {
        document.addEventListener('DOMContentLoaded', ready);
    }
})();
