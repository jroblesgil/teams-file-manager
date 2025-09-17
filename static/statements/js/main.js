// main.js - Production Version
// Store files globally for drag-and-drop
var selectedFiles = null;

function refreshAccountInventory(accountId) {
    var loadBtn = document.getElementById('load-btn-' + accountId);
    if (loadBtn) {
        loadBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';
        loadBtn.disabled = true;
    }
    
    var currentYear = window.StatementsApp.currentYear || 2025;
    window.location.href = '/statements/refresh-progress/' + accountId + '?year=' + currentYear;
}

/**
 * Download statement file for specified account and month
 * @param {string} accountId - Account identifier
 * @param {number} month - Month number (1-12)
 */
function downloadMonthFile(accountId, month) {
    month = parseInt(month, 10);
    
    var fileIcon = document.getElementById('file-icon-' + accountId + '-' + month);
    var cell = document.querySelector('[data-account-id="' + accountId + '"][data-month="' + month + '"]');
    var accountRow = document.querySelector('[data-account-id="' + accountId + '"]');
    
    if (!fileIcon || !cell) {
        window.StatementsUI.showAlert('danger', 'Error: Could not find page elements');
        return;
    }
    
    var hasFiles = !cell.classList.contains('no-file');
    if (!hasFiles) {
        window.StatementsUI.showAlert('info', 'No files available for this month');
        return;
    }
    
    var iconHTML = fileIcon.innerHTML;
    var hasExcel = iconHTML.includes('fa-file-excel');
    var hasPdf = iconHTML.includes('fa-file-pdf');
    var accountType = accountRow ? accountRow.getAttribute('data-account-type') : 'unknown';
    
    if (accountType === 'stp' && hasExcel && hasPdf) {
        showSTPFileSelectionModal(accountId, month, { hasExcel, hasPdf, iconHTML });
        return;
    } else if (hasExcel && !hasPdf) {
        downloadFile(accountId, month, 'xlsx');
        return;
    } else if (hasPdf && !hasExcel) {
        downloadFile(accountId, month, 'pdf');
        return;
    } else if (hasExcel && hasPdf) {
        downloadFile(accountId, month, 'pdf');
        return;
    } else {
        window.StatementsUI.showAlert('info', 'No files available for download');
        return;
    }
}

function refreshAllInventories() {
    window.StatementsUI.showAlert('info', 'Starting inventory refresh for all accounts...');
    
    fetch('/api/statements/refresh-all-inventories', {
        method: 'POST'
    })
    .then(function(response) {
        return response.json();
    })
    .then(function(data) {
        if (data.success) {
            window.StatementsUI.showAlert('info', 'Refreshing all inventories... Page will reload shortly.');
            setTimeout(function() {
                window.location.reload();
            }, 5000);
        } else {
            window.StatementsUI.showAlert('danger', 'Failed to start refresh: ' + (data.error || 'Unknown error'));
        }
    })
    .catch(function(error) {
        window.StatementsUI.showAlert('danger', 'Failed to start refresh: ' + error.message);
    });
}

function parseAccountRow(accountId) {
    window.StatementsAPI.parseAccount(accountId);
}

/**
 * Open upload modal for file selection
 */
function uploadToTeams() {
    showUploadModal();
}

/**
 * Create and display upload modal
 */
function showUploadModal() {
    var modalHtml = `
        <div class="modal fade" id="uploadModal" tabindex="-1" aria-hidden="true">
            <div class="modal-dialog modal-dialog-centered">
                <div class="modal-content">
                    <div class="modal-header bg-primary text-white">
                        <h5 class="modal-title">
                            <i class="fas fa-upload me-2"></i>
                            Upload Files to Teams
                        </h5>
                        <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button>
                    </div>
                    <div class="modal-body">
                        <div class="text-center mb-3">
                            <h6 class="text-primary">Select Files to Upload</h6>
                            <p class="text-muted mb-0">STP and BBVA statement files</p>
                        </div>
                        
                        <!-- File Drop Zone -->
                        <div class="d-grid gap-3 mb-3">
                            <div id="fileDropZone" class="file-option-btn btn-outline-primary" 
                                 onclick="document.getElementById('fileInput').click()"
                                 ondrop="handleFileDrop(event)" 
                                 ondragover="handleDragOver(event)"
                                 ondragenter="handleDragEnter(event)"
                                 ondragleave="handleDragLeave(event)">
                                <div class="d-flex align-items-center justify-content-between">
                                    <div class="d-flex align-items-center">
                                        <i class="fas fa-cloud-upload-alt text-primary me-3" style="font-size: 1.8rem;"></i>
                                        <div class="text-start">
                                            <div class="fw-bold">Drop Files Here</div>
                                            <small class="text-muted">Or click to browse files</small>
                                        </div>
                                    </div>
                                    <div class="text-end">
                                        <small class="text-primary">Browse</small>
                                    </div>
                                </div>
                            </div>
                        </div>
                        
                        <!-- Hidden File Input -->
                        <input type="file" id="fileInput" multiple accept=".pdf,.xlsx,.xls" 
                               style="display: none;" onchange="handleFileSelection()">
                        
                        <!-- Supported Formats Info -->
                        <div class="alert alert-info small mb-3">
                            <strong>Supported formats:</strong><br>
                            • STP files: ec-[account]-YYYYMM.xlsx/pdf<br>
                            • BBVA files: YYMM [AccountName].pdf or any PDF
                        </div>
                        
                        <!-- Selected Files Section -->
                        <div id="selectedFilesSection" style="display: none;">
                            <h6 class="text-primary mb-2">Selected Files:</h6>
                            <div id="selectedFilesList" class="mb-3"></div>
                        </div>
                        
                        <!-- Upload Progress -->
                        <div id="uploadProgress" style="display: none;">
                            <h6 class="text-primary mb-2">Upload Progress:</h6>
                            <div class="progress mb-2">
                                <div id="uploadProgressBar" class="progress-bar" role="progressbar" style="width: 0%"></div>
                            </div>
                            <small id="uploadStatus" class="text-muted">Preparing upload...</small>
                        </div>
                        
                        <!-- Upload Results -->
                        <div id="uploadResults" style="display: none;">
                            <h6 class="text-primary mb-2">Upload Results:</h6>
                            <div id="uploadResultsList"></div>
                        </div>
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal" id="cancelBtn">
                            <i class="fas fa-times me-1"></i>Cancel
                        </button>
                        <button type="button" class="btn btn-primary" id="uploadBtn" onclick="startUpload()" disabled>
                            <i class="fas fa-upload me-1"></i>Upload Files
                        </button>
                    </div>
                </div>
            </div>
        </div>
    `;
    
    var existingModal = document.getElementById('uploadModal');
    if (existingModal) {
        existingModal.remove();
    }
    
    document.body.insertAdjacentHTML('beforeend', modalHtml);
    
    var modal = new bootstrap.Modal(document.getElementById('uploadModal'));
    modal.show();
    
    document.getElementById('uploadModal').addEventListener('hidden.bs.modal', function() {
        selectedFiles = null;
        var fileInput = document.getElementById('fileInput');
        if (fileInput) {
            fileInput.value = '';
        }
        this.remove();
    });
}

