// Teams File Manager JavaScript

document.addEventListener('DOMContentLoaded', function() {
    // Initialize tooltips
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });

    // Add loading states to buttons
    const downloadButtons = document.querySelectorAll('a[href*="/download/"]');
    downloadButtons.forEach(button => {
        button.addEventListener('click', function() {
            const originalText = this.innerHTML;
            this.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Downloading...';
            this.classList.add('disabled');
            
            // Reset button after 3 seconds
            setTimeout(() => {
                this.innerHTML = originalText;
                this.classList.remove('disabled');
            }, 3000);
        });
    });

    // Auto-hide alerts after 5 seconds
    const alerts = document.querySelectorAll('.alert');
    alerts.forEach(alert => {
        setTimeout(() => {
            const bsAlert = new bootstrap.Alert(alert);
            bsAlert.close();
        }, 5000);
    });

    // Add search functionality
    const searchInput = document.querySelector('input[name="q"]');
    if (searchInput) {
        let searchTimeout;
        searchInput.addEventListener('input', function() {
            clearTimeout(searchTimeout);
            const query = this.value.trim();
            
            if (query.length >= 3) {
                searchTimeout = setTimeout(() => {
                    // Could implement live search here
                    console.log('Searching for:', query);
                }, 500);
            }
        });
    }

    // Add file type icons
    addFileTypeIcons();
    
    // Add smooth scrolling
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            e.preventDefault();
            const target = document.querySelector(this.getAttribute('href'));
            if (target) {
                target.scrollIntoView({
                    behavior: 'smooth',
                    block: 'start'
                });
            }
        });
    });
});

// Function to add file type icons
function addFileTypeIcons() {
    const fileRows = document.querySelectorAll('table tbody tr');
    fileRows.forEach(row => {
        const nameCell = row.querySelector('td:first-child');
        if (nameCell) {
            const fileName = nameCell.textContent.trim();
            const fileExtension = getFileExtension(fileName);
            const icon = getFileIcon(fileExtension);
            
            // Update existing icon
            const iconElement = nameCell.querySelector('i');
            if (iconElement && !fileName.includes('folder')) {
                iconElement.className = `fas ${icon} text-primary me-2`;
            }
        }
    });
}

// Function to get file extension
function getFileExtension(fileName) {
    return fileName.split('.').pop().toLowerCase();
}

// Function to get appropriate icon for file type
function getFileIcon(extension) {
    const iconMap = {
        // Documents
        'pdf': 'fa-file-pdf',
        'doc': 'fa-file-word',
        'docx': 'fa-file-word',
        'txt': 'fa-file-alt',
        'rtf': 'fa-file-alt',
        
        // Spreadsheets
        'xls': 'fa-file-excel',
        'xlsx': 'fa-file-excel',
        'csv': 'fa-file-csv',
        
        // Presentations
        'ppt': 'fa-file-powerpoint',
        'pptx': 'fa-file-powerpoint',
        
        // Images
        'jpg': 'fa-file-image',
        'jpeg': 'fa-file-image',
        'png': 'fa-file-image',
        'gif': 'fa-file-image',
        'bmp': 'fa-file-image',
        'svg': 'fa-file-image',
        
        // Videos
        'mp4': 'fa-file-video',
        'avi': 'fa-file-video',
        'mov': 'fa-file-video',
        'wmv': 'fa-file-video',
        'flv': 'fa-file-video',
        
        // Audio
        'mp3': 'fa-file-audio',
        'wav': 'fa-file-audio',
        'flac': 'fa-file-audio',
        'aac': 'fa-file-audio',
        
        // Archives
        'zip': 'fa-file-archive',
        'rar': 'fa-file-archive',
        '7z': 'fa-file-archive',
        'tar': 'fa-file-archive',
        'gz': 'fa-file-archive',
        
        // Code
        'js': 'fa-file-code',
        'html': 'fa-file-code',
        'css': 'fa-file-code',
        'py': 'fa-file-code',
        'java': 'fa-file-code',
        'cpp': 'fa-file-code',
        'c': 'fa-file-code',
        'php': 'fa-file-code',
        'rb': 'fa-file-code',
        'json': 'fa-file-code',
        'xml': 'fa-file-code'
    };
    
    return iconMap[extension] || 'fa-file';
}

// Function to format file sizes
function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

// Function to show loading spinner
function showLoading(element) {
    const spinner = document.createElement('div');
    spinner.className = 'spinner-border spinner-border-sm me-2';
    spinner.setAttribute('role', 'status');
    element.prepend(spinner);
}

// Function to hide loading spinner
function hideLoading(element) {
    const spinner = element.querySelector('.spinner-border');
    if (spinner) {
        spinner.remove();
    }
}

// Function to show toast notifications
function showToast(message, type = 'info') {
    const toastContainer = document.querySelector('.toast-container') || createToastContainer();
    
    const toast = document.createElement('div');
    toast.className = `toast align-items-center text-white bg-${type} border-0`;
    toast.setAttribute('role', 'alert');
    toast.innerHTML = `
        <div class="d-flex">
            <div class="toast-body">
                ${message}
            </div>
            <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
        </div>
    `;
    
    toastContainer.appendChild(toast);
    
    const bsToast = new bootstrap.Toast(toast);
    bsToast.show();
    
    // Remove toast element after it's hidden
    toast.addEventListener('hidden.bs.toast', function() {
        toast.remove();
    });
}

// Function to create toast container if it doesn't exist
function createToastContainer() {
    const container = document.createElement('div');
    container.className = 'toast-container position-fixed bottom-0 end-0 p-3';
    document.body.appendChild(container);
    return container;
}

// Global error handler
window.addEventListener('error', function(event) {
    console.error('Global error:', event.error);
    showToast('An unexpected error occurred. Please try again.', 'danger');
});

// Handle network errors
window.addEventListener('online', function() {
    showToast('Internet connection restored.', 'success');
});

window.addEventListener('offline', function() {
    showToast('Internet connection lost. Some features may not work.', 'warning');
});