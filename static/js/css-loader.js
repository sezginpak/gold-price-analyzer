/**
 * CSS Module Loader - Dynamic CSS loading for components
 */

class CSSModuleLoader {
    constructor() {
        this.loadedModules = new Set();
    }

    /**
     * Load a CSS module dynamically
     * @param {string} moduleName - Name of the CSS module to load
     * @returns {Promise<void>}
     */
    async loadModule(moduleName) {
        if (this.loadedModules.has(moduleName)) {
            return;
        }

        try {
            const link = document.createElement('link');
            link.rel = 'stylesheet';
            link.href = `/static/css/modules/${moduleName}.css`;
            
            // Create a promise that resolves when the CSS is loaded
            const loadPromise = new Promise((resolve, reject) => {
                link.onload = () => {
                    this.loadedModules.add(moduleName);
                    resolve();
                };
                link.onerror = () => reject(new Error(`Failed to load CSS module: ${moduleName}`));
            });

            document.head.appendChild(link);
            await loadPromise;
        } catch (error) {
            console.error('CSS Module loading error:', error);
        }
    }

    /**
     * Load multiple CSS modules
     * @param {string[]} modules - Array of module names
     * @returns {Promise<void>}
     */
    async loadModules(modules) {
        const promises = modules.map(module => this.loadModule(module));
        await Promise.all(promises);
    }

    /**
     * Check if a module is loaded
     * @param {string} moduleName - Name of the module
     * @returns {boolean}
     */
    isLoaded(moduleName) {
        return this.loadedModules.has(moduleName);
    }

    /**
     * Apply CSS class with module prefix
     * @param {HTMLElement} element - Element to apply class to
     * @param {string} className - Class name
     * @param {string} module - Module prefix
     */
    addClass(element, className, module = '') {
        if (module) {
            element.classList.add(`${module}__${className}`);
        } else {
            element.classList.add(className);
        }
    }

    /**
     * Create element with CSS module classes
     * @param {string} tag - HTML tag
     * @param {string[]} classes - Array of classes
     * @param {string} module - Module prefix
     * @returns {HTMLElement}
     */
    createElement(tag, classes = [], module = '') {
        const element = document.createElement(tag);
        classes.forEach(cls => this.addClass(element, cls, module));
        return element;
    }
}

// Export singleton instance
const cssLoader = new CSSModuleLoader();
window.cssLoader = cssLoader;