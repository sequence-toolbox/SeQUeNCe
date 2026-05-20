// Dark mode toggle functionality for Sphinx RTD theme
(function() {
    const DARK_MODE_KEY = 'sphinx-dark-mode';
    const html = document.documentElement;

    // Determine initial dark mode state
    function getDarkModePreference() {
        // Check localStorage first
        const saved = localStorage.getItem(DARK_MODE_KEY);
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
        localStorage.setItem(DARK_MODE_KEY, isDark);
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
        button.setAttribute('title', 'Toggle dark mode (d)');
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

    // Keyboard shortcut: 'd' key
    document.addEventListener('keydown', function(e) {
        if ((e.key === 'd' || e.key === 'D') && e.ctrlKey) {
            e.preventDefault();
            const isDarkMode = html.classList.contains('dark-mode');
            applyDarkMode(!isDarkMode);
            const button = document.getElementById('dark-mode-toggle');
            if (button) {
                button.innerHTML = !isDarkMode ? '☀️' : '🌙';
            }
        }
    });

    // Listen for system preference changes
    if (window.matchMedia) {
        window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', function(e) {
            if (localStorage.getItem(DARK_MODE_KEY) === null) {
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
