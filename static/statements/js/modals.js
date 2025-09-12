// Modal system for statements interface
window.Modals = {
    
    // Show success modal for individual account loading
    showSuccess: function(accountId, accountData) {
        var fileCount = accountData.total_files || 0;
        var transactionCount = accountData.total_transactions || 0;
        
        this._createAndShowModal('successModal', `
            <div class="modal-header">
                <h5 class="modal-title">
                    <i class="fas fa-check-circle text-success me-2"></i>Files Loaded Successfully
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
                <p class="text-muted mt-3 mb-0">Data for ${window.StatementsApp.currentYear} is now ready for parsing.</p>
            </div>
            <div class="modal-footer justify-content-center">
                <button type="button" class="btn btn-success" data-bs-dismiss="modal">
                    <i class="fas fa-thumbs-up me-1"></i>Great!
                </button>
            </div>
        `);
    },
    
    // Show no additional files modal
    showNoAdditionalFiles: function(accountId) {
        this._createAndShowModal('noFilesModal', `
            <div class="modal-header">
                <h5 class="modal-title">
                    <i class="fas fa-info-circle text-info me-2"></i>No Additional Files
                </h5>
                <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
            </div>
            <div class="modal-body text-center py-4">
                <div class="mb-3">
                    <i class="fas fa-folder-open text-muted" style="font-size: 3rem;"></i>
                </div>
                <h6>Account: <span class="text-primary">${accountId.toUpperCase()}</span></h6>
                <p class="text-muted mb-0">All available files for ${window.StatementsApp.currentYear} have already been loaded.</p>
            </div>
            <div class="modal-footer justify-content-center">
                <button type="button" class="btn btn-primary" data-bs-dismiss="modal">
                    <i class="fas fa-check me-1"></i>OK
                </button>
            </div>
        `);
    },
    
    // Show file selection modal for downloads
    showFileSelection: function(accountId, month, monthData) {
        var monthNames = ['', 'January', 'February', 'March', 'April', 'May', 'June', 
                         'July', 'August', 'September', 'October', 'November', 'December'];
        
        var excelCount = (monthData.xlsx && monthData.xlsx.transaction_count) || 0;
        var pdfCount = (monthData.pdf && monthData.pdf.transaction_count) || 0;
        
        this._createAndShowModal('fileSelectionModal', `
            <div class="modal-header">
                <h5 class="modal-title">
                    <i class="fas fa-download text-primary me-2"></i>Select File to Download
                </h5>
                <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
            </div>
            <div class="modal-body">
                <p class="text-center mb-4">
                    <strong>${accountId.toUpperCase()}</strong> - ${monthNames[month]} ${window.StatementsApp.currentYear}
                </p>
                <div class="d-grid gap-3">
                    <button type="button" class="btn btn-outline-success btn-lg d-flex align-items-center justify-content-between" 
                            onclick="downloadFile('${accountId}', ${month}, 'xlsx'); window.Modals.hide('fileSelectionModal');">
                        <div class="d-flex align-items-center">
                            <i class="fas fa-file-excel text-success me-3" style="font-size: 1.5rem;"></i>
                            <div class="text-start">
                                <div class="fw-bold">Excel File</div>
                                <small class="text-muted">Statement data</small>
                            </div>
                        </div>
                        <div class="text-end">
                            <small class="text-muted">${excelCount.toLocaleString()} transactions</small>
                        </div>
                    </button>
                    <button type="button" class="btn btn-outline-danger btn-lg d-flex align-items-center justify-content-between"
                            onclick="downloadFile('${accountId}', ${month}, 'pdf'); window.Modals.hide('fileSelectionModal');">
                        <div class="d-flex align-items-center">
                            <i class="fas fa-file-pdf text-danger me-3" style="font-size: 1.5rem;"></i>
                            <div class="text-start">
                                <div class="fw-bold">PDF File</div>
                                <small class="text-muted">Bank statement</small>
                            </div>
                        </div>
                        <div class="text-end">
                            <small class="text-muted">${pdfCount.toLocaleString()} transactions</small>
                        </div>
                    </button>
                </div>
            </div>
            <div class="modal-footer">
                <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">
                    <i class="fas fa-times me-1"></i>Cancel
                </button>
            </div>
        `);
    },
    
    // Show loading progress modal for bulk operations
    showLoadingProgress: function(totalAccounts) {
        this._createAndShowModal('loadingAllFilesModal', `
            <div class="modal-header">
                <h5 class="modal-title">
                    <i class="fas fa-download text-primary me-2"></i>Loading All Files
                </h5>
            </div>
            <div class="modal-body text-center py-4">
                <div class="mb-3">
                    <i class="fas fa-cloud-download-alt text-primary" style="font-size: 3rem;"></i>
                </div>
                <h6>Loading files from Teams for ${window.StatementsApp.currentYear}</h6>
                <div class="progress mt-3 mb-3" style="height: 20px;">
                    <div id="loadingProgressBar" class="progress-bar bg-primary" role="progressbar" style="width: 0%" 
                         aria-valuenow="0" aria-valuemin="0" aria-valuemax="100">0%</div>
                </div>
                <div id="loadingDetails" class="text-muted">Preparing to load ${totalAccounts} accounts...</div>
                <div class="row mt-3">
                    <div class="col-4">
                        <div class="bg-light rounded p-2">
                            <div class="text-muted small">Processed</div>
                            <div id="processedCount" class="h6 mb-0 text-info">0</div>
                        </div>
                    </div>
                    <div class="col-4">
                        <div class="bg-light rounded p-2">
                            <div class="text-muted small">Successful</div>
                            <div id="successfulCount" class="h6 mb-0 text-success">0</div>
                        </div>
                    </div>
                    <div class="col-4">
                        <div class="bg-light rounded p-2">
                            <div class="text-muted small">Errors</div>
                            <div id="errorCount" class="h6 mb-0 text-danger">0</div>
                        </div>
                    </div>
                </div>
            </div>
        `, {backdrop: 'static', keyboard: false});
    },
    
    // Update loading progress
    updateProgress: function(processed, total, successful, errorCount) {
        var progressPercent = Math.round((processed / total) * 100);
        
        var progressBar = document.getElementById('loadingProgressBar');
        var processedCountEl = document.getElementById('processedCount');
        var successfulCountEl = document.getElementById('successfulCount');
        var errorCountEl = document.getElementById('errorCount');
        var detailsEl = document.getElementById('loadingDetails');
        
        if (progressBar) {
            progressBar.style.width = progressPercent + '%';
            progressBar.textContent = progressPercent + '%';
            progressBar.setAttribute('aria-valuenow', progressPercent);
        }
        
        if (processedCountEl) processedCountEl.textContent = processed + '/' + total;
        if (successfulCountEl) successfulCountEl.textContent = successful;
        if (errorCountEl) errorCountEl.textContent = errorCount;
        
        if (detailsEl) {
            detailsEl.textContent = processed === total 
                ? 'All accounts processed. Finalizing...' 
                : `Processing account ${processed + 1} of ${total}...`;
        }
    },
    
    // Hide loading modal
    hideLoading: function() {
        this.hide('loadingAllFilesModal');
    },
    
    // Show loading completion modal
    showLoadingComplete: function(successful, errorCount, errors) {
        var isSuccess = errorCount === 0;
        var iconClass = isSuccess ? 'fa-check-circle text-success' : 'fa-exclamation-triangle text-warning';
        var title = isSuccess ? 'All Files Loaded Successfully' : 'Files Loading Completed';
        
        var errorDetails = '';
        if (errors && errors.length > 0) {
            errorDetails = '<div class="mt-3"><h6>Errors:</h6><ul class="text-start">';
            errors.forEach(function(error) {
                errorDetails += `<li><strong>${error.accountId}</strong>: ${error.error}</li>`;
            });
            errorDetails += '</ul></div>';
        }
        
        this._createAndShowModal('completedModal', `
            <div class="modal-header">
                <h5 class="modal-title">
                    <i class="fas ${iconClass} me-2"></i>${title}
                </h5>
                <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
            </div>
            <div class="modal-body text-center py-4">
                <div class="mb-3">
                    <i class="fas ${iconClass}" style="font-size: 3rem;"></i>
                </div>
                <h6>Loading Complete for ${window.StatementsApp.currentYear}</h6>
                <div class="row mt-3">
                    <div class="col-6">
                        <div class="bg-light rounded p-2">
                            <div class="text-muted small">Successful</div>
                            <div class="h5 mb-0 text-success">${successful}</div>
                        </div>
                    </div>
                    <div class="col-6">
                        <div class="bg-light rounded p-2">
                            <div class="text-muted small">Errors</div>
                            <div class="h5 mb-0 text-danger">${errorCount}</div>
                        </div>
                    </div>
                </div>
                ${errorDetails}
            </div>
            <div class="modal-footer justify-content-center">
                <button type="button" class="btn btn-success" data-bs-dismiss="modal">
                    <i class="fas fa-check me-1"></i>Done
                </button>
            </div>
        `);
    },
    
    // Show all files already complete modal
    showAllFilesComplete: function() {
        this._createAndShowModal('allFilesCompleteModal', `
            <div class="modal-header">
                <h5 class="modal-title">
                    <i class="fas fa-info-circle text-info me-2"></i>All Files Already Loaded
                </h5>
                <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
            </div>
            <div class="modal-body text-center py-4">
                <div class="mb-3">
                    <i class="fas fa-check-double text-success" style="font-size: 3rem;"></i>
                </div>
                <h6>All Available Files Loaded</h6>
                <p class="text-muted mb-0">All accounts for ${window.StatementsApp.currentYear} have already been loaded from Teams.</p>
                <p class="text-muted small mt-2">If you expect new files, they may not be available yet or may require re-uploading to Teams.</p>
            </div>
            <div class="modal-footer justify-content-center">
                <button type="button" class="btn btn-primary" data-bs-dismiss="modal">
                    <i class="fas fa-check me-1"></i>OK
                </button>
            </div>
        `);
    },
    
    // Generic modal creation and management
    _createAndShowModal: function(modalId, content, options) {
        // Remove existing modal
        var existingModal = document.getElementById(modalId);
        if (existingModal) {
            existingModal.remove();
        }
        
        // Create modal HTML
        var modalHtml = `
            <div class="modal fade" id="${modalId}" tabindex="-1" aria-hidden="true">
                <div class="modal-dialog modal-dialog-centered">
                    <div class="modal-content">${content}</div>
                </div>
            </div>
        `;
        
        // Add to body
        document.body.insertAdjacentHTML('beforeend', modalHtml);
        
        // Show modal
        var modal = new bootstrap.Modal(document.getElementById(modalId), options || {});
        modal.show();
        
        // Auto cleanup
        document.getElementById(modalId).addEventListener('hidden.bs.modal', function() {
            this.remove();
        });
        
        return modal;
    },
    
    // Hide specific modal
    hide: function(modalId) {
        var modal = bootstrap.Modal.getInstance(document.getElementById(modalId));
        if (modal) {
            modal.hide();
        }
    }
};