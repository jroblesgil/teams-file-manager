// Complete main.js file with upload functionality - FIXED VERSION
// Store files globally for drag-and-drop
var selectedFiles = null;

function refreshAccountInventory(accountId) {
    var loadBtn = document.getElementById('load-btn-' + accountId);
    if (loadBtn) {
        loadBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';
        loadBtn.disabled = true;
    }
    
    // Skip the API call, go directly to background task
    var currentYear = window.StatementsApp.currentYear || 2025;
    window.location.href = '/statements/refresh-progress/' + accountId + '?year=' + currentYear;
}

// Debug version of downloadMonthFile to identify the issue
function downloadMonthFile(accountId, month) {
    console.log('=== DOWNLOAD DEBUG START ===');
    console.log('Function called with:', { accountId, month });
    
    // Convert month to number if it's a string
    month = parseInt(month, 10);
    console.log('Converted month to integer:', month);
    
    // Get all the DOM elements we need
    var fileIcon = document.getElementById('file-icon-' + accountId + '-' + month);
    var cell = document.querySelector('[data-account-id="' + accountId + '"][data-month="' + month + '"]');
    var accountRow = document.querySelector('[data-account-id="' + accountId + '"]');
    
    console.log('DOM Elements Found:');
    console.log('  - File Icon:', fileIcon ? 'YES' : 'NO');
    console.log('  - Cell:', cell ? 'YES' : 'NO');  
    console.log('  - Account Row:', accountRow ? 'YES' : 'NO');
    
    if (!fileIcon || !cell) {
        console.error('Missing DOM elements! Cannot proceed.');
        window.StatementsUI.showAlert('danger', 'Error: Could not find page elements');
        return;
    }
    
    // Check cell classes
    console.log('Cell classes:', cell.className);
    var hasFiles = !cell.classList.contains('no-file');
    console.log('Cell has files (no .no-file class):', hasFiles);
    
    if (!hasFiles) {
        console.log('Cell marked as no-file, showing alert');
        window.StatementsUI.showAlert('info', 'No files available for this month');
        return;
    }
    
    // Analyze file icon content
    var iconHTML = fileIcon.innerHTML;
    console.log('File icon HTML:', iconHTML);
    
    var hasExcel = iconHTML.includes('fa-file-excel');
    var hasPdf = iconHTML.includes('fa-file-pdf');
    
    console.log('File Analysis:');
    console.log('  - Has Excel icon:', hasExcel);
    console.log('  - Has PDF icon:', hasPdf);
    console.log('  - Both files:', hasExcel && hasPdf);
    
    // Get account type
    var accountType = accountRow ? accountRow.getAttribute('data-account-type') : 'unknown';
    console.log('Account type:', accountType);
    
    // Decision logic
    console.log('=== DECISION LOGIC ===');
    if (accountType === 'stp' && hasExcel && hasPdf) {
        console.log('DECISION: Show STP selection modal (both files available)');
        showSTPFileSelectionModal(accountId, month, { hasExcel, hasPdf, iconHTML });
        return;
    } else if (hasExcel && !hasPdf) {
        console.log('DECISION: Download Excel file directly');
        downloadFile(accountId, month, 'xlsx');
        return;
    } else if (hasPdf && !hasExcel) {
        console.log('DECISION: Download PDF file directly');
        downloadFile(accountId, month, 'pdf');
        return;
    } else if (hasExcel && hasPdf) {
        console.log('DECISION: BBVA account with both files - download PDF');
        downloadFile(accountId, month, 'pdf');
        return;
    } else {
        console.log('DECISION: No files available');
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
            // Simple approach: reload after delay
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

// UPLOAD FUNCTIONALITY - IMPLEMENTED TO MATCH STP MODAL STYLING
function uploadToTeams() {
    console.log('=== OPENING UPLOAD MODAL ===');
    showUploadModal();
}

function showUploadModal() {
    console.log('Creating upload modal with STP modal styling...');
    
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
    
    // Remove existing modal if present
    var existingModal = document.getElementById('uploadModal');
    if (existingModal) {
        existingModal.remove();
    }
    
    // Add modal to body
    document.body.insertAdjacentHTML('beforeend', modalHtml);
    
    // Show modal
    var modal = new bootstrap.Modal(document.getElementById('uploadModal'));
    modal.show();
    
    // Clean up after modal is hidden
    document.getElementById('uploadModal').addEventListener('hidden.bs.modal', function() {
        console.log('Upload modal closed, cleaning up...');
        // Reset file selection
        selectedFiles = null;
        var fileInput = document.getElementById('fileInput');
        if (fileInput) {
            fileInput.value = '';
        }
        this.remove();
    });
    
    console.log('Upload modal created and shown');
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
    console.log('Files dropped');
    
    var dropZone = document.getElementById('fileDropZone');
    if (dropZone) {
        dropZone.classList.remove('border-success', 'btn-outline-success');
        dropZone.classList.add('btn-outline-primary');
    }
    
    var files = event.dataTransfer.files;
    if (files.length > 0) {
        // Store files globally since we can't set fileInput.files directly
        selectedFiles = files;
        displaySelectedFiles(files);
    }
}

function handleFileSelection() {
    var fileInput = document.getElementById('fileInput');
    if (fileInput.files.length > 0) {
        console.log('Files selected via browse:', fileInput.files.length);
        // For browse selection, use fileInput.files directly
        selectedFiles = fileInput.files;
        displaySelectedFiles(fileInput.files);
    }
}

function displaySelectedFiles(files) {
    console.log('Displaying', files.length, 'selected files');
    
    var selectedFilesSection = document.getElementById('selectedFilesSection');
    var selectedFilesList = document.getElementById('selectedFilesList');
    var uploadBtn = document.getElementById('uploadBtn');
    
    if (!selectedFilesSection || !selectedFilesList || !uploadBtn) {
        console.error('Missing UI elements for file display');
        return;
    }
    
    // Clear previous files
    selectedFilesList.innerHTML = '';
    
    var validFiles = 0;
    
    // Process each file
    Array.from(files).forEach(function(file, index) {
        var fileItem = document.createElement('div');
        fileItem.className = 'border rounded p-2 mb-2 d-flex justify-content-between align-items-center';
        
        // Validate file
        var validation = validateUploadFile(file);
        var isValid = validation.valid;
        
        if (isValid) {
            validFiles++;
            fileItem.classList.add('border-success', 'bg-light');
        } else {
            fileItem.classList.add('border-danger', 'bg-light');
        }
        
        // File icon
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
    
    // Show selected files section
    selectedFilesSection.style.display = 'block';
    
    // Enable/disable upload button
    uploadBtn.disabled = validFiles === 0;
    
    if (validFiles > 0) {
        uploadBtn.innerHTML = `<i class="fas fa-upload me-1"></i>Upload ${validFiles} File${validFiles > 1 ? 's' : ''}`;
    } else {
        uploadBtn.innerHTML = '<i class="fas fa-upload me-1"></i>Upload Files';
    }
    
    console.log(`Files processed: ${validFiles}/${files.length} valid`);
}

function validateUploadFile(file) {
    // Check file extension
    var fileName = file.name.toLowerCase();
    var validExtensions = ['.pdf', '.xlsx', '.xls'];
    var hasValidExtension = validExtensions.some(ext => fileName.endsWith(ext));
    
    if (!hasValidExtension) {
        return {
            valid: false,
            error: 'Invalid file type. Use PDF, XLSX, or XLS files.'
        };
    }
    
    // Check file size (50MB limit)
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


function startUpload() {
    console.log('=== START UPLOAD (FIXED VERSION) ===');
    
    var fileInput = document.getElementById('fileInput');
    var uploadProgress = document.getElementById('uploadProgress');
    var uploadStatus = document.getElementById('uploadStatus');
    var uploadBtn = document.getElementById('uploadBtn');
    var cancelBtn = document.querySelector('#uploadModal .btn-secondary');
    
    // Check if elements exist
    if (!fileInput) {
        console.error('File input not found');
        alert('Error: File input not found on page');
        return;
    }
    
    // FIXED: Use global selectedFiles (drag-and-drop) OR fileInput.files (browse)
    var filesToUpload = selectedFiles || fileInput.files;
    
    console.log('Selected files (global):', selectedFiles);
    console.log('File input files:', fileInput.files);
    console.log('Files to upload:', filesToUpload);
    console.log('Number of files to upload:', filesToUpload ? filesToUpload.length : 0);
    
    if (!filesToUpload || filesToUpload.length === 0) {
        console.error('No files to upload');
        alert('Please select files to upload');
        return;
    }
    
    // Log each file being uploaded
    console.log('Files being uploaded:');
    Array.from(filesToUpload).forEach(function(file, index) {
        console.log(`  ${index + 1}. ${file.name} (${file.size} bytes)`);
    });
    
    // Show progress (with null checks)
    if (uploadProgress) {
        uploadProgress.style.display = 'block';
    }
    
    if (uploadBtn) {
        uploadBtn.disabled = true;
    }
    
    if (cancelBtn) {
        cancelBtn.disabled = true;
    }
    
    // Create FormData using the correct files
    var formData = new FormData();
    Array.from(filesToUpload).forEach(function(file, index) {
        console.log(`Adding file ${index + 1} to FormData: ${file.name}`);
        formData.append('files', file);
    });
    
    if (uploadStatus) {
        uploadStatus.textContent = 'Uploading files...';
    }
    
    // Update progress bar
    var progressBar = document.getElementById('uploadProgressBar');
    if (progressBar) {
        progressBar.style.width = '20%';
        progressBar.className = 'progress-bar bg-primary';
    }
    
    console.log('Making fetch request to /api/statements/upload');
    
    fetch('/api/statements/upload', {
        method: 'POST',
        body: formData
    })
    .then(function(response) {
        console.log('Upload response status:', response.status);
        
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
        console.log('Upload completed successfully:', data);
        
        if (uploadStatus) {
            uploadStatus.textContent = 'Upload completed!';
        }
        
        if (progressBar) {
            progressBar.style.width = '100%';
            progressBar.className = 'progress-bar bg-success';
        }
        
        // Show results
        showUploadResults(data);
        
        // Store results for calendar refresh
        storeUploadResults(data);
        
        // Clear selected files after successful upload
        selectedFiles = null;
        if (fileInput) {
            fileInput.value = '';
        }
        
    })
    .catch(function(error) {
        console.error('Upload error:', error);
        
        if (uploadStatus) {
            uploadStatus.textContent = 'Upload failed: ' + error.message;
        }
        
        if (progressBar) {
            progressBar.style.width = '100%';
            progressBar.className = 'progress-bar bg-danger';
        }
        
        // Show error results
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
        console.log('Upload process finished');
        
        if (cancelBtn) {
            cancelBtn.disabled = false;
            cancelBtn.innerHTML = '<i class="fas fa-times me-1"></i>Close';
        }
    });
}

function showUploadResults(data) {
    var uploadResults = document.getElementById('uploadResults');
    var resultsList = document.getElementById('uploadResultsList');
    
    // Check if elements exist
    if (!uploadResults || !resultsList) {
        console.error('Upload results elements not found');
        // Fallback to alert
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
    
    // If upload was successful, automatically refresh calendar
    if (data.success && data.successful_uploads > 0) {
        // Show immediate feedback
        if (window.StatementsUI && window.StatementsUI.showAlert) {
            window.StatementsUI.showAlert('info', 'Files uploaded successfully! Refreshing calendar...');
        }
        
        // Refresh calendar for affected accounts
        refreshCalendarForUploadedFiles(data.results);
    }
}

function validateSelectedFiles() {
    var fileInput = document.getElementById('fileInput');
    var filePreview = document.getElementById('filePreview');
    var fileList = document.getElementById('fileList');
    var uploadBtn = document.getElementById('uploadBtn');
    
    // Check if elements exist
    if (!fileInput || !filePreview || !fileList || !uploadBtn) {
        console.error('Upload modal elements not found');
        return;
    }
    
    if (fileInput.files.length === 0) {
        filePreview.style.display = 'none';
        uploadBtn.disabled = true;
        return;
    }
    
    fileList.innerHTML = '';
    var validFiles = 0;
    
    Array.from(fileInput.files).forEach(function(file, index) {
        var listItem = document.createElement('div');
        listItem.className = 'list-group-item d-flex justify-content-between align-items-center';
        
        // Validate file type
        var isValid = file.name.toLowerCase().match(/\.(pdf|xlsx|xls)$/);
        var icon = 'fa-file';
        var badgeClass = 'secondary';
        var statusText = 'Unknown format';
        
        if (file.name.toLowerCase().endsWith('.pdf')) {
            icon = 'fa-file-pdf';
            badgeClass = 'danger';
            statusText = 'PDF';
        } else if (file.name.toLowerCase().match(/\.(xlsx|xls)$/)) {
            icon = 'fa-file-excel';
            badgeClass = 'success';
            statusText = 'Excel';
        }
        
        if (isValid) {
            validFiles++;
        } else {
            badgeClass = 'warning';
            statusText = 'Invalid';
        }
        
        listItem.innerHTML = `
            <div>
                <i class="fas ${icon} me-2"></i>
                <span>${file.name}</span>
                <small class="text-muted d-block">${(file.size / 1024 / 1024).toFixed(2)} MB</small>
            </div>
            <span class="badge bg-${badgeClass}">${statusText}</span>
        `;
        
        fileList.appendChild(listItem);
    });
    
    filePreview.style.display = 'block';
    uploadBtn.disabled = validFiles === 0;
    
    if (validFiles > 0) {
        uploadBtn.innerHTML = `<i class="fas fa-upload me-1"></i>Upload ${validFiles} File${validFiles > 1 ? 's' : ''}`;
    }
}

// Enhanced STP modal with debug info
function showSTPFileSelectionModal(accountId, month, monthData) {
    console.log('=== SHOWING STP MODAL ===');
    console.log('Modal data:', monthData);
    
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
                        
                        <!-- DEBUG INFO -->
                        <div class="alert alert-info small mb-3">
                            <strong>Debug:</strong> Icon HTML: <code>${monthData.iconHTML || 'N/A'}</code><br>
                            Excel: ${monthData.hasExcel ? '✓' : '✗'} | PDF: ${monthData.hasPdf ? '✓' : '✗'}
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
    
    // Remove existing modal if present
    var existingModal = document.getElementById('stpFileSelectionModal');
    if (existingModal) {
        existingModal.remove();
    }
    
    // Add modal to body
    document.body.insertAdjacentHTML('beforeend', modalHtml);
    
    // Show modal
    var modalElement = document.getElementById('stpFileSelectionModal');
    var modal = new bootstrap.Modal(modalElement);
    
    console.log('About to show modal...');
    modal.show();
    
    // Clean up after modal is hidden
    modalElement.addEventListener('hidden.bs.modal', function() {
        console.log('Modal hidden, cleaning up...');
        this.remove();
    });
    
    console.log('Modal should now be visible');
}

// Legacy function - keeping for compatibility but simplified
function showFileSelectionModal(accountId, month, monthData) {
    // This is the old function - redirect to new STP modal
    showSTPFileSelectionModal(accountId, month, {
        hasExcel: monthData.xlsx && monthData.xlsx !== null,
        hasPdf: monthData.pdf && monthData.pdf !== null
    });
}

// Helper function to close modal
function closeModal(modalId) {
    var modal = bootstrap.Modal.getInstance(document.getElementById(modalId));
    if (modal) {
        modal.hide();
    }
}

// Debug version of downloadFileFromModal
function downloadFileFromModal(accountId, month, fileType) {
    console.log('=== MODAL DOWNLOAD SELECTED ===');
    console.log('User selected:', { accountId, month, fileType });
    
    // Close the modal first
    var modal = bootstrap.Modal.getInstance(document.getElementById('stpFileSelectionModal'));
    if (modal) {
        console.log('Closing modal...');
        modal.hide();
    }
    
    // Start the download
    downloadFile(accountId, month, fileType);
}

// Debug version of downloadFile
function downloadFile(accountId, month, fileType) {
    console.log('=== STARTING DOWNLOAD ===');
    console.log('Download parameters:', { accountId, month, fileType });
    
    var year = window.StatementsApp.currentYear;
    var monthPadded = month.toString().padStart(2, '0');
    var downloadUrl = `/statements/download/${accountId}/${month}/${fileType}?year=${year}`;
    
    console.log('Download URL constructed:', downloadUrl);
    
    // Show loading alert
    window.StatementsUI.showAlert('info', `Preparing ${fileType.toUpperCase()} download...`);
    
    // Create a temporary link for download
    var link = document.createElement('a');
    link.href = downloadUrl;
    link.download = `${accountId}_${year}_${monthPadded}.${fileType}`;
    link.style.display = 'none';
    
    console.log('Created download link:', {
        href: link.href,
        download: link.download
    });
    
    // Add event listener for download feedback
    link.addEventListener('click', function() {
        console.log('Download link clicked');
        setTimeout(function() {
            window.StatementsUI.showAlert('success', 
                `${fileType.toUpperCase()} file download started: ${accountId}_${year}_${monthPadded}.${fileType}`
            );
        }, 500);
    });
    
    // Trigger download
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    
    console.log('Download triggered');
}

function showSuccessModal(accountId, accountData) {
    var fileCount = accountData.total_files || 0;
    var transactionCount = accountData.total_transactions || 0;
    
    // Create modal HTML
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
    
    // Remove existing modal if present
    var existingModal = document.getElementById('successModal');
    if (existingModal) {
        existingModal.remove();
    }
    
    // Add modal to body
    document.body.insertAdjacentHTML('beforeend', modalHtml);
    
    // Show modal
    var modal = new bootstrap.Modal(document.getElementById('successModal'));
    modal.show();
    
    // Clean up after modal is hidden
    document.getElementById('successModal').addEventListener('hidden.bs.modal', function() {
        this.remove();
    });
}

// Show modal when no additional files are available
function showNoAdditionalFilesModal(accountId) {
    // Create modal HTML
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
    
    // Remove existing modal if present
    var existingModal = document.getElementById('noFilesModal');
    if (existingModal) {
        existingModal.remove();
    }
    
    // Add modal to body
    document.body.insertAdjacentHTML('beforeend', modalHtml);
    
    // Show modal
    var modal = new bootstrap.Modal(document.getElementById('noFilesModal'));
    modal.show();
    
    // Clean up after modal is hidden
    document.getElementById('noFilesModal').addEventListener('hidden.bs.modal', function() {
        this.remove();
    });
}

// Year selector change handler
function handleYearChange(newYear) {
    var oldYear = window.StatementsApp.currentYear;
    
    if (oldYear === parseInt(newYear)) return; // No change needed
    
    console.log('Client-side year change:', oldYear, '->', newYear);
    
    // Show loading state
    showYearTransition(newYear);
    
    // Fetch new year data
    fetch('/api/statements/ui-data/' + newYear)
        .then(function(response) {
            if (!response.ok) throw new Error('Failed to load year data');
            return response.json();
        })
        .then(function(data) {
            if (data.success) {
                // Update application state
                window.StatementsApp.currentYear = parseInt(newYear);
                
                // Clear current UI
                clearAllAccountUI();
                
                // Render new year data
                displayUIData(data.ui_data);
                
                // Update URL without page reload
                var newUrl = '/statements/' + newYear;
                history.pushState({year: parseInt(newYear)}, '', newUrl);
                
                hideYearTransition();
            } else {
                throw new Error(data.error || 'Failed to load year data');
            }
        })
        .catch(function(error) {
            console.error('Year change failed:', error);
            window.StatementsUI.showAlert('danger', 'Failed to load year: ' + error.message);
            
            // Reset year selector
            var yearSelector = document.getElementById('yearSelector');
            if (yearSelector) {
                yearSelector.value = oldYear;
            }
            
            hideYearTransition();
        });
}

function showYearTransition(newYear) {
    // Add loading overlay or disable UI during transition
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
    // Reset all account buttons and icons
    window.StatementsApp.accountIds.forEach(function(accountId) {
        // Reset load button
        var loadBtn = document.getElementById('load-btn-' + accountId);
        if (loadBtn) {
            loadBtn.innerHTML = '<i class="fas fa-sync-alt"></i>';
            loadBtn.className = 'btn btn-primary btn-sm';
        }
        
        // Hide parse button
        var parseBtn = document.getElementById('parse-btn-' + accountId);
        if (parseBtn) {
            parseBtn.style.display = 'none';
        }
        
        // Clear all month cells
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
    // Same as existing function - renders account data
    for (var accountId in uiData) {
        var accountData = uiData[accountId];
        
        // Update load button
        var loadBtn = document.getElementById('load-btn-' + accountId);
        if (loadBtn) {
            loadBtn.innerHTML = '<i class="fas fa-check-circle"></i>';
            loadBtn.className = 'btn btn-success btn-sm';
        }
        
        // Show parse button
        var parseBtn = document.getElementById('parse-btn-' + accountId);
        if (parseBtn) {
            parseBtn.style.display = 'inline-block';
        }
        
        // Display month files
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

// Debug functions for troubleshooting
function testCell(accountId, month) {
    console.log(`\n=== TESTING CELL ${accountId}-${month} ===`);
    
    var fileIcon = document.getElementById('file-icon-' + accountId + '-' + month);
    var cell = document.querySelector('[data-account-id="' + accountId + '"][data-month="' + month + '"]');
    var accountRow = document.querySelector('[data-account-id="' + accountId + '"]');
    
    console.log('Elements:');
    console.log('  File Icon Element:', fileIcon);
    console.log('  Cell Element:', cell);
    console.log('  Account Row:', accountRow);
    
    if (fileIcon) {
        console.log('File Icon Details:');
        console.log('  ID:', fileIcon.id);
        console.log('  innerHTML:', JSON.stringify(fileIcon.innerHTML));
        console.log('  textContent:', JSON.stringify(fileIcon.textContent));
        console.log('  outerHTML:', fileIcon.outerHTML);
    }
    
    if (cell) {
        console.log('Cell Details:');
        console.log('  className:', cell.className);
        console.log('  classList:', Array.from(cell.classList));
        console.log('  data-account-id:', cell.getAttribute('data-account-id'));
        console.log('  data-month:', cell.getAttribute('data-month'));
        console.log('  onclick:', cell.getAttribute('onclick'));
    }
    
    if (accountRow) {
        console.log('Account Row Details:');
        console.log('  data-account-type:', accountRow.getAttribute('data-account-type'));
    }
}

function inspectCurrentPageData() {
    console.log('=== PAGE INSPECTION ===');
    
    // Check what accounts exist on the page
    var accountRows = document.querySelectorAll('[data-account-id]');
    console.log('Found', accountRows.length, 'account rows');
    
    accountRows.forEach(function(row, index) {
        var accountId = row.getAttribute('data-account-id');
        var accountType = row.getAttribute('data-account-type');
        
        console.log(`\nAccount ${index + 1}: ${accountId} (${accountType})`);
        
        // Check each month for this account
        for (var month = 1; month <= 12; month++) {
            var fileIcon = document.getElementById('file-icon-' + accountId + '-' + month);
            var cell = document.querySelector('[data-account-id="' + accountId + '"][data-month="' + month + '"]');
            
            if (fileIcon && cell) {
                var iconHTML = fileIcon.innerHTML.trim();
                var cellClass = cell.className;
                
                if (iconHTML || !cellClass.includes('no-file')) {
                    console.log(`  Month ${month}:`);
                    console.log(`    Icon HTML: "${iconHTML}"`);
                    console.log(`    Cell Class: "${cellClass}"`);
                    console.log(`    Has Excel: ${iconHTML.includes('fa-file-excel')}`);
                    console.log(`    Has PDF: ${iconHTML.includes('fa-file-pdf')}`);
                }
            }
        }
    });
}

// Add this function to your main.js file for debugging uploads

function debugUpload() {
    console.log('=== STARTING DEBUG UPLOAD ===');
    
    // Create a file input for testing
    var debugInput = document.createElement('input');
    debugInput.type = 'file';
    debugInput.accept = '.pdf,.xlsx,.xls';
    debugInput.multiple = true;
    
    debugInput.onchange = function() {
        if (debugInput.files.length === 0) {
            console.log('No files selected for debug');
            return;
        }
        
        console.log('Files selected for debug:', debugInput.files.length);
        
        // Create FormData
        var formData = new FormData();
        Array.from(debugInput.files).forEach(function(file) {
            formData.append('files', file);
            console.log('Added file to debug:', file.name, file.size, 'bytes');
        });
        
        // Show progress
        window.StatementsUI.showAlert('info', 'Running upload debug...');
        
        // Call debug endpoint
        fetch('/api/statements/debug-upload', {
            method: 'POST',
            body: formData
        })
        .then(function(response) {
            return response.json();
        })
        .then(function(data) {
            console.log('=== DEBUG UPLOAD RESULTS ===');
            console.log(data);
            
            if (data.success && data.debug_info) {
                data.debug_info.forEach(function(fileDebug, index) {
                    console.log(`\n--- FILE ${index + 1}: ${fileDebug.filename} ---`);
                    
                    console.log('Steps completed:');
                    fileDebug.steps.forEach(function(step, stepIndex) {
                        console.log(`  ${stepIndex + 1}. ${step}`);
                    });
                    
                    if (fileDebug.errors.length > 0) {
                        console.log('Errors encountered:');
                        fileDebug.errors.forEach(function(error, errorIndex) {
                            console.log(`  ERROR ${errorIndex + 1}: ${error}`);
                        });
                    }
                    
                    if (fileDebug.file_info) {
                        console.log('File info:', fileDebug.file_info);
                    }
                    
                    if (fileDebug.upload_response) {
                        console.log('Upload response:', fileDebug.upload_response);
                        
                        if (fileDebug.upload_response.success) {
                            console.log('✅ UPLOAD SUCCESSFUL');
                            if (fileDebug.upload_details) {
                                console.log('Upload details:', fileDebug.upload_details);
                            }
                        } else {
                            console.log('❌ UPLOAD FAILED');
                            console.log('Response text:', fileDebug.upload_response.response_text);
                        }
                    }
                    
                    if (fileDebug.sharepoint_access_test) {
                        console.log('SharePoint access test:', fileDebug.sharepoint_access_test);
                    }
                    
                    if (fileDebug.upload_url) {
                        console.log('Upload URL used:', fileDebug.upload_url);
                    }
                });
                
                // Show summary alert
                var totalFiles = data.debug_info.length;
                var successfulUploads = data.debug_info.filter(f => 
                    f.upload_response && f.upload_response.success
                ).length;
                var failedUploads = totalFiles - successfulUploads;
                
                if (successfulUploads > 0) {
                    window.StatementsUI.showAlert('success', 
                        `Debug complete: ${successfulUploads}/${totalFiles} uploads successful. Check console for details.`
                    );
                } else {
                    window.StatementsUI.showAlert('danger', 
                        `Debug complete: All uploads failed. Check console for error details.`
                    );
                }
            } else {
                console.log('Debug failed:', data.error);
                window.StatementsUI.showAlert('danger', 'Debug failed: ' + data.error);
            }
        })
        .catch(function(error) {
            console.error('Debug upload error:', error);
            window.StatementsUI.showAlert('danger', 'Debug error: ' + error.message);
        });
    };
    
    // Trigger file selection
    debugInput.click();
}

// Also add this enhanced version to your API module
window.StatementsAPI.uploadFiles = function(formData) {
    return new Promise(function(resolve, reject) {
        fetch('/api/statements/upload', {
            method: 'POST',
            body: formData
        })
        .then(function(response) {
            if (response.status === 401 || response.status === 403) {
                window.location.href = '/login';
                return;
            }
            if (!response.ok) {
                throw new Error('HTTP ' + response.status + ': ' + response.statusText);
            }
            return response.json();
        })
        .then(function(data) {
            console.log('=== UPLOAD API RESPONSE ===');
            console.log('Success:', data.success);
            console.log('Total files:', data.total_files);
            console.log('Successful uploads:', data.successful_uploads);
            console.log('Failed uploads:', data.failed_uploads);
            
            if (data.results) {
                console.log('Individual results:');
                data.results.forEach(function(result, index) {
                    console.log(`  ${index + 1}. ${result.filename}: ${result.success ? 'SUCCESS' : 'FAILED'}`);
                    if (!result.success) {
                        console.log(`     Error: ${result.error}`);
                    } else {
                        console.log(`     Account: ${result.account_name || result.account_type}`);
                    }
                });
            }
            
            resolve(data);
        })
        .catch(function(error) {
            console.error('Upload API error:', error);
            reject(error);
        });
    });
};

// Add a button to easily run debug from console
console.log('🔧 UPLOAD DEBUG READY');
console.log('Run debugUpload() to test file upload with detailed logging');
console.log('This will help identify exactly where the upload is failing');

function refreshCalendarForUploadedFiles(uploadResults) {
    if (!uploadResults || uploadResults.length === 0) {
        return;
    }
    
    // Get accounts that had successful uploads
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
        console.log('No accounts to refresh');
        return;
    }
    
    console.log('Refreshing calendar for accounts:', Array.from(accountsToRefresh));
    
    // Refresh each affected account
    var refreshPromises = [];
    
    accountsToRefresh.forEach(function(accountId) {
        var promise = refreshSingleAccountCalendar(accountId);
        refreshPromises.push(promise);
    });
    
    // Wait for all refreshes to complete
    Promise.allSettled(refreshPromises).then(function(results) {
        var successful = results.filter(r => r.status === 'fulfilled').length;
        var failed = results.filter(r => r.status === 'rejected').length;
        
        if (successful > 0 && window.StatementsUI && window.StatementsUI.showAlert) {
            window.StatementsUI.showAlert('success', 
                `Calendar updated! ${successful} account${successful > 1 ? 's' : ''} refreshed.`
            );
        }
        
        if (failed > 0) {
            console.warn(`${failed} account refreshes failed`);
        }
    });
}

function mapAccountNameToId(accountName) {
    console.log('=== ACCOUNT NAME MAPPING DEBUG ===');
    console.log('Trying to map account name:', JSON.stringify(accountName));
    
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
    
    var result = accountMappings[accountName] || null;
    console.log('Mapping result:', result);
    
    if (!result) {
        console.log('Available mappings:', Object.keys(accountMappings));
    }
    
    return result;
}

function refreshSingleAccountCalendar(accountId) {
    return new Promise(function(resolve, reject) {
        // Check if StatementsAPI exists
        if (!window.StatementsAPI || !window.StatementsAPI.loadAccount) {
            console.warn('StatementsAPI not available, skipping refresh');
            resolve(accountId);
            return;
        }
        
        console.log(`Refreshing calendar for ${accountId}...`);
        
        window.StatementsAPI.loadAccount(accountId)
            .then(function(accountData) {
                console.log(`Received fresh data for ${accountId}:`, accountData);
                
                // Update the UI with fresh data
                if (window.StatementsUI && window.StatementsUI.updateAccountDisplay) {
                    window.StatementsUI.updateAccountDisplay(accountId, accountData);
                }
                
                // Update load button to show account is loaded
                if (window.StatementsUI && window.StatementsUI.updateLoadButton) {
                    window.StatementsUI.updateLoadButton(accountId, true);
                }
                
                console.log(`Calendar updated for ${accountId}`);
                resolve(accountId);
            })
            .catch(function(error) {
                console.error(`Failed to refresh ${accountId}:`, error);
                reject(error);
            });
    });
}

// Enhanced loadAccountData function with upload awareness
function loadAccountData(accountId) {
    var loadBtn = document.getElementById('load-btn-' + accountId);
    
    if (!loadBtn) {
        console.error('Load button not found for account:', accountId);
        return;
    }
    
    // Show loading state
    loadBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';
    loadBtn.disabled = true;
    
    window.StatementsUI.showAlert('info', 'Loading account data...');
    
    window.StatementsAPI.loadAccount(accountId)
        .then(function(accountData) {
            console.log('Account data loaded:', accountData);
            
            // Update UI
            window.StatementsUI.updateAccountDisplay(accountId, accountData);
            
            // Update load button
            window.StatementsUI.updateLoadButton(accountId, true);
            loadBtn.disabled = false;
            
            // Show parse button
            var parseBtn = document.getElementById('parse-btn-' + accountId);
            if (parseBtn) {
                parseBtn.style.display = 'inline-block';
            }
            
            // Show success message
            var fileCount = accountData.total_files || 0;
            var transactionCount = accountData.total_transactions || 0;
            
            window.StatementsUI.showAlert('success', 
                `${accountId.toUpperCase()}: ${fileCount} files loaded, ${transactionCount.toLocaleString()} transactions`
            );
            
            // Show success modal if significant data
            if (fileCount > 0) {
                showSuccessModal(accountId, accountData);
            } else {
                showNoAdditionalFilesModal(accountId);
            }
        })
        .catch(function(error) {
            console.error('Failed to load account data:', error);
            
            // Reset button
            loadBtn.innerHTML = '<i class="fas fa-download"></i>';
            loadBtn.disabled = false;
            
            window.StatementsUI.showAlert('danger', 
                'Failed to load account data: ' + error.message
            );
        });
}

// Add automatic refresh on page load if there were recent uploads
document.addEventListener('DOMContentLoaded', function() {
    // Check if there were recent uploads (you could use sessionStorage for this)
    var recentUploads = sessionStorage.getItem('recentUploads');
    
    if (recentUploads) {
        try {
            var uploadData = JSON.parse(recentUploads);
            if (uploadData.timestamp && Date.now() - uploadData.timestamp < 60000) { // Within 1 minute
                console.log('Detected recent uploads, refreshing affected accounts...');
                refreshCalendarForUploadedFiles(uploadData.results);
            }
        } catch (e) {
            console.warn('Could not parse recent upload data:', e);
        }
        
        // Clear the flag
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
            console.warn('Could not store upload results:', e);
        }
    }
}

// Updated parseAccountRow function - replace existing one
function parseAccountRow(accountId) {
    console.log('=== STARTING PARSE OPERATION ===');
    console.log('Account ID:', accountId);
    
    // Get account name for display
    var accountConfig = window.StatementsApp.accountIds.find(id => id === accountId);
    var accountName = accountId.toUpperCase().replace('_', ' ');
    
    // Show parse modal
    showParseModal(accountId, accountName);
    
    // Start parse operation
    startParseOperation(accountId, accountName);
}

// Show parse progress modal (copy of upload modal pattern)
function showParseModal(accountId, accountName) {
    console.log('Creating parse modal with upload modal styling...');
    
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
                        
                        <!-- Parse Progress -->
                        <div id="parseProgress" style="display: block;">
                            <h6 class="text-warning mb-2">Parse Progress:</h6>
                            <div class="progress mb-2">
                                <div id="parseProgressBar" class="progress-bar bg-warning" role="progressbar" style="width: 0%"></div>
                            </div>
                            <small id="parseStatus" class="text-muted">Initializing parse operation...</small>
                            
                            <!-- File Progress Details -->
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
                                
                                <!-- Current File -->
                                <div id="currentFileSection" class="mt-3" style="display: none;">
                                    <div class="alert alert-info small mb-0">
                                        <strong>Processing:</strong> <span id="currentFileName">-</span>
                                    </div>
                                </div>
                            </div>
                        </div>
                        
                        <!-- Parse Results -->
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
    
    // Remove existing modal if present
    var existingModal = document.getElementById('parseModal');
    if (existingModal) {
        existingModal.remove();
    }
    
    // Add modal to body
    document.body.insertAdjacentHTML('beforeend', modalHtml);
    
    // Show modal
    var modal = new bootstrap.Modal(document.getElementById('parseModal'));
    modal.show();
    
    // Clean up after modal is hidden
    document.getElementById('parseModal').addEventListener('hidden.bs.modal', function() {
        console.log('Parse modal closed, cleaning up...');
        this.remove();
    });
    
    console.log('Parse modal created and shown');
}

// Start parse operation and track progress
function startParseOperation(accountId, accountName) {
    console.log('=== STARTING PARSE API CALL ===');
    
    var parseStatus = document.getElementById('parseStatus');
    var parseProgressBar = document.getElementById('parseProgressBar');
    var parseCloseBtn = document.getElementById('parseCloseBtn');
    
    // Update initial status
    if (parseStatus) {
        parseStatus.textContent = 'Starting parse operation...';
    }
    
    if (parseProgressBar) {
        parseProgressBar.style.width = '10%';
    }
    
    if (parseCloseBtn) {
        parseCloseBtn.disabled = true;
    }
    
    // Start parse via API
    window.StatementsAPI.parseAccount(accountId)
        .then(function(response) {
            console.log('Parse started successfully:', response);
            
            if (parseStatus) {
                parseStatus.textContent = 'Parse operation started, tracking progress...';
            }
            
            if (parseProgressBar) {
                parseProgressBar.style.width = '20%';
            }
            
            // Start progress polling
            startParseProgressPolling(response.session_id, accountId, accountName);
        })
        .catch(function(error) {
            console.error('Failed to start parse:', error);
            
            if (parseStatus) {
                parseStatus.textContent = 'Failed to start parse: ' + error.message;
            }
            
            if (parseProgressBar) {
                parseProgressBar.style.width = '100%';
                parseProgressBar.className = 'progress-bar bg-danger';
            }
            
            // Show error results
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

// Poll parse progress (copy of upload progress pattern)
function startParseProgressPolling(sessionId, accountId, accountName) {
    console.log('Starting progress polling for session:', sessionId);
    
    var progressInterval = setInterval(function() {
        window.StatementsAPI.getParseProgress(sessionId)
            .then(function(progress) {
                console.log('Progress update:', progress);
                updateParseProgress(progress);
                
                // Check if completed
                if (progress.status === 'completed' || progress.status === 'error') {
                    clearInterval(progressInterval);
                    handleParseCompletion(progress, accountId);
                }
            })
            .catch(function(error) {
                console.error('Progress polling error:', error);
                clearInterval(progressInterval);
                
                var parseStatus = document.getElementById('parseStatus');
                if (parseStatus) {
                    parseStatus.textContent = 'Progress tracking failed: ' + error.message;
                }
            });
    }, 2000); // Poll every 2 seconds
}

// Update parse progress display
function updateParseProgress(progress) {
    var parseStatus = document.getElementById('parseStatus');
    var parseProgressBar = document.getElementById('parseProgressBar');
    var parseDetails = document.getElementById('parseDetails');
    var filesProcessedCount = document.getElementById('filesProcessedCount');
    var totalFilesCount = document.getElementById('totalFilesCount');
    var transactionsCount = document.getElementById('transactionsCount');
    var currentFileSection = document.getElementById('currentFileSection');
    var currentFileName = document.getElementById('currentFileName');
    
    // Update progress bar
    if (parseProgressBar) {
        parseProgressBar.style.width = (progress.progress_percentage || 0) + '%';
        
        // Color coding
        if (progress.status === 'error') {
            parseProgressBar.className = 'progress-bar bg-danger';
        } else if (progress.progress_percentage >= 100) {
            parseProgressBar.className = 'progress-bar bg-success';
        } else {
            parseProgressBar.className = 'progress-bar bg-warning';
        }
    }
    
    // Update status text
    if (parseStatus) {
        var statusText = progress.details || progress.status || 'Processing...';
        parseStatus.textContent = statusText;
    }
    
    // Show/update details section
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
    
    // Show current file being processed
    if (currentFileSection && currentFileName && progress.current_file) {
        currentFileSection.style.display = 'block';
        currentFileName.textContent = progress.current_file;
    } else if (currentFileSection && !progress.current_file) {
        currentFileSection.style.display = 'none';
    }
}

function handleParseCompletion(progress, accountId) {
    console.log('=== PARSE COMPLETION DATA DEBUG ===');
    console.log('Full progress object:', progress);
    console.log('progress.result:', progress.result);
    console.log('progress.status:', progress.status);
    console.log('Type of progress:', typeof progress);
    console.log('Progress keys:', Object.keys(progress));
    
    if (progress.result) {
        console.log('Result object exists:');
        console.log('  result.success:', progress.result.success);
        console.log('  result.files_processed:', progress.result.files_processed);
        console.log('  result.files_skipped:', progress.result.files_skipped);
        console.log('  result.message:', progress.result.message);
    }
    console.log('=== END DEBUG ===');
    
    var parseStatus = document.getElementById('parseStatus');
    var parseCloseBtn = document.getElementById('parseCloseBtn');
    
    if (progress.status === 'completed') {
        if (parseStatus) {
            parseStatus.textContent = 'Parse completed successfully!';
        }
        
        // FIX: Transform progress object into the format showParseResults expects
        var resultData = {
            success: true,  // CRITICAL: Parse completion means success
            files_processed: progress.files_processed || 0,
            files_skipped: progress.files_skipped || 0,
            transactions_added: progress.transactions_added || 0,
            total_files: progress.total_files || 0,
            message: progress.details || 'Parse completed successfully',
            errors: progress.errors || []
        };
        
        console.log('=== TRANSFORMED RESULT DATA ===');
        console.log('Passing to showParseResults:', resultData);
        console.log('Success field set to:', resultData.success);
        console.log('Files processed:', resultData.files_processed);
        console.log('Files skipped:', resultData.files_skipped);
        
        // Show results
        showParseResults(resultData);
        
        // Refresh account display
        refreshAccountAfterParse(accountId);
        
    } else if (progress.status === 'error') {
        if (parseStatus) {
            parseStatus.textContent = 'Parse failed: ' + (progress.error || 'Unknown error');
        }
        
        // Show error results
        showParseResults({
            success: false,
            error: progress.error || 'Parse operation failed',
            account_id: accountId,
            files_processed: progress.files_processed || 0,
            transactions_added: progress.transactions_added || 0
        });
    }
    
    // Re-enable close button
    if (parseCloseBtn) {
        parseCloseBtn.disabled = false;
        parseCloseBtn.innerHTML = '<i class="fas fa-check me-1"></i>Close';
    }
}

// Show parse results (FIXED VERSION)
function showParseResults(result) {
    var parseResults = document.getElementById('parseResults');
    var parseResultsList = document.getElementById('parseResultsList');
    
    if (!parseResults || !parseResultsList) {
        console.warn('Parse results elements not found');
        return;
    }
    
    // FIXED: Handle "all files current" case properly
    var isSuccess = result.success;
    var filesProcessed = result.files_processed || 0;
    var filesSkipped = result.files_skipped || 0;
    var transactionsAdded = result.transactions_added || 0;
    var totalFiles = result.total_files || filesProcessed + filesSkipped;
    
    // Determine appropriate message based on results
    var messageText = '';
    var isAllCurrent = isSuccess && filesProcessed === 0 && filesSkipped > 0;
    
    if (isAllCurrent) {
        // All files are already current - this is a SUCCESS case
        messageText = `All ${filesSkipped} files are already up to date. No parsing needed.`;
    } else if (isSuccess && filesProcessed > 0) {
        // Some files were processed
        messageText = `${filesProcessed} files processed successfully. ${transactionsAdded} transactions added to database.`;
        if (filesSkipped > 0) {
            messageText += ` ${filesSkipped} files were already current.`;
        }
    } else if (!isSuccess) {
        // Actual failure
        messageText = `Parse failed. ${filesProcessed} files processed. ${transactionsAdded} transactions added.`;
    } else {
        // Fallback
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
    
    // Add summary statistics if successful
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
        
        // Add helpful message for all-current case
        if (isAllCurrent) {
            summaryHtml += `
                <div class="mt-2 alert alert-info small">
                    <i class="fas fa-info-circle me-1"></i>
                    All files have been parsed previously and are up to date. This is the expected result for accounts that have already been processed.
                </div>
            `;
        }
    }
    
    // Add error details if any
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

// Add this to refreshAccountAfterParse function, right after the console.log line:
function refreshAccountAfterParse(accountId) {
    console.log('=== PARSE COMPLETION DEBUG ===');
    console.log('About to refresh account:', accountId);

    // Check current state of month cells BEFORE refresh
    for (var month = 1; month <= 12; month++) {
        var countElement = document.getElementById('count-' + accountId + '-' + month);
        if (countElement && countElement.textContent !== '-') {
            console.log(`Month ${month} count BEFORE refresh:`, countElement.textContent);
        }
    }
    
    console.log('=== PARSE COMPLETION - FORCING INVENTORY REFRESH ===');
    
    // Show initial message
    if (window.StatementsUI && window.StatementsUI.showAlert) {
        window.StatementsUI.showAlert('info', 'Parse completed! Refreshing inventory...');
    }
    
    // FORCE inventory refresh to ensure new parse data is used
    fetch('/api/statements/refresh-inventory/' + accountId, {
        method: 'POST'
    })
    .then(function(response) {
        return response.json();
    })
    .then(function(refreshResult) {
        console.log('Inventory refresh initiated:', refreshResult);
        
        // Wait a moment for inventory to process, then load fresh data
        setTimeout(function() {
            window.StatementsAPI.loadAccount(accountId)
                .then(function(accountData) {
                    console.log('=== ACCOUNT DATA RECEIVED ===');
                    console.log('Account data refreshed after parse:', accountData);
                    
                    // Check if the data itself has duplication
                    if (accountData.months) {
                        console.log('=== CHECKING MONTH DATA ===');
                        for (var monthKey in accountData.months) {
                            var monthData = accountData.months[monthKey];
                            if (monthData.xlsx && monthData.pdf) {
                                console.log(`Month ${monthKey}:`);
                                console.log('  XLSX transactions:', monthData.xlsx.transaction_count);
                                console.log('  PDF transactions:', monthData.pdf.transaction_count);
                            }
                        }
                    }
                    
                    // Update UI display
                    if (window.StatementsUI && window.StatementsUI.updateAccountDisplay) {
                        window.StatementsUI.updateAccountDisplay(accountId, accountData);
                    }
                    
                    // Check counts AFTER UI update
                    setTimeout(function() {
                        console.log('=== AFTER UI UPDATE ===');
                        for (var month = 1; month <= 12; month++) {
                            var countElement = document.getElementById('count-' + accountId + '-' + month);
                            if (countElement && countElement.textContent !== '-') {
                                console.log(`Month ${month} count AFTER refresh:`, countElement.textContent);
                            }
                        }
                    }, 500);
                    
                    if (window.StatementsUI && window.StatementsUI.showAlert) {
                        window.StatementsUI.showAlert('success', 'Account data refreshed successfully!');
                    }
                })
                .catch(function(error) {
                    console.error('Failed to refresh account after parse:', error);
                    if (window.StatementsUI && window.StatementsUI.showAlert) {
                        window.StatementsUI.showAlert('danger', 'Failed to refresh account data');
                    }
                });
        }, 2000); // Wait 2 seconds for inventory refresh to complete
    })
    .catch(function(error) {
        console.error('Failed to refresh inventory:', error);
        if (window.StatementsUI && window.StatementsUI.showAlert) {
            window.StatementsUI.showAlert('warning', 'Inventory refresh failed, loading cached data...');
        }
        
        // Fallback: try to load without inventory refresh
        window.StatementsAPI.loadAccount(accountId)
            .then(function(accountData) {
                window.StatementsUI.updateAccountDisplay(accountId, accountData);
            });
    });
}


// Initialize on DOM ready
document.addEventListener('DOMContentLoaded', function() {
    // Initialize app with template year
    var templateYear = document.querySelector('meta[name="current-year"]');
    var currentYear = templateYear ? templateYear.content : '2025';
    
    window.StatementsApp.init(currentYear);
    
    // Setup year selector
    var yearSelector = document.getElementById('yearSelector');
    if (yearSelector) {
        yearSelector.value = window.StatementsApp.currentYear.toString();
        yearSelector.addEventListener('change', function(e) {
            handleYearChange(e.target.value);
        });
    }
    
    // Load debug functions
    console.log('DEBUG FUNCTIONS LOADED');
    console.log('Run inspectCurrentPageData() to see all page data');
    console.log('Run testCell("accountId", monthNumber) to test specific cells');
    console.log('StatementsApp state:', window.StatementsApp);
    
    console.log('Upload functionality ready - FIXED VERSION!');
});

// Handle browser back/forward buttons
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
    // Set initial state for current year
    var currentYear = window.StatementsApp.currentYear;
    history.replaceState({year: currentYear}, '', '/statements/' + currentYear);
});