// File Drop Zone Handlers
function handleDragOver(event) {
    event.preventDefault();
    event.dataTransfer.dropEffect = 'copy';
}

function handleDragEnter(event) {
    event.preventDefault();
    var dropZone = document.getElementById('fileDropZone');
    if (dropZone) {
        dropZone.classList.add('border-success');
        dropZone.classList.remove('btn-outline-primary');
        dropZone.classList.add('btn-outline-success');
    }
}

function handleDragLeave(event) {
    event.preventDefault();
    var dropZone = document.getElementById('fileDropZone');
    if (dropZone && !dropZone.contains(event.relatedTarget)) {
        dropZone.classList.remove('border-success', 'btn-outline-success');
        dropZone.classList.add('btn-outline-primary');
    }
}

function handleFileDrop(event) {
    event.preventDefault();
    
    var dropZone = document.getElementById('fileDropZone');
    if (dropZone) {
        dropZone.classList.remove('border-success', 'btn-outline-success');
        dropZone.classList.add('btn-outline-primary');
    }
    
    var files = event.dataTransfer.files;
    if (files.length > 0) {
        selectedFiles = files;
        displaySelectedFiles(files);
    }
}

function handleFileSelection() {
    var fileInput = document.getElementById('fileInput');
    if (fileInput.files.length > 0) {
        selectedFiles = fileInput.files;
        displaySelectedFiles(fileInput.files);
    }
}

/**
 * Display selected files with validation
 * @param {FileList} files - Selected files to display
 */
function displaySelectedFiles(files) {
    var selectedFilesSection = document.getElementById('selectedFilesSection');
    var selectedFilesList = document.getElementById('selectedFilesList');
    var uploadBtn = document.getElementById('uploadBtn');
    
    if (!selectedFilesSection || !selectedFilesList || !uploadBtn) {
        return;
    }
    
    selectedFilesList.innerHTML = '';
    var validFiles = 0;
    
    Array.from(files).forEach(function(file, index) {
        var fileItem = document.createElement('div');
        fileItem.className = 'border rounded p-2 mb-2 d-flex justify-content-between align-items-center';
        
        var validation = validateUploadFile(file);
        var isValid = validation.valid;
        
        if (isValid) {
            validFiles++;
            fileItem.classList.add('border-success', 'bg-light');
        } else {
            fileItem.classList.add('border-danger', 'bg-light');
        }
        
        var icon = 'fa-file';
        var iconColor = 'text-muted';
        
        if (file.name.toLowerCase().endsWith('.pdf')) {
            icon = 'fa-file-pdf';
            iconColor = 'text-danger';
        } else if (file.name.toLowerCase().match(/\.(xlsx|xls)$/)) {
            icon = 'fa-file-excel';
            iconColor = 'text-success';
        }
        
        fileItem.innerHTML = `
            <div class="d-flex align-items-center">
                <i class="fas ${icon} ${iconColor} me-2"></i>
                <div>
                    <div class="fw-bold">${file.name}</div>
                    <small class="text-muted">${(file.size / 1024 / 1024).toFixed(2)} MB</small>
                    ${!isValid ? `<br><small class="text-danger">${validation.error}</small>` : ''}
                    ${isValid && validation.info ? `<br><small class="text-info">${validation.info}</small>` : ''}
                </div>
            </div>
            <span class="badge ${isValid ? 'bg-success' : 'bg-danger'}">
                ${isValid ? '✓ Valid' : '✗ Invalid'}
            </span>
        `;
        
        selectedFilesList.appendChild(fileItem);
    });
    
    selectedFilesSection.style.display = 'block';
    uploadBtn.disabled = validFiles === 0;
    
    if (validFiles > 0) {
        uploadBtn.innerHTML = `<i class="fas fa-upload me-1"></i>Upload ${validFiles} File${validFiles > 1 ? 's' : ''}`;
    } else {
        uploadBtn.innerHTML = '<i class="fas fa-upload me-1"></i>Upload Files';
    }
}

/**
 * Validate uploaded file format and size
 * @param {File} file - File to validate
 * @returns {Object} Validation result with valid flag and messages
 */
function validateUploadFile(file) {
    var fileName = file.name.toLowerCase();
    var validExtensions = ['.pdf', '.xlsx', '.xls'];
    var hasValidExtension = validExtensions.some(ext => fileName.endsWith(ext));
    
    if (!hasValidExtension) {
        return {
            valid: false,
            error: 'Invalid file type. Use PDF, XLSX, or XLS files.'
        };
    }
    
    var maxSize = 50 * 1024 * 1024; // 50MB
    if (file.size > maxSize) {
        return {
            valid: false,
            error: 'File too large. Maximum size is 50MB.'
        };
    }
    
    // Check STP pattern
    var stpPattern = /^ec-(\d{18})-(\d{4})(\d{2})\.(pdf|xlsx|xls)$/;
    var stpMatch = fileName.match(stpPattern);
    
    if (stpMatch) {
        return {
            valid: true,
            info: `STP file: ${stpMatch[1]} - ${stpMatch[2]}/${stpMatch[3]}`
        };
    }
    
    // Check BBVA pattern
    var bbvaPattern = /^(\d{4})\s+(.+?)\.(pdf)$/;
    var bbvaMatch = fileName.match(bbvaPattern);
    
    if (bbvaMatch) {
        return {
            valid: true,
            info: `BBVA file: ${bbvaMatch[1]} - ${bbvaMatch[2]}`
        };
    }
    
    // PDF files are valid for auto-detection
    if (fileName.endsWith('.pdf')) {
        return {
            valid: true,
            info: 'PDF file - will auto-detect account'
        };
    }
    
    return {
        valid: false,
        error: 'Filename doesn\'t match expected patterns'
    };
}

