// Global configuration and data storage
window.StatementsApp = {
    // Account IDs from your unified accounts configuration
    accountIds: ['stp_sa', 'stp_ip_pi', 'stp_ip_pd', 'bbva_mx_mxn', 'bbva_mx_usd', 'bbva_sa_mxn', 'bbva_sa_usd', 'bbva_ip_corp', 'bbva_ip_clientes'],
    
    // Data storage by year (used by some legacy functions)
    accountDataByYear: {},
    
    // Current year from template or URL
    currentYear: null,
    
    // Initialize from template data
    init: function(templateYear) {
        // Get year from template, URL parameter, or default to current year
        this.currentYear = parseInt(templateYear, 10) || new Date().getFullYear();
        
        // Override with URL parameter if present
        var urlParams = new URLSearchParams(window.location.search);
        var urlYear = urlParams.get('year');
        if (urlYear) {
            this.currentYear = parseInt(urlYear, 10);
        }
        
        // Also check if year is in the URL path
        var pathMatch = window.location.pathname.match(/\/statements\/(\d{4})/);
        if (pathMatch) {
            this.currentYear = parseInt(pathMatch[1], 10);
        }
        
        console.log('StatementsApp initialized - Year:', this.currentYear, 'Accounts:', this.accountIds.length);
        
        // Initialize year data structure
        if (!this.accountDataByYear[this.currentYear]) {
            this.accountDataByYear[this.currentYear] = {};
        }
    },
    
    // Helper function to get current year
    getCurrentYear: function() {
        return this.currentYear;
    },
    
    // Helper function to check if account data is loaded
    isAccountLoaded: function(accountId) {
        return this.accountDataByYear[this.currentYear] && 
               this.accountDataByYear[this.currentYear][accountId] !== undefined;
    },
    
    // Helper function to get account data
    getAccountData: function(accountId) {
        if (!this.isAccountLoaded(accountId)) {
            return null;
        }
        return this.accountDataByYear[this.currentYear][accountId];
    }
};