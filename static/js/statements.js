/**
 * Unified Statements Frontend Logic
 * Clean, focused JavaScript for the unified statements system
 */

// Global variables
let currentParseSession = null;
let parseProgressInterval = null;

// Initialize page
document.addEventListener('DOMContentLoaded', function() {
    initializeTooltips();
    initializeModals();
    setupEventListeners();
});

// ============================================================================
// INITIALIZATION
// ============================================================================

function initializeTooltips() {
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function(tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
}

function initializeModals() {
    // Initialize Bootstrap modals
    const uploadModal = document.getElementById('uploadModal');
    const parseModal = document.getElementById('parseModal');
    
    if (uploadModal) {
        window.uploadModalInstance = new bootstrap.Modal(uploadModal);
    }
    
    if (parseModal) {
        window.parseModalInstance = new bootstrap.Modal(parseModal);
    }
}

function setupEventListeners() {
    // File input change handler
    const fileInput = document.getElementById('fileInput');
    if (fileInput) {
        fileInput.addEventListener('change', handleFileSelect);
    }
}

// ============================================================================
// ACCOUNT OPERATIONS
// ============================================================================

function parseAccount(accountId) {
    if (!accountId) {
        showAlert('error', 'Invalid account ID');
        return;
    }
    
    showParseModal();
    updateParseProgress(0, 'Starting parse operation...');
    
    fetch(`/api/statements/parse/${accountId}`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            currentParseSession = data.session_id;
            startProgressTracking();
        } else {
            showAlert('error', data.error || 'Failed to start parse operation');
            hideParseModal();
        }
    })
    .catch(error => {
        console.error('Parse start error:', error);
        showAlert('error', 'Failed to start parse operation');
        hideParseModal();
    });
}

function parseAllAccounts() {
    if (!confirm('Are you sure you want to parse all accounts? This may take several minutes.')) {
        return;
    }
    
    showAlert('info', 'Batch parsing not yet implemented');
}

function viewAccountDetail(accountId) {
    // Open account detail in new tab/window
    window.open(`/api/statements/account/${accountId}/summary`, '_blank');
}

function exportAccount(accountId) {
    showAlert('info', 'Export functionality not yet implemented');
}

// ============================================================================
// PARSE PROGRESS TRACKING
// ============================================================================

function showParseModal() {
    const parseModal = document.getElementById('parseModal');
    if (parseModal && window.parseModalInstance) {
        window.parseModalInstance.show();
    }
}

function hideParseModal() {
    const parseModal = document.getElementById('parseModal');
    if (parseModal && window.parseModalInstance) {
        window.parseModalInstance.hide();
    }
}

function startProgressTracking() {
    if (!currentParseSession) return;
    
    parseProgressInterval = setInterval(() => {
        fetch(`/api/statements/parse-progress/${currentParseSession}`)
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    const progress = data.progress;
                    updateParseProgress(
                        progress.progress_percentage,
                        progress.current_file || `Processing... (${progress.files_processed}/${progress.total_files})`
                    );
                    
                    if (progress.status === 'completed' || progress.status === 'error') {
                        stopProgressTracking();
                        showParseResults(progress);
                    }
                } else {
                    stopProgressTracking();
                    showAlert('error', data.error || 'Failed to get progress');
                    hideParseModal();
                }
            })
            .catch(error => {
                console.error('Progress tracking error:', error);
                stopProgressTracking();
            });
    }, 1000);
}

function stopProgressTracking() {
    if (parseProgressInterval) {
        clearInterval(parseProgressInterval);
        parseProgressInterval = null;
    }
}

function updateParseProgress(percentage, status) {
    const progressBar = document.getElementById('parseProgressBar');
    const statusElement = document.getElementById('parseStatus');
    
    if (progressBar) {
        progressBar.style.width = percentage + '%';
        progressBar.setAttribute('aria-valuenow', percentage);
        progressBar.textContent = Math.round(percentage) + '%';
    }
    
    if (statusElement) {
        statusElement.textContent = status;
    }
}

function showParseResults(progress) {
    const resultsElement = document.getElementById('parseResults');
    const progressElement = document.getElementById('parseProgress');
    
    if (resultsElement) {
        let html = '';
        
        if (progress.status === 'completed') {
            html = `
                <div class="alert alert-success">
                    <h6><i class="fas fa-check-circle me-2"></i>Parse Complete!</h6>
                    <p>Successfully processed ${progress.files_processed} files</p>
                    <small>Added ${progress.transactions_added} transactions</small>
                </div>
            `;
        } else if (progress.status === 'error') {
            html = `
                <div class="alert alert-danger">
                    <h6><i class="fas fa-exclamation-triangle me-2"></i>Parse Failed</h6>
                    <p>${progress.error || 'Unknown error occurred'}</p>
                </div>
            `;
        }
        
        resultsElement.innerHTML = html;
        resultsElement.style.display = 'block';
    }
    
    if (progressElement) {
        progressElement.style.display = 'none';
    }
    
    // Auto-close modal after 3 seconds
    setTimeout(() => {
        hideParseModal();
        refreshPage();
    }, 3000);
}

// ============================================================================
// FILE UPLOAD FUNCTIONALITY
// ============================================================================

function showUploadModal() {
    const uploadModal = document.getElementById('uploadModal');
    if (uploadModal && window.uploadModalInstance) {
        window.uploadModalInstance.show();
    }
}

function handleFileSelect(event) {
    const files = Array.from(event.target.files);
    if (files.length === 0) return;
    
    validateFiles(files);
}

