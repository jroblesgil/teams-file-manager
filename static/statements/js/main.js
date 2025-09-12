// Complete main.js file with upload functionality
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
        displaySelectedFiles(files);
    }
}

function handleFileSelection() {
    var fileInput = document.getElementById('fileInput');
    if (fileInput.files.length > 0) {
        console.log('Files selected via browse:', fileInput.files.length);
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
    console.log('=== STARTING UPLOAD PROCESS ===');
    
    var fileInput = document.getElementById('fileInput');
    var uploadProgress = document.getElementById('uploadProgress');
    var uploadProgressBar = document.getElementById('uploadProgressBar');
    var uploadStatus = document.getElementById('uploadStatus');
    var uploadBtn = document.getElementById('uploadBtn');
    var cancelBtn = document.getElementById('cancelBtn');
    var selectedFilesSection = document.getElementById('selectedFilesSection');
    
    if (!fileInput.files.length) {
        window.StatementsUI.showAlert('warning', 'No files selected');
        return;
    }
    
    // Show progress section
    uploadProgress.style.display = 'block';
    selectedFilesSection.style.display = 'none';
    
    // Disable buttons
    uploadBtn.disabled = true;
    uploadBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i>Uploading...';
    cancelBtn.disabled = true;
    
    // Update progress
    uploadProgressBar.style.width = '10%';
    uploadStatus.textContent = 'Preparing files for upload...';
    
    // Create FormData
    var formData = new FormData();
    Array.from(fileInput.files).forEach(function(file) {
        formData.append('files', file);
    });
    
    uploadStatus.textContent = 'Uploading files to server...';
    uploadProgressBar.style.width = '50%';
    
    // Upload via API
    window.StatementsAPI.uploadFiles(formData)
        .then(function(data) {
            console.log('Upload completed:', data);
            
            uploadProgressBar.style.width = '100%';
            uploadProgressBar.classList.add('bg-success');
            uploadStatus.textContent = 'Upload completed successfully!';
            
            // Show results
            showUploadResults(data);
            
            // Re-enable cancel button
            cancelBtn.disabled = false;
            cancelBtn.innerHTML = '<i class="fas fa-check me-1"></i>Close';
            
            // Suggest page refresh if uploads were successful
            if (data.success && data.successful_uploads > 0) {
                setTimeout(function() {
                    if (confirm('Files uploaded successfully! Refresh the page to see new files?')) {
                        window.location.reload();
                    }
                }, 2000);
            }
        })
        .catch(function(error) {
            console.error('Upload failed:', error);
            
            uploadProgressBar.classList.add('bg-danger');
            uploadStatus.textContent = 'Upload failed: ' + error.message;
            
            showUploadResults({
                success: false,
                error: error.message,
                total_files: fileInput.files.length,
                successful_uploads: 0,
                failed_uploads: fileInput.files.length
            });
            
            // Re-enable buttons
            uploadBtn.disabled = false;
            uploadBtn.innerHTML = '<i class="fas fa-upload me-1"></i>Retry Upload';
            cancelBtn.disabled = false;
        });
}

function showUploadResults(data) {
    var uploadResults = document.getElementById('uploadResults');
    var uploadResultsList = document.getElementById('uploadResultsList');
    
    if (!uploadResults || !uploadResultsList) return;
    
    var alertClass = data.success ? 'alert-success' : 'alert-danger';
    var iconClass = data.success ? 'fa-check-circle' : 'fa-exclamation-triangle';
    
    var summaryHtml = `
        <div class="alert ${alertClass}" role="alert">
            <h6 class="alert-heading">
                <i class="fas ${iconClass} me-2"></i>
                Upload ${data.success ? 'Completed' : 'Failed'}
            </h6>
            <p class="mb-0">
                ${data.successful_uploads || 0} of ${data.total_files || 0} files uploaded successfully.
                ${data.failed_uploads > 0 ? ` ${data.failed_uploads} files failed.` : ''}
            </p>
        </div>
    `;
    
    // Add individual file results if available
    if (data.results && data.results.length > 0) {
        summaryHtml += '<div class="mt-2">';
        data.results.forEach(function(result) {
            var resultIcon = result.success ? 'fa-check-circle text-success' : 'fa-times-circle text-danger';
            var message = result.success ? 
                `Uploaded to ${result.account_name || result.account_type || 'account'}` : 
                `Failed: ${result.error || 'Unknown error'}`;
                
            summaryHtml += `
                <div class="border rounded p-2 mb-1 d-flex justify-content-between align-items-center">
                    <div>
                        <strong>${result.filename || 'Unknown file'}</strong>
                        <small class="text-muted d-block">${message}</small>
                    </div>
                    <i class="fas ${resultIcon}"></i>
                </div>
            `;
        });
        summaryHtml += '</div>';
    }
    
    uploadResultsList.innerHTML = summaryHtml;
    uploadResults.style.display = 'block';
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
    
    console.log('Upload functionality ready!');
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