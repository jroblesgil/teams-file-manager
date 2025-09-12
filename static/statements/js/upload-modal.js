// Upload Modal Component for Unified Statement Upload
window.UploadModal = {
    currentFiles: new Map(), // Store files with validation results
    
    // Show the upload modal
    show: function() {
        this.createModal();
        const modal = new bootstrap.Modal(document.getElementById('uploadModal'));
        modal.show();
        
        // Clean up on close
        document.getElementById('uploadModal').addEventListener('hidden.bs.modal', function() {
            this.remove();
        });
    },
    
    // Create modal HTML
    createModal: function() {
        // Remove existing modal if present
        const existingModal = document.getElementById('uploadModal');
        if (existingModal) {
            existingModal.remove();
        }
        
        const modalHtml = `
            <div class="modal fade" id="uploadModal" tabindex="-1" aria-hidden="true">
                <div class="modal-dialog modal-dialog-centered">
                    <div class="modal-content">
                        <div class="modal-header">
                            <h5 class="modal-title">
                                <i class="fas fa-cloud-upload-alt text-primary me-2"></i>
                                Upload to Teams
                            </h5>
                            <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                        </div>
                        <div class="modal-body">
                            <!-- Drop Zone -->
                            <div id="dropZone" class="upload-drop-zone text-center p-4 border border-2 border-dashed rounded">
                                <i class="fas fa-cloud-upload-alt text-muted mb-3" style="font-size: 3rem;"></i>
                                <p class="mb-2"><strong>Drag and drop files here</strong></p>
                                <p class="text-muted small mb-3">or</p>
                                <button type="button" class="btn btn-outline-primary" onclick="document.getElementById('fileInput').click()">
                                    <i class="fas fa-folder-open me-2"></i>Browse Files
                                </button>
                                <input type="file" id="fileInput" multiple accept=".pdf,.xlsx,.xls" style="display: none;">
                                <div class="mt-3">
                                    <small class="text-muted">
                                        Supported: STP Excel files (.xlsx) and BBVA PDF statements (.pdf)
                                    </small>
                                </div>
                            </div>
                            
                            <!-- File List -->
                            <div id="fileList" class="mt-3" style="display: none;">
                                <h6 class="mb-2">Selected Files:</h6>
                                <div id="fileItems"></div>
                            </div>
                        </div>
                        <div class="modal-footer">
                            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">
                                <i class="fas fa-times me-1"></i>Cancel
                            </button>
                            <button type="button" id="uploadBtn" class="btn btn-primary" disabled onclick="window.UploadModal.startUpload()">
                                <i class="fas fa-upload me-1"></i>Upload Files
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        `;
        
        document.body.insertAdjacentHTML('beforeend', modalHtml);
        this.setupEventListeners();
    },
    
    // Setup drag/drop and file input listeners
    setupEventListeners: function() {
        const dropZone = document.getElementById('dropZone');
        const fileInput = document.getElementById('fileInput');
        
        // Drag and drop events
        dropZone.addEventListener('dragover', function(e) {
            e.preventDefault();
            dropZone.classList.add('border-primary', 'bg-light');
        });
        
        dropZone.addEventListener('dragleave', function(e) {
            e.preventDefault();
            dropZone.classList.remove('border-primary', 'bg-light');
        });
        
        dropZone.addEventListener('drop', (e) => {
            e.preventDefault();
            dropZone.classList.remove('border-primary', 'bg-light');
            this.handleFiles(e.dataTransfer.files);
        });
        
        // File input change
        fileInput.addEventListener('change', (e) => {
            this.handleFiles(e.target.files);
        });
    },
    
    // Handle file selection
    handleFiles: function(files) {
        console.log('Files selected:', files.length);
        
        // Clear previous files
        this.currentFiles.clear();
        
        // Process each file
        Array.from(files).forEach(file => {
            this.addFile(file);
        });
        
        this.updateFileList();
    },
    
    // Add file and validate immediately
    addFile: function(file) {
        const fileId = Date.now() + '_' + Math.random().toString(36).substr(2, 9);
        
        // Store file with initial validation state
        this.currentFiles.set(fileId, {
            file: file,
            id: fileId,
            name: file.name,
            size: file.size,
            validationStatus: 'validating',
            validationResult: null
        });
        
        // Validate file immediately
        this.validateFile(fileId, file.name);
    },
    
    // Validate file using existing API
    validateFile: function(fileId, filename) {
        fetch('/api/statements/upload/validate', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ filename: filename })
        })
        .then(response => response.json())
        .then(data => {
            const fileData = this.currentFiles.get(fileId);
            if (fileData) {
                if (data.success && data.validation && data.validation.success) {
                    fileData.validationStatus = 'valid';
                    fileData.validationResult = data.validation.file_info;
                } else {
                    fileData.validationStatus = 'invalid';
                    fileData.validationResult = { error: data.validation?.error || 'Invalid file format' };
                }
                this.updateFileItem(fileId);
                this.updateUploadButton();
            }
        })
        .catch(error => {
            console.error('Validation error:', error);
            const fileData = this.currentFiles.get(fileId);
            if (fileData) {
                fileData.validationStatus = 'error';
                fileData.validationResult = { error: 'Validation failed' };
                this.updateFileItem(fileId);
                this.updateUploadButton();
            }
        });
    },
    
    // Update file list display
    updateFileList: function() {
        const fileList = document.getElementById('fileList');
        const fileItems = document.getElementById('fileItems');
        
        if (this.currentFiles.size > 0) {
            fileList.style.display = 'block';
            fileItems.innerHTML = '';
            
            this.currentFiles.forEach((fileData, fileId) => {
                this.createFileItem(fileId, fileData);
            });
        } else {
            fileList.style.display = 'none';
        }
        
        this.updateUploadButton();
    },
    
    // Create individual file item
    createFileItem: function(fileId, fileData) {
        const fileItems = document.getElementById('fileItems');
        
        const fileItemHtml = `
            <div class="file-item border rounded p-2 mb-2" id="fileItem_${fileId}">
                <div class="d-flex align-items-center justify-content-between">
                    <div class="d-flex align-items-center">
                        <i class="fas fa-file me-2 text-muted"></i>
                        <div>
                            <div class="fw-semibold small">${fileData.name}</div>
                            <div class="validation-status" id="validationStatus_${fileId}">
                                <i class="fas fa-spinner fa-spin text-primary"></i>
                                <small class="text-muted ms-1">Validating...</small>
                            </div>
                        </div>
                    </div>
                    <button type="button" class="btn btn-sm btn-outline-danger" onclick="window.UploadModal.removeFile('${fileId}')">
                        <i class="fas fa-times"></i>
                    </button>
                </div>
            </div>
        `;
        
        fileItems.insertAdjacentHTML('beforeend', fileItemHtml);
    },
    
    // Update specific file item validation status
    updateFileItem: function(fileId) {
        const statusElement = document.getElementById(`validationStatus_${fileId}`);
        if (!statusElement) return;
        
        const fileData = this.currentFiles.get(fileId);
        if (!fileData) return;
        
        let statusHtml = '';
        
        switch (fileData.validationStatus) {
            case 'valid':
                const info = fileData.validationResult;
                const accountName = info.account_name || 'Unknown Account';
                const accountType = info.type ? info.type.toUpperCase() : 'Unknown';
                
                statusHtml = `
                    <i class="fas fa-check-circle text-success"></i>
                    <small class="text-success ms-1">${accountType}: ${accountName}</small>
                `;
                break;
                
            case 'invalid':
                statusHtml = `
                    <i class="fas fa-exclamation-triangle text-warning"></i>
                    <small class="text-warning ms-1">${fileData.validationResult.error}</small>
                `;
                break;
                
            case 'error':
                statusHtml = `
                    <i class="fas fa-times-circle text-danger"></i>
                    <small class="text-danger ms-1">Validation failed</small>
                `;
                break;
                
            default:
                statusHtml = `
                    <i class="fas fa-spinner fa-spin text-primary"></i>
                    <small class="text-muted ms-1">Validating...</small>
                `;
        }
        
        statusElement.innerHTML = statusHtml;
    },
    
    // Remove file from list
    removeFile: function(fileId) {
        this.currentFiles.delete(fileId);
        const fileItem = document.getElementById(`fileItem_${fileId}`);
        if (fileItem) {
            fileItem.remove();
        }
        
        if (this.currentFiles.size === 0) {
            document.getElementById('fileList').style.display = 'none';
        }
        
        this.updateUploadButton();
    },
    
    // Update upload button state
    updateUploadButton: function() {
        const uploadBtn = document.getElementById('uploadBtn');
        if (!uploadBtn) return;
        
        const hasValidFiles = Array.from(this.currentFiles.values()).some(
            fileData => fileData.validationStatus === 'valid'
        );
        
        const hasInvalidFiles = Array.from(this.currentFiles.values()).some(
            fileData => fileData.validationStatus === 'invalid' || fileData.validationStatus === 'error'
        );
        
        const isValidating = Array.from(this.currentFiles.values()).some(
            fileData => fileData.validationStatus === 'validating'
        );
        
        uploadBtn.disabled = !hasValidFiles || isValidating;
        
        // Update button text based on state
        if (isValidating) {
            uploadBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i>Validating...';
        } else if (hasValidFiles && hasInvalidFiles) {
            const validCount = Array.from(this.currentFiles.values()).filter(
                fileData => fileData.validationStatus === 'valid'
            ).length;
            uploadBtn.innerHTML = `<i class="fas fa-upload me-1"></i>Upload ${validCount} Valid Files`;
        } else if (hasValidFiles) {
            uploadBtn.innerHTML = `<i class="fas fa-upload me-1"></i>Upload ${this.currentFiles.size} Files`;
        } else {
            uploadBtn.innerHTML = '<i class="fas fa-upload me-1"></i>Upload Files';
        }
    },
    
    // Start upload process
    startUpload: function() {
        const validFiles = Array.from(this.currentFiles.values()).filter(
            fileData => fileData.validationStatus === 'valid'
        );
        
        if (validFiles.length === 0) {
            window.StatementsUI.showAlert('warning', 'No valid files to upload');
            return;
        }
        
        console.log('Starting upload for', validFiles.length, 'files');
        
        // Close file selection modal
        const modal = bootstrap.Modal.getInstance(document.getElementById('uploadModal'));
        if (modal) {
            modal.hide();
        }
        
        // Show progress modal and start upload
        this.showProgressModal(validFiles);
        this.performUpload(validFiles);
    },
    
    // Show upload progress modal
    showProgressModal: function(filesToUpload) {
        const modalHtml = `
            <div class="modal fade" id="uploadProgressModal" tabindex="-1" aria-hidden="true" data-bs-backdrop="static">
                <div class="modal-dialog modal-dialog-centered">
                    <div class="modal-content">
                        <div class="modal-header">
                            <h5 class="modal-title">
                                <i class="fas fa-cloud-upload-alt text-primary me-2"></i>
                                Uploading Files
                            </h5>
                        </div>
                        <div class="modal-body">
                            <div class="mb-3">
                                <div class="d-flex justify-content-between mb-2">
                                    <span>Overall Progress</span>
                                    <span id="overallProgress">0 / ${filesToUpload.length}</span>
                                </div>
                                <div class="progress mb-3">
                                    <div class="progress-bar" id="overallProgressBar" style="width: 0%"></div>
                                </div>
                            </div>
                            
                            <div id="currentFile" class="mb-3">
                                <small class="text-muted">Preparing upload...</small>
                            </div>
                            
                            <div id="uploadResults" class="upload-results">
                                <!-- Upload results will appear here -->
                            </div>
                        </div>
                        <div class="modal-footer">
                            <button type="button" id="progressCloseBtn" class="btn btn-secondary" disabled>
                                <i class="fas fa-times me-1"></i>Close
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        `;
        
        document.body.insertAdjacentHTML('beforeend', modalHtml);
        const progressModal = new bootstrap.Modal(document.getElementById('uploadProgressModal'));
        progressModal.show();
        
        // Clean up on close
        document.getElementById('uploadProgressModal').addEventListener('hidden.bs.modal', function() {
            this.remove();
        });
    },
    
    // Perform actual upload
    performUpload: function(filesToUpload) {
        let uploadedCount = 0;
        const results = [];
        
        // Upload files sequentially to avoid overwhelming server
        const uploadNext = (index) => {
            if (index >= filesToUpload.length) {
                // All uploads complete
                this.showUploadComplete(results);
                return;
            }
            
            const fileData = filesToUpload[index];
            this.updateCurrentFile(fileData, index + 1, filesToUpload.length);
            
            // Create FormData for this file
            const formData = new FormData();
            formData.append('files', fileData.file);
            
            // Upload file
            fetch('/api/statements/upload', {
                method: 'POST',
                body: formData
            })
            .then(response => {
                if (response.status === 401 || response.status === 403) {
                    window.location.href = '/login';
                    return;
                }
                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}: ${response.statusText}`);
                }
                return response.json();
            })
            .then(data => {
                uploadedCount++;
                
                // Process response (API returns array of results)
                const fileResult = data.results && data.results.length > 0 ? data.results[0] : data;
                results.push({
                    filename: fileData.name,
                    success: fileResult.success,
                    message: fileResult.message || fileResult.error,
                    accountName: fileResult.account_name,
                    accountType: fileResult.account_type
                });
                
                this.updateProgress(uploadedCount, filesToUpload.length);
                this.addUploadResult(fileResult, fileData.name);
                
                // Upload next file after short delay
                setTimeout(() => uploadNext(index + 1), 500);
            })
            .catch(error => {
                console.error('Upload error:', error);
                uploadedCount++;
                
                results.push({
                    filename: fileData.name,
                    success: false,
                    message: error.message || 'Upload failed',
                    accountName: null,
                    accountType: null
                });
                
                this.updateProgress(uploadedCount, filesToUpload.length);
                this.addUploadResult({ success: false, error: error.message }, fileData.name);
                
                // Continue with next file
                setTimeout(() => uploadNext(index + 1), 500);
            });
        };
        
        // Start uploading
        uploadNext(0);
    },
    
    // Update current file display
    updateCurrentFile: function(fileData, current, total) {
        const currentFileElement = document.getElementById('currentFile');
        if (currentFileElement) {
            const accountInfo = fileData.validationResult;
            const accountText = accountInfo.account_name ? `to ${accountInfo.account_name}` : '';
            
            currentFileElement.innerHTML = `
                <div class="d-flex align-items-center">
                    <i class="fas fa-upload text-primary me-2"></i>
                    <div>
                        <div class="fw-semibold small">${fileData.name}</div>
                        <small class="text-muted">Uploading ${accountText}... (${current}/${total})</small>
                    </div>
                </div>
            `;
        }
    },
    
    // Update progress bars
    updateProgress: function(completed, total) {
        const percentage = (completed / total) * 100;
        
        const progressText = document.getElementById('overallProgress');
        if (progressText) {
            progressText.textContent = `${completed} / ${total}`;
        }
        
        const progressBar = document.getElementById('overallProgressBar');
        if (progressBar) {
            progressBar.style.width = `${percentage}%`;
            progressBar.setAttribute('aria-valuenow', percentage);
        }
    },
    
    // Add upload result to results area
    addUploadResult: function(result, filename) {
        const resultsContainer = document.getElementById('uploadResults');
        if (!resultsContainer) return;
        
        const resultHtml = `
            <div class="upload-result-item d-flex align-items-center mb-2 p-2 border rounded">
                <i class="fas ${result.success ? 'fa-check-circle text-success' : 'fa-times-circle text-danger'} me-2"></i>
                <div class="flex-grow-1">
                    <div class="fw-semibold small">${filename}</div>
                    <small class="text-muted">
                        ${result.success ? 
                            `✅ ${result.message || `Uploaded to ${result.account_name || 'account'}`}` : 
                            `❌ ${result.error || result.message || 'Upload failed'}`
                        }
                    </small>
                </div>
            </div>
        `;
        
        resultsContainer.insertAdjacentHTML('beforeend', resultHtml);
        
        // Scroll to bottom of results
        resultsContainer.scrollTop = resultsContainer.scrollHeight;
    },
    
    // Show upload completion
    showUploadComplete: function(results) {
        const successCount = results.filter(r => r.success).length;
        const failureCount = results.length - successCount;
        
        // Update current file display to show completion
        const currentFileElement = document.getElementById('currentFile');
        if (currentFileElement) {
            currentFileElement.innerHTML = `
                <div class="text-center">
                    <i class="fas fa-check-circle text-success me-2"></i>
                    <span class="fw-semibold">Upload Complete!</span>
                    <div class="mt-2">
                        <small class="text-success">✅ ${successCount} successful</small>
                        ${failureCount > 0 ? `<small class="text-danger ms-3">❌ ${failureCount} failed</small>` : ''}
                    </div>
                </div>
            `;
        }
        
        // Enable close button
        const closeBtn = document.getElementById('progressCloseBtn');
        if (closeBtn) {
            closeBtn.disabled = false;
            closeBtn.onclick = () => {
                const modal = bootstrap.Modal.getInstance(document.getElementById('uploadProgressModal'));
                if (modal) modal.hide();
                
                // Show summary alert
                if (successCount > 0) {
                    window.StatementsUI.showAlert('success', 
                        `Upload complete: ${successCount} files uploaded successfully`);
                } else {
                    window.StatementsUI.showAlert('danger', 
                        `Upload failed: ${failureCount} files could not be uploaded`);
                }
            };
        }
    }
};

// Add CSS styles for upload modal
const uploadModalStyles = `
<style>
.upload-drop-zone {
    background-color: #f8f9fa;
    transition: all 0.3s ease;
}

.upload-drop-zone:hover {
    background-color: #e9ecef;
}

.upload-drop-zone.border-primary {
    border-color: #0d6efd !important;
    background-color: #cff4fc !important;
}

.file-item {
    background-color: #f8f9fa;
}

.file-item:hover {
    background-color: #e9ecef;
}

.upload-results {
    max-height: 200px;
    overflow-y: auto;
}

.upload-result-item {
    background-color: #f8f9fa;
}

.progress {
    height: 8px;
}

.progress-bar {
    transition: width 0.3s ease;
}
</style>
`;

// Inject styles
document.head.insertAdjacentHTML('beforeend', uploadModalStyles);