/**
 * Start file upload process
 */
function startUpload() {
    var fileInput = document.getElementById('fileInput');
    var uploadProgress = document.getElementById('uploadProgress');
    var uploadStatus = document.getElementById('uploadStatus');
    var uploadBtn = document.getElementById('uploadBtn');
    var cancelBtn = document.querySelector('#uploadModal .btn-secondary');
    
    if (!fileInput) {
        alert('Error: File input not found on page');
        return;
    }
    
    var filesToUpload = selectedFiles || fileInput.files;
    
    if (!filesToUpload || filesToUpload.length === 0) {
        alert('Please select files to upload');
        return;
    }
    
    if (uploadProgress) {
        uploadProgress.style.display = 'block';
    }
    
    if (uploadBtn) {
        uploadBtn.disabled = true;
    }
    
    if (cancelBtn) {
        cancelBtn.disabled = true;
    }
    
    var formData = new FormData();
    Array.from(filesToUpload).forEach(function(file, index) {
        formData.append('files', file);
    });
    
    if (uploadStatus) {
        uploadStatus.textContent = 'Uploading files...';
    }
    
    var progressBar = document.getElementById('uploadProgressBar');
    if (progressBar) {
        progressBar.style.width = '20%';
        progressBar.className = 'progress-bar bg-primary';
    }
    
    fetch('/api/statements/upload', {
        method: 'POST',
        body: formData
    })
    .then(function(response) {
        if (uploadStatus) {
            uploadStatus.textContent = 'Processing response...';
        }
        
        if (progressBar) {
            progressBar.style.width = '60%';
        }
        
        if (!response.ok) {
            throw new Error('Upload failed: HTTP ' + response.status);
        }
        return response.json();
    })
    .then(function(data) {
        if (uploadStatus) {
            uploadStatus.textContent = 'Upload completed!';
        }
        
        if (progressBar) {
            progressBar.style.width = '100%';
            progressBar.className = 'progress-bar bg-success';
        }
        
        showUploadResults(data);
        storeUploadResults(data);
        
        selectedFiles = null;
        if (fileInput) {
            fileInput.value = '';
        }
        
    })
    .catch(function(error) {
        if (uploadStatus) {
            uploadStatus.textContent = 'Upload failed: ' + error.message;
        }
        
        if (progressBar) {
            progressBar.style.width = '100%';
            progressBar.className = 'progress-bar bg-danger';
        }
        
        showUploadResults({
            success: false,
            error: error.message,
            total_files: filesToUpload.length,
            successful_uploads: 0,
            failed_uploads: filesToUpload.length,
            results: []
        });
    })
    .finally(function() {
        if (cancelBtn) {
            cancelBtn.disabled = false;
            cancelBtn.innerHTML = '<i class="fas fa-times me-1"></i>Close';
        }
    });
}

/**
 * Display upload results
 * @param {Object} data - Upload result data
 */
function showUploadResults(data) {
    var uploadResults = document.getElementById('uploadResults');
    var resultsList = document.getElementById('uploadResultsList');
    
    if (!uploadResults || !resultsList) {
        if (data.success) {
            alert(`Upload successful! ${data.successful_uploads || 0} files uploaded.`);
        } else {
            alert(`Upload failed: ${data.error || 'Unknown error'}`);
        }
        return;
    }
    
    var summaryHtml = `
        <div class="alert alert-${data.success ? 'success' : 'danger'}" role="alert">
            <h6 class="alert-heading">
                <i class="fas fa-${data.success ? 'check-circle' : 'exclamation-triangle'} me-2"></i>
                Upload ${data.success ? 'Completed' : 'Failed'}
            </h6>
            <p class="mb-0">
                ${data.successful_uploads || 0} of ${data.total_files || 0} files uploaded successfully.
                ${data.failed_uploads > 0 ? `${data.failed_uploads} files failed.` : ''}
            </p>
        </div>
    `;
    
    if (data.results && data.results.length > 0) {
        summaryHtml += '<div class="list-group mt-2">';
        data.results.forEach(function(result) {
            var iconClass = result.success ? 'fa-check-circle text-success' : 'fa-times-circle text-danger';
            var message = result.success ? 
                `Uploaded to ${result.account_name || 'account'}` : 
                `Failed: ${result.error || 'Unknown error'}`;
                
            summaryHtml += `
                <div class="list-group-item d-flex justify-content-between align-items-center">
                    <div>
                        <strong>${result.filename || 'Unknown file'}</strong>
                        <small class="text-muted d-block">${message}</small>
                    </div>
                    <i class="fas ${iconClass}"></i>
                </div>
            `;
        });
        summaryHtml += '</div>';
    }
    
    resultsList.innerHTML = summaryHtml;
    uploadResults.style.display = 'block';
    
    if (data.success && data.successful_uploads > 0) {
        if (window.StatementsUI && window.StatementsUI.showAlert) {
            window.StatementsUI.showAlert('info', 'Files uploaded successfully! Refreshing calendar...');
        }
        
        refreshCalendarForUploadedFiles(data.results);
    }
}

/**
 * Show STP file selection modal
 * @param {string} accountId - Account identifier
 * @param {number} month - Month number
 * @param {Object} monthData - Month data with file availability
 */
