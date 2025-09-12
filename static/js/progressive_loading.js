// static/js/progressive_loading.js
/**
 * Progressive Loading System for STP and BBVA Calendars
 * Provides real-time loading feedback and skeleton UI
 */

class ProgressiveCalendarLoader {
    constructor(systemType = 'stp') {
        this.systemType = systemType;
        this.loadedAccounts = new Set();
        this.totalAccounts = 0;
        this.isLoading = false;
        this.loadStartTime = null;
        this.accountsToLoad = [];
        
        // Performance tracking
        this.performanceMetrics = {
            totalLoadTime: 0,
            accountLoadTimes: {},
            cacheHits: 0,
            totalRequests: 0
        };
    }
    
    async loadCalendarProgressive(year, containerId = null) {
        if (this.isLoading) {
            console.log('Loading already in progress...');
            return;
        }
        
        this.isLoading = true;
        this.loadStartTime = Date.now();
        
        try {
            // Determine container
            const container = containerId ? 
                document.getElementById(containerId) : 
                document.querySelector('.calendar-container, #calendar-content');
            
            if (!container) {
                throw new Error('Calendar container not found');
            }
            
            // Show skeleton UI immediately
            this.showSkeletonCalendar(container);
            
            // Start progressive loading
            await this.loadWithProgress(year, container);
            
        } catch (error) {
            console.error('Progressive loading error:', error);
            this.showErrorState(container);
        } finally {
            this.isLoading = false;
            this.logPerformanceMetrics();
        }
    }
    
    async loadWithProgress(year, container) {
        try {
            // First, try to get cached data quickly
            const cachedResponse = await fetch(`/api/${this.systemType}/calendar-cached/${year}`, {
                method: 'GET',
                cache: 'force-cache'
            });
            
            if (cachedResponse.ok) {
                const cachedData = await cachedResponse.json();
                if (cachedData.calendar_data && Object.keys(cachedData.calendar_data).length > 0) {
                    this.performanceMetrics.cacheHits++;
                    this.renderCalendarData(container, cachedData.calendar_data, year);
                    this.updateProgress(100, 'Loaded from cache');
                    return;
                }
            }
            
            // If no cache, load progressively
            this.performanceMetrics.totalRequests++;
            await this.loadProgressivelyFromAPI(year, container);
            
        } catch (error) {
            console.error('Error in loadWithProgress:', error);
            throw error;
        }
    }
    
    async loadProgressivelyFromAPI(year, container) {
        try {
            const response = await fetch(`/api/${this.systemType}/calendar-progressive/${year}`, {
                method: 'GET',
                headers: {
                    'Accept': 'text/stream',
                    'Cache-Control': 'no-cache'
                }
            });
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            let buffer = '';
            
            while (true) {
                const { done, value } = await reader.read();
                
                if (done) break;
                
                buffer += decoder.decode(value, { stream: true });
                const lines = buffer.split('\n');
                buffer = lines.pop(); // Keep incomplete line in buffer
                
                for (const line of lines) {
                    if (line.trim()) {
                        try {
                            const data = JSON.parse(line);
                            this.handleProgressiveUpdate(data, container, year);
                        } catch (e) {
                            console.warn('Failed to parse progressive update:', line);
                        }
                    }
                }
            }
            
            // Process any remaining buffer
            if (buffer.trim()) {
                try {
                    const data = JSON.parse(buffer);
                    this.handleProgressiveUpdate(data, container, year);
                } catch (e) {
                    console.warn('Failed to parse final update:', buffer);
                }
            }
            
        } catch (error) {
            console.error('Progressive API loading error:', error);
            // Fallback to regular loading
            await this.fallbackToRegularLoad(year, container);
        }
    }
    
    async fallbackToRegularLoad(year, container) {
        console.log('Falling back to regular loading...');
        this.updateProgress(50, 'Loading all accounts...');
        
        try {
            const response = await fetch(`/api/${this.systemType}/calendar/${year}`);
            const data = await response.json();
            
            if (data.calendar_data) {
                this.renderCalendarData(container, data.calendar_data, year);
                this.updateProgress(100, 'Loaded successfully');
            } else {
                throw new Error('No calendar data received');
            }
        } catch (error) {
            console.error('Fallback loading failed:', error);
            throw error;
        }
    }
    
