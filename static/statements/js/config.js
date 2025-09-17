// Global configuration and data storage - Production Version
window.StatementsApp = {
    /**
     * Account IDs from unified accounts configuration
     * @type {string[]}
     */
    accountIds: [
        'stp_sa', 
        'stp_ip_pi', 
        'stp_ip_pd', 
        'bbva_mx_mxn', 
        'bbva_mx_usd', 
        'bbva_sa_mxn', 
        'bbva_sa_usd', 
        'bbva_ip_corp', 
        'bbva_ip_clientes'
    ],
    
    /**
     * Data storage by year
     * @type {Object}
     */
    accountDataByYear: {},
    
    /**
     * Current year from template or URL
     * @type {number|null}
     */
    currentYear: null,
    
    /**
     * Environment configuration
     * @type {string}
     */
    environment: 'production',
    
    /**
     * API base URL (set based on environment)
     * @type {string}
     */
    apiBaseUrl: '',
    
    /**
     * Initialize application configuration
     * @param {string|number} templateYear - Year from template
     */
    init: function(templateYear) {
        // Set environment based on hostname
        this.environment = this.detectEnvironment();
        this.apiBaseUrl = this.getApiBaseUrl();
        
        // Get year from template, URL parameter, or default to current year
        this.currentYear = parseInt(templateYear, 10) || new Date().getFullYear();
        
        // Override with URL parameter if present
        var urlParams = new URLSearchParams(window.location.search);
        var urlYear = urlParams.get('year');
        if (urlYear) {
            this.currentYear = parseInt(urlYear, 10);
        }
        
        // Check if year is in the URL path
        var pathMatch = window.location.pathname.match(/\/statements\/(\d{4})/);
        if (pathMatch) {
            this.currentYear = parseInt(pathMatch[1], 10);
        }
        
        // Initialize year data structure
        if (!this.accountDataByYear[this.currentYear]) {
            this.accountDataByYear[this.currentYear] = {};
        }
        
        // Set up error handling
        this.setupErrorHandling();
    },
    
    /**
     * Detect current environment
     * @returns {string} Environment name
     */
    detectEnvironment: function() {
        var hostname = window.location.hostname;
        
        if (hostname === 'localhost' || hostname === '127.0.0.1') {
            return 'development';
        } else if (hostname.includes('staging') || hostname.includes('test')) {
            return 'staging';
        } else {
            return 'production';
        }
    },
    
    /**
     * Get API base URL based on environment
     * @returns {string} API base URL
     */
    getApiBaseUrl: function() {
        switch (this.environment) {
            case 'development':
                return 'http://localhost:5001';
            case 'staging':
                return ''; // Use relative URLs for staging
            case 'production':
            default:
                return ''; // Use relative URLs for production
        }
    },
    
    /**
     * Set up global error handling
     */
    setupErrorHandling: function() {
        var self = this;
        
        // Handle unhandled promise rejections
        window.addEventListener('unhandledrejection', function(event) {
            if (self.environment === 'development') {
                console.error('Unhandled promise rejection:', event.reason);
            }
            
            // Show user-friendly error message
            if (window.StatementsUI && window.StatementsUI.showAlert) {
                window.StatementsUI.showAlert('danger', 'An unexpected error occurred. Please try again or refresh the page.');
            }
        });
        
        // Handle JavaScript errors
        window.addEventListener('error', function(event) {
            if (self.environment === 'development') {
                console.error('JavaScript error:', event.error);
            }
            
            // Show user-friendly error message for critical errors
            if (event.error && event.error.message && 
                !event.error.message.includes('Non-Error promise rejection captured')) {
                if (window.StatementsUI && window.StatementsUI.showAlert) {
                    window.StatementsUI.showAlert('warning', 'A technical error occurred. Some features may not work properly.');
                }
            }
        });
    },
    
    /**
     * Get current year
     * @returns {number} Current year
     */
    getCurrentYear: function() {
        return this.currentYear;
    },
    
    /**
     * Check if account data is loaded for current year
     * @param {string} accountId - Account identifier
     * @returns {boolean} Whether account is loaded
     */
    isAccountLoaded: function(accountId) {
        return this.accountDataByYear[this.currentYear] && 
               this.accountDataByYear[this.currentYear][accountId] !== undefined;
    },
    
    /**
     * Get account data for current year
     * @param {string} accountId - Account identifier
     * @returns {Object|null} Account data or null if not loaded
     */
    getAccountData: function(accountId) {
        if (!this.isAccountLoaded(accountId)) {
            return null;
        }
        return this.accountDataByYear[this.currentYear][accountId];
    },
    
    /**
     * Store account data for current year
     * @param {string} accountId - Account identifier
     * @param {Object} accountData - Account data to store
     */
    setAccountData: function(accountId, accountData) {
        if (!this.accountDataByYear[this.currentYear]) {
            this.accountDataByYear[this.currentYear] = {};
        }
        this.accountDataByYear[this.currentYear][accountId] = accountData;
    },
    
    /**
     * Clear account data for current year
     * @param {string} accountId - Account identifier (optional, clears all if not provided)
     */
    clearAccountData: function(accountId) {
        if (!this.accountDataByYear[this.currentYear]) {
            return;
        }
        
        if (accountId) {
            delete this.accountDataByYear[this.currentYear][accountId];
        } else {
            this.accountDataByYear[this.currentYear] = {};
        }
    },
    
    /**
     * Get all loaded account IDs for current year
     * @returns {string[]} Array of loaded account IDs
     */
    getLoadedAccountIds: function() {
        if (!this.accountDataByYear[this.currentYear]) {
            return [];
        }
        return Object.keys(this.accountDataByYear[this.currentYear]);
    },
    
    /**
     * Check if running in development mode
     * @returns {boolean} Whether in development mode
     */
    isDevelopment: function() {
        return this.environment === 'development';
    },
    
    /**
     * Check if running in production mode
     * @returns {boolean} Whether in production mode
     */
    isProduction: function() {
        return this.environment === 'production';
    },
    
    /**
     * Get configuration for specific account
     * @param {string} accountId - Account identifier
     * @returns {Object|null} Account configuration or null if not found
     */
    getAccountConfig: function(accountId) {
        // This would ideally come from the server configuration
        // For now, return basic info based on account ID
        if (!this.accountIds.includes(accountId)) {
            return null;
        }
        
        var type = accountId.startsWith('stp_') ? 'stp' : 'bbva';
        var parts = accountId.split('_');
        
        return {
            id: accountId,
            type: type,
            name: this.formatAccountName(accountId),
            currency: accountId.includes('usd') ? 'USD' : 'MXN'
        };
    },
    
    /**
     * Format account ID into display name
     * @param {string} accountId - Account identifier
     * @returns {string} Formatted account name
     */
    formatAccountName: function(accountId) {
        var nameMap = {
            'stp_sa': 'STP SA',
            'stp_ip_pi': 'STP IP - PI',
            'stp_ip_pd': 'STP IP - PD',
            'bbva_mx_mxn': 'BBVA MX MXN',
            'bbva_mx_usd': 'BBVA MX USD',
            'bbva_sa_mxn': 'BBVA SA MXN',
            'bbva_sa_usd': 'BBVA SA USD',
            'bbva_ip_corp': 'BBVA IP Corp',
            'bbva_ip_clientes': 'BBVA IP Clientes'
        };
        
        return nameMap[accountId] || accountId.toUpperCase().replace(/_/g, ' ');
    },
    
    /**
     * Get available years for navigation
     * @returns {number[]} Array of available years
     */
    getAvailableYears: function() {
        var currentYear = new Date().getFullYear();
        return [currentYear - 2, currentYear - 1, currentYear];
    },
    
    /**
     * Validate year parameter
     * @param {string|number} year - Year to validate
     * @returns {boolean} Whether year is valid
     */
    isValidYear: function(year) {
        var yearNum = parseInt(year, 10);
        var currentYear = new Date().getFullYear();
        return yearNum >= (currentYear - 5) && yearNum <= (currentYear + 1);
    }
};