function showSTPFileSelectionModal(accountId, month, monthData) {
    var monthNames = ['', 'January', 'February', 'March', 'April', 'May', 'June', 
                     'July', 'August', 'September', 'October', 'November', 'December'];
    
    var modalHtml = `
        <div class="modal fade" id="stpFileSelectionModal" tabindex="-1" aria-hidden="true">
            <div class="modal-dialog modal-dialog-centered">
                <div class="modal-content">
                    <div class="modal-header bg-primary text-white">
                        <h5 class="modal-title">
                            <i class="fas fa-download me-2"></i>
                            Select File to Download
                        </h5>
                        <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button>
                    </div>
                    <div class="modal-body">
                        <div class="text-center mb-3">
                            <h6 class="text-primary">${accountId.toUpperCase().replace('_', ' ')}</h6>
                            <p class="text-muted mb-0">${monthNames[month]} ${window.StatementsApp.currentYear}</p>
                        </div>
                        
                        <div class="d-grid gap-3">
                            <button type="button" class="btn btn-outline-success btn-lg file-option-btn" 
                                    onclick="downloadFileFromModal('${accountId}', ${month}, 'xlsx')">
                                <div class="d-flex align-items-center justify-content-between">
                                    <div class="d-flex align-items-center">
                                        <i class="fas fa-file-excel text-success me-3" style="font-size: 1.8rem;"></i>
                                        <div class="text-start">
                                            <div class="fw-bold">Excel Statement</div>
                                            <small class="text-muted">Detailed transaction data (.xlsx)</small>
                                        </div>
                                    </div>
                                    <div class="text-end">
                                        <small class="text-success">Spreadsheet</small>
                                    </div>
                                </div>
                            </button>
                            
                            <button type="button" class="btn btn-outline-danger btn-lg file-option-btn"
                                    onclick="downloadFileFromModal('${accountId}', ${month}, 'pdf')">
                                <div class="d-flex align-items-center justify-content-between">
                                    <div class="d-flex align-items-center">
                                        <i class="fas fa-file-pdf text-danger me-3" style="font-size: 1.8rem;"></i>
                                        <div class="text-start">
                                            <div class="fw-bold">PDF Statement</div>
                                            <small class="text-muted">Bank statement (.pdf)</small>
                                        </div>
                                    </div>
                                    <div class="text-end">
                                        <small class="text-danger">Document</small>
                                    </div>
                                </div>
                            </button>
                        </div>
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">
                            <i class="fas fa-times me-1"></i>Cancel
                        </button>
                    </div>
                </div>
            </div>
        </div>
    `;
    
    var existingModal = document.getElementById('stpFileSelectionModal');
    if (existingModal) {
        existingModal.remove();
    }
    
    document.body.insertAdjacentHTML('beforeend', modalHtml);
    
    var modalElement = document.getElementById('stpFileSelectionModal');
    var modal = new bootstrap.Modal(modalElement);
    modal.show();
    
    modalElement.addEventListener('hidden.bs.modal', function() {
        this.remove();
    });
}

function closeModal(modalId) {
    var modal = bootstrap.Modal.getInstance(document.getElementById(modalId));
    if (modal) {
        modal.hide();
    }
}

/**
 * Download file from modal selection
 * @param {string} accountId - Account identifier
 * @param {number} month - Month number
 * @param {string} fileType - File type (pdf/xlsx)
 */
function downloadFileFromModal(accountId, month, fileType) {
    var modal = bootstrap.Modal.getInstance(document.getElementById('stpFileSelectionModal'));
    if (modal) {
        modal.hide();
    }
    
    downloadFile(accountId, month, fileType);
}

/**
 * Download file directly
 * @param {string} accountId - Account identifier
 * @param {number} month - Month number
 * @param {string} fileType - File type (pdf/xlsx)
 */
function downloadFile(accountId, month, fileType) {
    var year = window.StatementsApp.currentYear;
    var monthPadded = month.toString().padStart(2, '0');
    var downloadUrl = `/statements/download/${accountId}/${month}/${fileType}?year=${year}`;
    
    window.StatementsUI.showAlert('info', `Preparing ${fileType.toUpperCase()} download...`);
    
    var link = document.createElement('a');
    link.href = downloadUrl;
    link.download = `${accountId}_${year}_${monthPadded}.${fileType}`;
    link.style.display = 'none';
    
    link.addEventListener('click', function() {
        setTimeout(function() {
            window.StatementsUI.showAlert('success', 
                `${fileType.toUpperCase()} file download started: ${accountId}_${year}_${monthPadded}.${fileType}`
            );
        }, 500);
    });
    
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
}

function showSuccessModal(accountId, accountData) {
    var fileCount = accountData.total_files || 0;
    var transactionCount = accountData.total_transactions || 0;
    
    var modalHtml = `
        <div class="modal fade" id="successModal" tabindex="-1" aria-hidden="true">
            <div class="modal-dialog modal-dialog-centered">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title">
                            <i class="fas fa-check-circle text-success me-2"></i>
                            Files Loaded Successfully
                        </h5>
                        <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                    </div>
                    <div class="modal-body text-center py-4">
                        <div class="mb-3">
                            <i class="fas fa-file-check text-success" style="font-size: 3rem;"></i>
                        </div>
                        <h6>Account: <span class="text-primary">${accountId.toUpperCase()}</span></h6>
                        <div class="row mt-3">
                            <div class="col-6">
                                <div class="bg-light rounded p-2">
                                    <div class="text-muted small">Files Loaded</div>
                                    <div class="h5 mb-0 text-success">${fileCount}</div>
                                </div>
                            </div>
                            <div class="col-6">
                                <div class="bg-light rounded p-2">
                                    <div class="text-muted small">Transactions</div>
                                    <div class="h5 mb-0 text-info">${transactionCount.toLocaleString()}</div>
                                </div>
                            </div>
                        </div>
                        <p class="text-muted mt-3 mb-0">
                            Data for ${window.StatementsApp.currentYear} is now ready for parsing.
                        </p>
                    </div>
                    <div class="modal-footer justify-content-center">
                        <button type="button" class="btn btn-success" data-bs-dismiss="modal">
                            <i class="fas fa-thumbs-up me-1"></i>Great!
                        </button>
                    </div>
                </div>
            </div>
        </div>
    `;
    
    var existingModal = document.getElementById('successModal');
    if (existingModal) {
        existingModal.remove();
    }
    
    document.body.insertAdjacentHTML('beforeend', modalHtml);
    
    var modal = new bootstrap.Modal(document.getElementById('successModal'));
    modal.show();
    
    document.getElementById('successModal').addEventListener('hidden.bs.modal', function() {
        this.remove();
    });
}