function validateFiles(files) {
    const validExtensions = ['.pdf', '.xlsx', '.xls'];
    const invalidFiles = files.filter(file => {
        const extension = '.' + file.name.split('.').pop().toLowerCase();
        return !validExtensions.includes(extension);
    });
    
    if (invalidFiles.length > 0) {
        showAlert('error', `Invalid file types: ${invalidFiles.map(f => f.name).join(', ')}`);
        return;
    }
    
    showAlert('info', `Selected ${files.length} files for upload`);
}

function uploadFiles() {
    const fileInput = document.getElementById('fileInput');
    if (!fileInput || !fileInput.files.length) {
        showAlert('error', 'Please select files to upload');
        return;
    }
    
    const formData = new FormData();
    Array.from(fileInput.files).forEach(file => {
        formData.append('files', file);
    });
    
    // Show progress
    const progressElement = document.getElementById('uploadProgress');
    const progressBar = document.getElementById('uploadProgressBar');
    
    if (progressElement) progressElement.style.display = 'block';
    if (progressBar) {
        progressBar.style.width = '0%';
        progressBar.textContent = '0%';
    }
    
    fetch('/api/statements/upload', {
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        handleUploadResults(data);
    })
    .catch(error => {
        console.error('Upload error:', error);
        showAlert('error', 'Upload failed: ' + error.message);
    })
    .finally(() => {
        if (progressElement) progressElement.style.display = 'none';
    });
}

function handleUploadResults(data) {
    const resultsElement = document.getElementById('uploadResults');
    
    if (!resultsElement) return;
    
    let html = '';
    
    if (data.success) {
        html = `
            <div class="alert alert-success">
                <h6>Upload Successful!</h6>
                <p>Successfully uploaded ${data.successful_uploads} of ${data.total_files} files</p>
            </div>
        `;
    } else {
        html = `
            <div class="alert alert-warning">
                <h6>Upload Completed with Issues</h6>
                <p>Uploaded ${data.successful_uploads} of ${data.total_files} files</p>
                <p>${data.failed_uploads} files failed</p>
            </div>
        `;
    }
    
    // Show individual file results
    if (data.results && data.results.length > 0) {
        html += '<div class="mt-3"><h6>File Details:</h6><ul class="list-unstyled">';
        data.results.forEach(result => {
            const icon = result.success ? 'fa-check text-success' : 'fa-times text-danger';
            const message = result.success ? 'Uploaded successfully' : (result.error || 'Upload failed');
            html += `<li><i class="fas ${icon}"></i> ${result.filename}: ${message}</li>`;
        });
        html += '</ul></div>';
    }
    
    resultsElement.innerHTML = html;
    
    // Clear file input
    const fileInput = document.getElementById('fileInput');
    if (fileInput) fileInput.value = '';
    
    // Auto-close modal after 3 seconds if successful
    if (data.success) {
        setTimeout(() => {
            if (window.uploadModalInstance) {
                window.uploadModalInstance.hide();
            }
            refreshPage();
        }, 3000);
    }
}

// ============================================================================
// DATA REFRESH
// ============================================================================

function refreshAllData() {
    showAlert('info', 'Refreshing data...');
    
    fetch('/api/cache/clear', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'success') {
            showAlert('success', 'Data refreshed successfully');
            setTimeout(refreshPage, 1000);
        } else {
            showAlert('error', data.message || 'Failed to refresh data');
        }
    })
    .catch(error => {
        console.error('Refresh error:', error);
        showAlert('error', 'Failed to refresh data');
    });
}

function refreshPage() {
    window.location.reload();
}

// ============================================================================
// UTILITY FUNCTIONS
// ============================================================================

function showAlert(type, message, duration = 5000) {
    // Remove existing alerts
    const existingAlerts = document.querySelectorAll('.alert-floating');
    existingAlerts.forEach(alert => alert.remove());
    
    // Create new alert
    const alertClass = type === 'error' ? 'alert-danger' : 
                     type === 'success' ? 'alert-success' : 
                     type === 'warning' ? 'alert-warning' : 'alert-info';
    
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert ${alertClass} alert-floating`;
    alertDiv.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        z-index: 1050;
        min-width: 300px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    `;
    
    alertDiv.innerHTML = `
        <div class="d-flex justify-content-between align-items-center">
            <span>${message}</span>
            <button type="button" class="btn-close" onclick="this.parentElement.parentElement.remove()"></button>
        </div>
    `;
    
    document.body.appendChild(alertDiv);
    
    // Auto-remove after duration
    if (duration > 0) {
        setTimeout(() => {
            if (alertDiv.parentNode) {
                alertDiv.remove();
            }
        }, duration);
    }
}

function formatDateTime(dateString) {
    if (!dateString || dateString === 'Never') return dateString;
    
    try {
        const date = new Date(dateString);
        return date.toLocaleDateString() + ' ' + date.toLocaleTimeString();
    } catch {
        return dateString;
    }
}

function formatNumber(number) {
    if (typeof number !== 'number') return number;
    return number.toLocaleString();
}

// ============================================================================
// KEYBOARD SHORTCUTS
// ============================================================================

document.addEventListener('keydown', function(event) {
    // Ctrl/Cmd + U: Upload
    if ((event.ctrlKey || event.metaKey) && event.key === 'u') {
        event.preventDefault();
        showUploadModal();
    }
    
    // Ctrl/Cmd + R: Refresh (override default to use our refresh)
    if ((event.ctrlKey || event.metaKey) && event.key === 'r') {
        event.preventDefault();
        refreshAllData();
    }
    
    // Escape: Close modals
    if (event.key === 'Escape') {
        // Bootstrap handles this automatically, but we can add custom logic here
    }
});