    handleProgressiveUpdate(data, container, year) {
        switch (data.type) {
            case 'init':
                this.totalAccounts = data.total_accounts || 0;
                this.accountsToLoad = data.accounts || [];
                this.updateProgress(10, `Preparing to load ${this.totalAccounts} accounts...`);
                break;
                
            case 'account_start':
                this.updateProgress(
                    data.progress || 20, 
                    `Loading ${data.account_name || data.account}...`
                );
                break;
                
            case 'account_loaded':
                this.loadedAccounts.add(data.account);
                this.updateAccountInCalendar(container, data.account_data, data.account);
                
                const progress = (this.loadedAccounts.size / this.totalAccounts) * 80 + 20;
                this.updateProgress(
                    progress, 
                    `Loaded ${data.account_name || data.account} (${this.loadedAccounts.size}/${this.totalAccounts})`
                );
                
                // Track performance
                if (data.load_time) {
                    this.performanceMetrics.accountLoadTimes[data.account] = data.load_time;
                }
                break;
                
            case 'completed':
                this.renderCalendarData(container, data.calendar_data, year);
                this.updateProgress(100, 'All accounts loaded successfully');
                break;
                
            case 'error':
                console.error('Progressive loading error:', data.error);
                this.showErrorState(container, data.error);
                break;
        }
    }
    
    showSkeletonCalendar(container) {
        const skeletonHTML = `
            <div class="progressive-loading-container">
                <!-- Progress Bar -->
                <div class="progress mb-4" style="height: 8px;">
                    <div class="progress-bar progress-bar-striped progress-bar-animated bg-primary" 
                         id="loading-progress-bar" style="width: 5%"></div>
                </div>
                
                <!-- Status Message -->
                <div class="text-center mb-4">
                    <div class="loading-spinner">
                        <div class="spinner-border text-primary" role="status">
                            <span class="visually-hidden">Loading...</span>
                        </div>
                    </div>
                    <div id="loading-status" class="mt-2 text-muted">
                        Initializing ${this.systemType.toUpperCase()} calendar...
                    </div>
                    <div id="loading-time" class="small text-muted mt-1">
                        Loading started...
                    </div>
                </div>
                
                <!-- Skeleton Account Cards -->
                <div class="row" id="skeleton-accounts">
                    ${this.generateSkeletonCards()}
                </div>
                
                <!-- Performance Info (Debug) -->
                <div class="mt-3 text-center" style="font-size: 0.8em; color: #6c757d;">
                    <div id="performance-info"></div>
                </div>
            </div>
        `;
        
        container.innerHTML = skeletonHTML;
        
        // Start time tracker
        setInterval(() => {
            const elapsed = ((Date.now() - this.loadStartTime) / 1000).toFixed(1);
            const timeElement = document.getElementById('loading-time');
            if (timeElement && this.isLoading) {
                timeElement.textContent = `Loading time: ${elapsed}s`;
            }
        }, 100);
    }
    
    generateSkeletonCards() {
        const accountCount = this.systemType === 'stp' ? 3 : 6; // STP has 3, BBVA has 6
        let skeletonHTML = '';
        
        for (let i = 0; i < accountCount; i++) {
            skeletonHTML += `
                <div class="col-md-6 col-lg-4 mb-4">
                    <div class="card skeleton-card">
                        <div class="card-header">
                            <div class="skeleton-line skeleton-title"></div>
                            <div class="skeleton-line skeleton-subtitle"></div>
                        </div>
                        <div class="card-body">
                            <div class="skeleton-calendar">
                                ${this.generateSkeletonCalendarGrid()}
                            </div>
                        </div>
                    </div>
                </div>
            `;
        }
        
        return skeletonHTML;
    }
    
    generateSkeletonCalendarGrid() {
        let gridHTML = '';
        
        // Generate 4 rows × 3 columns = 12 months
        for (let row = 0; row < 4; row++) {
            gridHTML += '<div class="skeleton-calendar-row">';
            for (let col = 0; col < 3; col++) {
                gridHTML += '<div class="skeleton-month"></div>';
            }
            gridHTML += '</div>';
        }
        
        return gridHTML;
    }
    
    updateProgress(percentage, message) {
        const progressBar = document.getElementById('loading-progress-bar');
        const statusElement = document.getElementById('loading-status');
        
        if (progressBar) {
            progressBar.style.width = `${Math.min(percentage, 100)}%`;
            progressBar.setAttribute('aria-valuenow', percentage);
        }
        
        if (statusElement) {
            statusElement.textContent = message;
        }
        
        // Update performance info
        this.updatePerformanceInfo();
    }
    
    updatePerformanceInfo() {
        const perfElement = document.getElementById('performance-info');
        if (perfElement && this.loadStartTime) {
            const elapsed = ((Date.now() - this.loadStartTime) / 1000).toFixed(1);
            const loaded = this.loadedAccounts.size;
            const total = this.totalAccounts || 0;
            
            perfElement.innerHTML = `
                Loaded: ${loaded}/${total} accounts | 
                Time: ${elapsed}s | 
                Cache hits: ${this.performanceMetrics.cacheHits}
            `;
        }
    }
    
    updateAccountInCalendar(container, accountData, accountKey) {
        // Find and update specific account card
        const accountCard = container.querySelector(`[data-account="${accountKey}"]`);
        if (accountCard) {
            accountCard.innerHTML = this.generateAccountHTML(accountData);
            accountCard.classList.add('loaded-account');
            
            // Add loading animation
            accountCard.style.animation = 'fadeInUp 0.5s ease-out';
        }
    }
    