function showNoAdditionalFilesModal(accountId) {
    var modalHtml = `
        <div class="modal fade" id="noFilesModal" tabindex="-1" aria-hidden="true">
            <div class="modal-dialog modal-dialog-centered">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title">
                            <i class="fas fa-info-circle text-info me-2"></i>
                            No Additional Files
                        </h5>
                        <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                    </div>
                    <div class="modal-body text-center py-4">
                        <div class="mb-3">
                            <i class="fas fa-folder-open text-muted" style="font-size: 3rem;"></i>
                        </div>
                        <h6>Account: <span class="text-primary">${accountId.toUpperCase()}</span></h6>
                        <p class="text-muted mb-0">
                            All available files for ${window.StatementsApp.currentYear} have already been loaded.
                        </p>
                    </div>
                    <div class="modal-footer justify-content-center">
                        <button type="button" class="btn btn-primary" data-bs-dismiss="modal">
                            <i class="fas fa-check me-1"></i>OK
                        </button>
                    </div>
                </div>
            </div>
        </div>
    `;
    
    var existingModal = document.getElementById('noFilesModal');
    if (existingModal) {
        existingModal.remove();
    }
    
    document.body.insertAdjacentHTML('beforeend', modalHtml);
    
    var modal = new bootstrap.Modal(document.getElementById('noFilesModal'));
    modal.show();
    
    document.getElementById('noFilesModal').addEventListener('hidden.bs.modal', function() {
        this.remove();
    });
}

function handleYearChange(newYear) {
    var oldYear = window.StatementsApp.currentYear;
    
    if (oldYear === parseInt(newYear)) return;
    
    showYearTransition(newYear);
    
    fetch('/api/statements/ui-data/' + newYear)
        .then(function(response) {
            if (!response.ok) throw new Error('Failed to load year data');
            return response.json();
        })
        .then(function(data) {
            if (data.success) {
                window.StatementsApp.currentYear = parseInt(newYear);
                clearAllAccountUI();
                displayUIData(data.ui_data);
                
                var newUrl = '/statements/' + newYear;
                history.pushState({year: parseInt(newYear)}, '', newUrl);
                
                hideYearTransition();
            } else {
                throw new Error(data.error || 'Failed to load year data');
            }
        })
        .catch(function(error) {
            window.StatementsUI.showAlert('danger', 'Failed to load year: ' + error.message);
            
            var yearSelector = document.getElementById('yearSelector');
            if (yearSelector) {
                yearSelector.value = oldYear;
            }
            
            hideYearTransition();
        });
}

function showYearTransition(newYear) {
    var tableContainer = document.querySelector('.table-container');
    if (tableContainer) {
        tableContainer.style.opacity = '0.6';
        tableContainer.style.pointerEvents = 'none';
    }
    
    window.StatementsUI.showAlert('info', 'Loading ' + newYear + ' data...');
}

function hideYearTransition() {
    var tableContainer = document.querySelector('.table-container');
    if (tableContainer) {
        tableContainer.style.opacity = '1';
        tableContainer.style.pointerEvents = 'auto';
    }
}

function clearAllAccountUI() {
    window.StatementsApp.accountIds.forEach(function(accountId) {
        var loadBtn = document.getElementById('load-btn-' + accountId);
        if (loadBtn) {
            loadBtn.innerHTML = '<i class="fas fa-sync-alt"></i>';
            loadBtn.className = 'btn btn-primary btn-sm';
        }
        
        var parseBtn = document.getElementById('parse-btn-' + accountId);
        if (parseBtn) {
            parseBtn.style.display = 'none';
        }
        
        for (var month = 1; month <= 12; month++) {
            var fileIcon = document.getElementById('file-icon-' + accountId + '-' + month);
            var dbIcon = document.getElementById('db-icon-' + accountId + '-' + month);
            var cell = document.querySelector('[data-account-id="' + accountId + '"][data-month="' + month + '"]');
            
            if (fileIcon) fileIcon.innerHTML = '';
            if (dbIcon) dbIcon.className = 'database-icon db-not-loaded';
            if (cell) cell.className = 'month-cell no-file';
        }
    });
}

function displayUIData(uiData) {
    for (var accountId in uiData) {
        var accountData = uiData[accountId];
        
        var loadBtn = document.getElementById('load-btn-' + accountId);
        if (loadBtn) {
            loadBtn.innerHTML = '<i class="fas fa-check-circle"></i>';
            loadBtn.className = 'btn btn-success btn-sm';
        }
        
        var parseBtn = document.getElementById('parse-btn-' + accountId);
        if (parseBtn) {
            parseBtn.style.display = 'inline-block';
        }
        
        accountData.months.forEach(function(monthData) {
            var month = monthData.month;
            var fileIcon = document.getElementById('file-icon-' + accountId + '-' + month);
            var dbIcon = document.getElementById('db-icon-' + accountId + '-' + month);
            var cell = document.querySelector('[data-account-id="' + accountId + '"][data-month="' + month + '"]');
            
            if (fileIcon) {
                var iconHtml = '';
                if (monthData.has_xlsx && monthData.has_pdf) {
                    iconHtml = '<i class="fas fa-file-excel text-success me-1"></i><i class="fas fa-file-pdf text-danger"></i>';
                } else if (monthData.has_xlsx) {
                    iconHtml = '<i class="fas fa-file-excel text-success"></i>';
                } else if (monthData.has_pdf) {
                    iconHtml = '<i class="fas fa-file-pdf text-danger"></i>';
                }
                fileIcon.innerHTML = iconHtml;
            }
            
            if (dbIcon) {
                dbIcon.className = 'database-icon db-loaded';
            }
            
            if (cell) {
                cell.className = 'month-cell';
            }
        });
    }
}

function refreshCalendarForUploadedFiles(uploadResults) {
    if (!uploadResults || uploadResults.length === 0) {
        return;
    }
    
    var accountsToRefresh = new Set();
    
    uploadResults.forEach(function(result) {
        if (result.success && result.account_name) {
            var accountId = mapAccountNameToId(result.account_name);
            if (accountId) {
                accountsToRefresh.add(accountId);
            }
        }
    });
    
    if (accountsToRefresh.size === 0) {
        return;
    }
    
    var refreshPromises = [];
    
    accountsToRefresh.forEach(function(accountId) {
        var promise = refreshSingleAccountCalendar(accountId);
        refreshPromises.push(promise);
    });
    
    Promise.allSettled(refreshPromises).then(function(results) {
        var successful = results.filter(r => r.status === 'fulfilled').length;
        
        if (successful > 0 && window.StatementsUI && window.StatementsUI.showAlert) {
            window.StatementsUI.showAlert('success', 
                `Calendar updated! ${successful} account${successful > 1 ? 's' : ''} refreshed.`
            );
        }
    });
}

function mapAccountNameToId(accountName) {
    var accountMappings = {
        'STP SA': 'stp_sa',
        'STP IP - PD': 'stp_ip_pd', 
        'STP IP - PI': 'stp_ip_pi',
        'BBVA MX MXN': 'bbva_mx_mxn',
        'BBVA MX USD': 'bbva_mx_usd',
        'BBVA SA MXN': 'bbva_sa_mxn',
        'BBVA SA USD': 'bbva_sa_usd',
        'BBVA IP Corp': 'bbva_ip_corp',
        'BBVA IP Clientes': 'bbva_ip_clientes'
    };
    
    return accountMappings[accountName] || null;
}

function refreshSingleAccountCalendar(accountId) {
    return new Promise(function(resolve, reject) {
        if (!window.StatementsAPI || !window.StatementsAPI.loadAccount) {
            resolve(accountId);
            return;
        }
        
        window.StatementsAPI.loadAccount(accountId)
            .then(function(accountData) {
                if (window.StatementsUI && window.StatementsUI.updateAccountDisplay) {
                    window.StatementsUI.updateAccountDisplay(accountId, accountData);
                }
                
                if (window.StatementsUI && window.StatementsUI.updateLoadButton) {
                    window.StatementsUI.updateLoadButton(accountId, true);
                }
                
                resolve(accountId);
            })
            .catch(function(error) {
                reject(error);
            });
    });
}

function loadAccountData(accountId) {
    var loadBtn = document.getElementById('load-btn-' + accountId);
    
    if (!loadBtn) {
        return;
    }
    
    loadBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';
    loadBtn.disabled = true;
    
    window.StatementsUI.showAlert('info', 'Loading account data...');
    
    window.StatementsAPI.loadAccount(accountId)
        .then(function(accountData) {
            window.StatementsUI.updateAccountDisplay(accountId, accountData);
            
            window.StatementsUI.updateLoadButton(accountId, true);
            loadBtn.disabled = false;
            
            var parseBtn = document.getElementById('parse-btn-' + accountId);
            if (parseBtn) {
                parseBtn.style.display = 'inline-block';
            }
            
            var fileCount = accountData.total_files || 0;
            var transactionCount = accountData.total_transactions || 0;
            
            window.StatementsUI.showAlert('success', 
                `${accountId.toUpperCase()}: ${fileCount} files loaded, ${transactionCount.toLocaleString()} transactions`
            );
            
            if (fileCount > 0) {
                showSuccessModal(accountId, accountData);
            } else {
                showNoAdditionalFilesModal(accountId);
            }
        })
        .catch(function(error) {
            loadBtn.innerHTML = '<i class="fas fa-download"></i>';
            loadBtn.disabled = false;
            
            window.StatementsUI.showAlert('danger', 
                'Failed to load account data: ' + error.message
            );
        });
}

document.addEventListener('DOMContentLoaded', function() {
    var recentUploads = sessionStorage.getItem('recentUploads');
    
    if (recentUploads) {
        try {
            var uploadData = JSON.parse(recentUploads);
            if (uploadData.timestamp && Date.now() - uploadData.timestamp < 60000) {
                refreshCalendarForUploadedFiles(uploadData.results);
            }
        } catch (e) {
            // Ignore errors in parsing upload data
        }
        
        sessionStorage.removeItem('recentUploads');
    }
});

function storeUploadResults(data) {
    if (data.success && data.results) {
        try {
            sessionStorage.setItem('recentUploads', JSON.stringify({
                results: data.results,
                timestamp: Date.now()
            }));
        } catch (e) {
            // Ignore storage errors
        }
    }
}

/**
 * Start parse operation for account
 * @param {string} accountId - Account identifier
 */
function parseAccountRow(accountId) {
    var accountName = accountId.toUpperCase().replace('_', ' ');
    showParseModal(accountId, accountName);
    startParseOperation(accountId, accountName);
}

function showParseModal(accountId, accountName) {
    var modalHtml = `
        <div class="modal fade" id="parseModal" tabindex="-1" aria-hidden="true">
            <div class="modal-dialog modal-dialog-centered">
                <div class="modal-content">
                    <div class="modal-header bg-warning text-white">
                        <h5 class="modal-title">
                            <i class="fas fa-cog me-2"></i>
                            Parse Account Statements
                        </h5>
                        <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button>
                    </div>
                    <div class="modal-body">
                        <div class="text-center mb-3">
                            <h6 class="text-warning">${accountName}</h6>
                            <p class="text-muted mb-0">Processing statement files and extracting transactions</p>
                        </div>
                        
                        <div id="parseProgress" style="display: block;">
                            <h6 class="text-warning mb-2">Parse Progress:</h6>
                            <div class="progress mb-2">
                                <div id="parseProgressBar" class="progress-bar bg-warning" role="progressbar" style="width: 0%"></div>
                            </div>
                            <small id="parseStatus" class="text-muted">Initializing parse operation...</small>
                            
                            <div id="parseDetails" class="mt-3" style="display: none;">
                                <div class="row text-center">
                                    <div class="col-4">
                                        <div class="bg-light rounded p-2">
                                            <div class="text-muted small">Files Processed</div>
                                            <div id="filesProcessedCount" class="h6 mb-0 text-warning">0</div>
                                        </div>
                                    </div>
                                    <div class="col-4">
                                        <div class="bg-light rounded p-2">
                                            <div class="text-muted small">Total Files</div>
                                            <div id="totalFilesCount" class="h6 mb-0 text-info">-</div>
                                        </div>
                                    </div>
                                    <div class="col-4">
                                        <div class="bg-light rounded p-2">
                                            <div class="text-muted small">Transactions</div>
                                            <div id="transactionsCount" class="h6 mb-0 text-success">0</div>
                                        </div>
                                    </div>
                                </div>
                                
                                <div id="currentFileSection" class="mt-3" style="display: none;">
                                    <div class="alert alert-info small mb-0">
                                        <strong>Processing:</strong> <span id="currentFileName">-</span>
                                    </div>
                                </div>
                            </div>
                        </div>
                        
                        <div id="parseResults" style="display: none;">
                            <h6 class="text-warning mb-2">Parse Results:</h6>
                            <div id="parseResultsList"></div>
                        </div>
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal" id="parseCloseBtn">
                            <i class="fas fa-times me-1"></i>Cancel
                        </button>
                    </div>
                </div>
            </div>
        </div>
    `;
    
    var existingModal = document.getElementById('parseModal');
    if (existingModal) {
        existingModal.remove();
    }
    
    document.body.insertAdjacentHTML('beforeend', modalHtml);
    
    var modal = new bootstrap.Modal(document.getElementById('parseModal'));
    modal.show();
    
    document.getElementById('parseModal').addEventListener('hidden.bs.modal', function() {
        this.remove();
    });
}