    renderCalendarData(container, calendarData, year) {
        // Generate final calendar HTML
        let calendarHTML = `
            <div class="calendar-loaded">
                <div class="row">
        `;
        
        Object.entries(calendarData).forEach(([accountKey, accountData]) => {
            calendarHTML += `
                <div class="col-md-6 col-lg-4 mb-4">
                    <div class="card account-card loaded-account" data-account="${accountKey}">
                        ${this.generateAccountHTML(accountData, accountKey)}
                    </div>
                </div>
            `;
        });
        
        calendarHTML += `
                </div>
            </div>
        `;
        
        container.innerHTML = calendarHTML;
        
        // Initialize any additional functionality
        this.initializeCalendarInteractions();
    }
    
    generateAccountHTML(accountData, accountKey = '') {
        // This would be customized based on your specific account card format
        const accountInfo = accountData.account_info || {};
        const months = accountData.months || {};
        
        let html = `
            <div class="card-header">
                <h6 class="mb-1">${accountInfo.name || accountKey}</h6>
                <small class="text-muted">${accountInfo.description || ''}</small>
            </div>
            <div class="card-body">
                <div class="calendar-grid">
        `;
        
        // Generate month grid
        Object.entries(months).forEach(([monthKey, monthData]) => {
            const status = monthData.status || 'missing';
            const statusClass = this.getStatusClass(status);
            
            html += `
                <div class="calendar-month ${statusClass}" data-month="${monthKey}">
                    <div class="month-indicator"></div>
                </div>
            `;
        });
        
        html += `
                </div>
                <div class="mt-2 small text-muted">
                    Total files: ${accountData.total_files || 0}
                </div>
            </div>
        `;
        
        return html;
    }
    
    getStatusClass(status) {
        const statusMap = {
            'complete': 'status-complete',
            'partial': 'status-partial', 
            'missing': 'status-missing',
            'error': 'status-error'
        };
        return statusMap[status] || 'status-unknown';
    }
    
    showErrorState(container, errorMessage = 'Failed to load calendar data') {
        container.innerHTML = `
            <div class="alert alert-danger">
                <div class="d-flex align-items-center">
                    <i class="fas fa-exclamation-triangle me-2"></i>
                    <div>
                        <strong>Loading Error</strong><br>
                        ${errorMessage}
                    </div>
                </div>
                <button class="btn btn-outline-danger btn-sm mt-2" onclick="location.reload()">
                    <i class="fas fa-redo"></i> Retry
                </button>
            </div>
        `;
    }
    
    initializeCalendarInteractions() {
        // Add click handlers, tooltips, etc.
        const monthElements = document.querySelectorAll('.calendar-month');
        monthElements.forEach(element => {
            element.addEventListener('click', (e) => {
                const month = e.target.dataset.month;
                if (month) {
                    this.handleMonthClick(month);
                }
            });
        });
    }
    
    handleMonthClick(month) {
        console.log(`Month clicked: ${month}`);
        // Implement month click functionality
    }
    
    logPerformanceMetrics() {
        const totalTime = (Date.now() - this.loadStartTime) / 1000;
        this.performanceMetrics.totalLoadTime = totalTime;
        
        console.log('📊 Progressive Loading Performance:', {
            ...this.performanceMetrics,
            accountsLoaded: this.loadedAccounts.size,
            totalAccounts: this.totalAccounts,
            loadTime: `${totalTime.toFixed(2)}s`
        });
    }
}

// Global instances
window.stpLoader = new ProgressiveCalendarLoader('stp');
window.bbvaLoader = new ProgressiveCalendarLoader('bbva');

// Auto-initialize on page load
document.addEventListener('DOMContentLoaded', function() {
    // Check if we're on a calendar page
    const calendarContainer = document.querySelector('.calendar-container, #calendar-content');
    const currentYear = new Date().getFullYear();
    
    if (calendarContainer) {
        // Determine system type from URL or page data
        const systemType = window.location.pathname.includes('bbva') || 
                          window.location.pathname.includes('banks') ? 'bbva' : 'stp';
        
        const loader = systemType === 'bbva' ? window.bbvaLoader : window.stpLoader;
        
        // Start progressive loading
        loader.loadCalendarProgressive(currentYear, calendarContainer.id);
    }
});

// Utility functions
function refreshCalendar(systemType = 'stp', year = null) {
    year = year || new Date().getFullYear();
    const loader = systemType === 'bbva' ? window.bbvaLoader : window.stpLoader;
    loader.loadCalendarProgressive(year);
}

function clearCache(systemType = 'all') {
    if (systemType === 'all' || systemType === 'stp') {
        window.stpLoader.performanceMetrics.cacheHits = 0;
    }
    if (systemType === 'all' || systemType === 'bbva') {
        window.bbvaLoader.performanceMetrics.cacheHits = 0;
    }
    console.log(`Cache cleared for ${systemType}`);
}