function startParseOperation(accountId, accountName) {
    var parseStatus = document.getElementById('parseStatus');
    var parseProgressBar = document.getElementById('parseProgressBar');
    var parseCloseBtn = document.getElementById('parseCloseBtn');
    
    if (parseStatus) {
        parseStatus.textContent = 'Starting parse operation...';
    }
    
    if (parseProgressBar) {
        parseProgressBar.style.width = '10%';
    }
    
    if (parseCloseBtn) {
        parseCloseBtn.disabled = true;
    }
    
    window.StatementsAPI.parseAccount(accountId)
        .then(function(response) {
            if (parseStatus) {
                parseStatus.textContent = 'Parse operation started, tracking progress...';
            }
            
            if (parseProgressBar) {
                parseProgressBar.style.width = '20%';
            }
            
            startParseProgressPolling(response.session_id, accountId, accountName);
        })
        .catch(function(error) {
            if (parseStatus) {
                parseStatus.textContent = 'Failed to start parse: ' + error.message;
            }
            
            if (parseProgressBar) {
                parseProgressBar.style.width = '100%';
                parseProgressBar.className = 'progress-bar bg-danger';
            }
            
            showParseResults({
                success: false,
                error: error.message,
                account_id: accountId,
                files_processed: 0,
                transactions_added: 0
            });
            
            if (parseCloseBtn) {
                parseCloseBtn.disabled = false;
                parseCloseBtn.innerHTML = '<i class="fas fa-times me-1"></i>Close';
            }
        });
}

function startParseProgressPolling(sessionId, accountId, accountName) {
    var progressInterval = setInterval(function() {
        window.StatementsAPI.getParseProgress(sessionId)
            .then(function(progress) {
                updateParseProgress(progress);
                
                if (progress.status === 'completed' || progress.status === 'error') {
                    clearInterval(progressInterval);
                    handleParseCompletion(progress, accountId);
                }
            })
            .catch(function(error) {
                clearInterval(progressInterval);
                
                var parseStatus = document.getElementById('parseStatus');
                if (parseStatus) {
                    parseStatus.textContent = 'Progress tracking failed: ' + error.message;
                }
            });
    }, 2000);
}

function updateParseProgress(progress) {
    var parseStatus = document.getElementById('parseStatus');
    var parseProgressBar = document.getElementById('parseProgressBar');
    var parseDetails = document.getElementById('parseDetails');
    var filesProcessedCount = document.getElementById('filesProcessedCount');
    var totalFilesCount = document.getElementById('totalFilesCount');
    var transactionsCount = document.getElementById('transactionsCount');
    var currentFileSection = document.getElementById('currentFileSection');
    var currentFileName = document.getElementById('currentFileName');
    
    if (parseProgressBar) {
        parseProgressBar.style.width = (progress.progress_percentage || 0) + '%';
        
        if (progress.status === 'error') {
            parseProgressBar.className = 'progress-bar bg-danger';
        } else if (progress.progress_percentage >= 100) {
            parseProgressBar.className = 'progress-bar bg-success';
        } else {
            parseProgressBar.className = 'progress-bar bg-warning';
        }
    }
    
    if (parseStatus) {
        var statusText = progress.details || progress.status || 'Processing...';
        parseStatus.textContent = statusText;
    }
    
    if (parseDetails && (progress.total_files || progress.files_processed || progress.transactions_added)) {
        parseDetails.style.display = 'block';
        
        if (filesProcessedCount) {
            filesProcessedCount.textContent = progress.files_processed || 0;
        }
        
        if (totalFilesCount && progress.total_files) {
            totalFilesCount.textContent = progress.total_files;
        }
        
        if (transactionsCount) {
            transactionsCount.textContent = progress.transactions_added || 0;
        }
    }
    
    if (currentFileSection && currentFileName && progress.current_file) {
        currentFileSection.style.display = 'block';
        currentFileName.textContent = progress.current_file;
    } else if (currentFileSection && !progress.current_file) {
        currentFileSection.style.display = 'none';
    }
}

function handleParseCompletion(progress, accountId) {
    var parseStatus = document.getElementById('parseStatus');
    var parseCloseBtn = document.getElementById('parseCloseBtn');
    
    if (progress.status === 'completed') {
        if (parseStatus) {
            parseStatus.textContent = 'Parse completed successfully!';
        }
        
        var resultData = {
            success: true,
            files_processed: progress.files_processed || 0,
            files_skipped: progress.files_skipped || 0,
            transactions_added: progress.transactions_added || 0,
            total_files: progress.total_files || 0,
            message: progress.details || 'Parse completed successfully',
            errors: progress.errors || []
        };
        
        showParseResults(resultData);
        refreshAccountAfterParse(accountId);
        
    } else if (progress.status === 'error') {
        if (parseStatus) {
            parseStatus.textContent = 'Parse failed: ' + (progress.error || 'Unknown error');
        }
        
        showParseResults({
            success: false,
            error: progress.error || 'Parse operation failed',
            account_id: accountId,
            files_processed: progress.files_processed || 0,
            transactions_added: progress.transactions_added || 0
        });
    }
    
    if (parseCloseBtn) {
        parseCloseBtn.disabled = false;
        parseCloseBtn.innerHTML = '<i class="fas fa-check me-1"></i>Close';
    }
}

function showParseResults(result) {
    var parseResults = document.getElementById('parseResults');
    var parseResultsList = document.getElementById('parseResultsList');
    
    if (!parseResults || !parseResultsList) {
        return;
    }
    
    var isSuccess = result.success;
    var filesProcessed = result.files_processed || 0;
    var filesSkipped = result.files_skipped || 0;
    var transactionsAdded = result.transactions_added || 0;
    var totalFiles = result.total_files || filesProcessed + filesSkipped;
    
    var messageText = '';
    var isAllCurrent = isSuccess && filesProcessed === 0 && filesSkipped > 0;
    
    if (isAllCurrent) {
        messageText = `All ${filesSkipped} files are already up to date. No parsing needed.`;
    } else if (isSuccess && filesProcessed > 0) {
        messageText = `${filesProcessed} files processed successfully. ${transactionsAdded} transactions added to database.`;
        if (filesSkipped > 0) {
            messageText += ` ${filesSkipped} files were already current.`;
        }
    } else if (!isSuccess) {
        messageText = `Parse failed. ${filesProcessed} files processed. ${transactionsAdded} transactions added.`;
    } else {
        messageText = `${filesProcessed} files processed successfully. ${transactionsAdded} transactions added to database.`;
    }
    
    var summaryHtml = `
        <div class="alert alert-${isSuccess ? 'success' : 'danger'}" role="alert">
            <h6 class="alert-heading">
                <i class="fas fa-${isSuccess ? 'check-circle' : 'exclamation-triangle'} me-2"></i>
                Parse ${isSuccess ? 'Completed' : 'Failed'}
            </h6>
            <p class="mb-0">${messageText}</p>
        </div>
    `;
    
    if (isSuccess) {
        summaryHtml += `
            <div class="row mt-2">
                <div class="col-4">
                    <div class="bg-light rounded p-2 text-center">
                        <div class="text-muted small">Files Checked</div>
                        <div class="h5 mb-0 text-info">${totalFiles}</div>
                    </div>
                </div>
                <div class="col-4">
                    <div class="bg-light rounded p-2 text-center">
                        <div class="text-muted small">${isAllCurrent ? 'Already Current' : 'Processed'}</div>
                        <div class="h5 mb-0 text-${isAllCurrent ? 'success' : 'warning'}">${isAllCurrent ? filesSkipped : filesProcessed}</div>
                    </div>
                </div>
                <div class="col-4">
                    <div class="bg-light rounded p-2 text-center">
                        <div class="text-muted small">Transactions Added</div>
                        <div class="h5 mb-0 text-success">${transactionsAdded}</div>
                    </div>
                </div>
            </div>
        `;
        
        if (isAllCurrent) {
            summaryHtml += `
                <div class="mt-2 alert alert-info small">
                    <i class="fas fa-info-circle me-1"></i>
                    All files have been parsed previously and are up to date. This is the expected result for accounts that have already been processed.
                </div>
            `;
        }
    }
    
    if (result.errors && result.errors.length > 0) {
        summaryHtml += '<div class="mt-2"><strong>Errors encountered:</strong><ul class="small">';
        result.errors.forEach(function(error) {
            summaryHtml += `<li class="text-danger">${error}</li>`;
        });
        summaryHtml += '</ul></div>';
    }
    
    parseResultsList.innerHTML = summaryHtml;
    parseResults.style.display = 'block';
}

function refreshAccountAfterParse(accountId) {
    if (window.StatementsUI && window.StatementsUI.showAlert) {
        window.StatementsUI.showAlert('info', 'Parse completed! Refreshing inventory...');
    }
    
    fetch('/api/statements/refresh-inventory/' + accountId, {
        method: 'POST'
    })
    .then(function(response) {
        return response.json();
    })
    .then(function(refreshResult) {
        setTimeout(function() {
            window.StatementsAPI.loadAccount(accountId)
                .then(function(accountData) {
                    if (window.StatementsUI && window.StatementsUI.updateAccountDisplay) {
                        window.StatementsUI.updateAccountDisplay(accountId, accountData);
                    }
                    
                    if (window.StatementsUI && window.StatementsUI.showAlert) {
                        window.StatementsUI.showAlert('success', 'Account data refreshed successfully!');
                    }
                })
                .catch(function(error) {
                    if (window.StatementsUI && window.StatementsUI.showAlert) {
                        window.StatementsUI.showAlert('danger', 'Failed to refresh account data');
                    }
                });
        }, 2000);
    })
    .catch(function(error) {
        if (window.StatementsUI && window.StatementsUI.showAlert) {
            window.StatementsUI.showAlert('warning', 'Inventory refresh failed, loading cached data...');
        }
        
        window.StatementsAPI.loadAccount(accountId)
            .then(function(accountData) {
                window.StatementsUI.updateAccountDisplay(accountId, accountData);
            });
    });
}

// Initialize application
document.addEventListener('DOMContentLoaded', function() {
    var templateYear = document.querySelector('meta[name="current-year"]');
    var currentYear = templateYear ? templateYear.content : '2025';
    
    window.StatementsApp.init(currentYear);
    
    var yearSelector = document.getElementById('yearSelector');
    if (yearSelector) {
        yearSelector.value = window.StatementsApp.currentYear.toString();
        yearSelector.addEventListener('change', function(e) {
            handleYearChange(e.target.value);
        });
    }
});

// Handle browser navigation
window.addEventListener('popstate', function(event) {
    if (event.state && event.state.year) {
        var targetYear = event.state.year;
        var yearSelector = document.getElementById('yearSelector');
        
        if (yearSelector) {
            yearSelector.value = targetYear;
            handleYearChange(targetYear);
        }
    }
});

// Set initial history state
document.addEventListener('DOMContentLoaded', function() {
    var currentYear = window.StatementsApp.currentYear;
    history.replaceState({year: currentYear}, '', '/statements/' + currentYear);
});