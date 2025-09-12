// Bulk file loading functionality
window.BulkLoader = {
    
    loadAllFiles: function() {
        var app = window.StatementsApp;
        var currentYearData = app.accountDataByYear[app.currentYear] || {};
        
        // Find unloaded accounts
        var accountsToLoad = app.accountIds.filter(function(accountId) {
            return !currentYearData[accountId];
        });
        
        // If all accounts are loaded, show completion modal
        if (accountsToLoad.length === 0) {
            this.showAllFilesLoadedModal();
            return;
        }
        
        // Show loading modal and start loading process
        this.showLoadingModal(accountsToLoad.length);
        
        var processed = 0;
        var successful = 0;
        var errors = [];
        var self = this;
        
        // Load accounts with staggered timing
        accountsToLoad.forEach(function(accountId, index) {
            setTimeout(function() {
                self.updateProgress(processed + 1, accountsToLoad.length, successful, errors.length, accountId);
                
                // Load account data directly via API without triggering individual modals
                var loadBtn = document.getElementById('load-btn-' + accountId);
                if (loadBtn) {
                    loadBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';
                    loadBtn.disabled = true;
                }
                
                // Call API directly without using loadAccountData (which shows modals)
                window.StatementsAPI.loadAccount(accountId)
                    .then(function(accountData) {
                        processed++;
                        
                        // DEBUG: Log what we received
                        console.log('Bulk loader received data for', accountId, ':', {
                            total_files: accountData ? accountData.total_files : 'no data',
                            has_months: accountData && accountData.months ? Object.keys(accountData.months).length : 0,
                            first_month_data: accountData && accountData.months ? Object.values(accountData.months)[0] : null
                        });
                        
                        // DEBUG: Check the condition
                        var hasAccountData = !!accountData;
                        var hasMonths = accountData && !!accountData.months;
                        var hasFiles = accountData && accountData.total_files > 0;
                        
                        console.log('Condition check for', accountId, ':', {
                            hasAccountData: hasAccountData,
                            hasMonths: hasMonths,
                            hasFiles: hasFiles,
                            shouldProceed: hasAccountData && hasMonths && hasFiles
                        });
                        
                        if (accountData && accountData.months && accountData.total_files > 0) {
                            console.log('✅ Proceeding with UI update for', accountId);
                            
                            try {
                                successful++;
                                
                                // FIX: Initialize year data if it doesn't exist
                                if (!app.accountDataByYear[app.currentYear]) {
                                    app.accountDataByYear[app.currentYear] = {};
                                }
                                
                                // Store data and update UI
                                app.accountDataByYear[app.currentYear][accountId] = accountData;
                                
                                console.log('Attempting to update UI for', accountId);
                                
                                // Check if StatementsUI exists and has the function
                                if (window.StatementsUI && window.StatementsUI.updateAccountDisplay) {
                                    console.log('Calling StatementsUI.updateAccountDisplay for', accountId);
                                    window.StatementsUI.updateAccountDisplay(accountId, accountData);
                                } else {
                                    console.log('StatementsUI.updateAccountDisplay not available - using fallback for', accountId);
                                    // Fallback: try to update manually
                                    console.log('Starting fallback UI update for', accountId);
                                    
                                    for (var month = 1; month <= 12; month++) {
                                        var monthKey = app.currentYear + '-' + (month < 10 ? '0' + month : month);
                                        var monthData = accountData.months[monthKey];
                                        
                                        console.log('Month', month, 'data for', accountId, ':', monthData ? monthData.status : 'no data');
                                        
                                        var fileIcon = document.getElementById('file-icon-' + accountId + '-' + month);
                                        var dbIcon = document.getElementById('db-icon-' + accountId + '-' + month);
                                        var countElement = document.getElementById('count-' + accountId + '-' + month);
                                        var cell = document.querySelector('[data-account-id="' + accountId + '"][data-month="' + month + '"]');
                                        
                                        console.log('DOM elements for', accountId, month, ':', {
                                            fileIcon: !!fileIcon,
                                            dbIcon: !!dbIcon,
                                            countElement: !!countElement,
                                            cell: !!cell
                                        });
                                        
                                        if (fileIcon && monthData && monthData.status !== 'missing') {
                                            console.log('Updating icons for', accountId, month, 'status:', monthData.status);
                                            
                                            // Show PDF icon for BBVA files or Excel for STP
                                            if (accountData.type === 'stp') {
                                                if (monthData.xlsx) {
                                                    fileIcon.innerHTML = '<i class="fas fa-file-excel text-success"></i>';
                                                }
                                                if (monthData.pdf) {
                                                    fileIcon.innerHTML += '<i class="fas fa-file-pdf text-danger"></i>';
                                                }
                                            } else {
                                                fileIcon.innerHTML = '<i class="fas fa-file-pdf text-danger"></i>';
                                            }
                                            
                                            if (dbIcon) dbIcon.className = 'database-icon db-loaded';
                                            if (countElement) countElement.textContent = monthData.file_count || '1';
                                            if (cell) cell.className = 'month-cell';
                                            
                                            console.log('Updated UI for', accountId, month);
                                        } else {
                                            console.log('Skipping', accountId, month, '- missing elements or data');
                                        }
                                    }
                                    console.log('Fallback UI update completed for', accountId);
                                }
                                
                                // Show parse button
                                var parseBtn = document.getElementById('parse-btn-' + accountId);
                                if (parseBtn) {
                                    console.log('Showing parse button for', accountId);
                                    parseBtn.style.display = 'inline-block';
                                } else {
                                    console.log('Parse button not found for', accountId);
                                }
                                
                                // Update load button to green
                                if (loadBtn) {
                                    console.log('Updating load button for', accountId);
                                    if (window.StatementsUI && window.StatementsUI.updateLoadButton) {
                                        window.StatementsUI.updateLoadButton(accountId, true);
                                    } else {
                                        loadBtn.innerHTML = '<i class="fas fa-download"></i>';
                                        loadBtn.className = 'btn btn-success btn-sm';
                                    }
                                    loadBtn.disabled = false;
                                    console.log('Load button updated for', accountId);
                                } else {
                                    console.log('Load button not found for', accountId);
                                }
                                
                                console.log('UI update completed successfully for', accountId);
                                
                            } catch (error) {
                                console.error('Error updating UI for', accountId, ':', error);
                                errors.push(accountId + ': UI update failed - ' + error.message);
                            }
                        } else {
                            console.log('❌ Condition failed for', accountId, '- adding to errors');
                            // Handle case where files were found but no months data
                            if (accountData && accountData.total_files > 0) {
                                successful++;
                                app.accountDataByYear[app.currentYear][accountId] = accountData;
                                
                                // Still update UI even if months structure is different
                                window.StatementsUI.updateAccountDisplay(accountId, accountData);
                                
                                var parseBtn = document.getElementById('parse-btn-' + accountId);
                                if (parseBtn) parseBtn.style.display = 'inline-block';
                                
                                if (loadBtn) {
                                    window.StatementsUI.updateLoadButton(accountId, true);
                                    loadBtn.disabled = false;
                                }
                            } else {
                                errors.push(accountId + ': No files found');
                                if (loadBtn) {
                                    loadBtn.innerHTML = '<i class="fas fa-download"></i>';
                                    loadBtn.disabled = false;
                                }
                            }
                        }
                        
                        // Update progress
                        self.updateProgress(processed, accountsToLoad.length, successful, errors.length);
                        
                        // If this is the last account, show completion
                        if (processed === accountsToLoad.length) {
                            setTimeout(function() {
                                self.showCompletionModal(successful, errors.length, errors);
                            }, 500);
                        }
                    })
                    .catch(function(error) {
                        processed++;
                        errors.push(accountId + ': ' + (error.message || 'Load failed'));
                        
                        if (loadBtn) {
                            loadBtn.innerHTML = '<i class="fas fa-download"></i>';
                            loadBtn.disabled = false;
                        }
                        
                        // Update progress
                        self.updateProgress(processed, accountsToLoad.length, successful, errors.length);
                        
                        // If this is the last account, show completion
                        if (processed === accountsToLoad.length) {
                            setTimeout(function() {
                                self.showCompletionModal(successful, errors.length, errors);
                            }, 500);
                        }
                    });
            }, index * 1000); // 1 second stagger
        });
    },
    
    showLoadingModal: function(totalAccounts) {
        var modalHtml = `
            <div class="modal fade" id="bulkLoadingModal" tabindex="-1" aria-hidden="true" data-bs-backdrop="static">
                <div class="modal-dialog modal-dialog-centered">
                    <div class="modal-content">
                        <div class="modal-header">
                            <h5 class="modal-title">
                                <i class="fas fa-download text-primary me-2"></i>
                                Loading All Files from Teams
                            </h5>
                        </div>
                        <div class="modal-body">
                            <div class="mb-3">
                                <div class="d-flex justify-content-between mb-2">
                                    <span>Progress</span>
                                    <span id="bulkProgress">0 / ${totalAccounts}</span>
                                </div>
                                <div class="progress mb-3">
                                    <div class="progress-bar progress-bar-striped progress-bar-animated" 
                                         id="bulkProgressBar" style="width: 0%"></div>
                                </div>
                            </div>
                            <div id="currentAccount" class="text-center">
                                <small class="text-muted">Starting bulk load...</small>
                            </div>
                            <div class="mt-3">
                                <div class="row text-center">
                                    <div class="col-4">
                                        <div class="text-success fw-bold" id="successCount">0</div>
                                        <small class="text-muted">Successful</small>
                                    </div>
                                    <div class="col-4">
                                        <div class="text-danger fw-bold" id="errorCount">0</div>
                                        <small class="text-muted">Errors</small>
                                    </div>
                                    <div class="col-4">
                                        <div class="text-info fw-bold" id="remainingCount">${totalAccounts}</div>
                                        <small class="text-muted">Remaining</small>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        `;
        
        // Remove existing modal
        var existing = document.getElementById('bulkLoadingModal');
        if (existing) existing.remove();
        
        document.body.insertAdjacentHTML('beforeend', modalHtml);
        var modal = new bootstrap.Modal(document.getElementById('bulkLoadingModal'));
        modal.show();
    },
    
    updateProgress: function(processed, total, successful, errorCount, currentAccount) {
        var progressBar = document.getElementById('bulkProgressBar');
        var progressText = document.getElementById('bulkProgress');
        var currentAccountEl = document.getElementById('currentAccount');
        var successCountEl = document.getElementById('successCount');
        var errorCountEl = document.getElementById('errorCount');
        var remainingCountEl = document.getElementById('remainingCount');
        
        var percentage = Math.round((processed / total) * 100);
        
        if (progressBar) {
            progressBar.style.width = percentage + '%';
        }
        
        if (progressText) {
            progressText.textContent = processed + ' / ' + total;
        }
        
        if (currentAccountEl && currentAccount) {
            currentAccountEl.innerHTML = `
                <div class="d-flex align-items-center justify-content-center">
                    <i class="fas fa-download text-primary me-2"></i>
                    <span>Loading <strong>${currentAccount.toUpperCase()}</strong>...</span>
                </div>
            `;
        } else if (currentAccountEl && processed === total) {
            currentAccountEl.innerHTML = `
                <div class="text-success">
                    <i class="fas fa-check-circle me-2"></i>
                    All accounts processed
                </div>
            `;
        }
        
        if (successCountEl) successCountEl.textContent = successful;
        if (errorCountEl) errorCountEl.textContent = errorCount;
        if (remainingCountEl) remainingCountEl.textContent = Math.max(0, total - processed);
    },
    
    showCompletionModal: function(successful, errorCount, errors) {
        // Close loading modal
        var loadingModal = bootstrap.Modal.getInstance(document.getElementById('bulkLoadingModal'));
        if (loadingModal) loadingModal.hide();
        
        setTimeout(() => {
            var existing = document.getElementById('bulkLoadingModal');
            if (existing) existing.remove();
            
            var isSuccess = errorCount === 0;
            var modalHtml = `
                <div class="modal fade" id="bulkCompleteModal" tabindex="-1" aria-hidden="true">
                    <div class="modal-dialog modal-dialog-centered">
                        <div class="modal-content">
                            <div class="modal-header">
                                <h5 class="modal-title">
                                    <i class="fas fa-${isSuccess ? 'check-circle text-success' : 'exclamation-triangle text-warning'} me-2"></i>
                                    All Files Loading Complete
                                </h5>
                                <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                            </div>
                            <div class="modal-body text-center py-4">
                                <div class="mb-3">
                                    <i class="fas fa-${isSuccess ? 'check-circle text-success' : 'exclamation-triangle text-warning'}" 
                                       style="font-size: 3rem;"></i>
                                </div>
                                <div class="row">
                                    <div class="col-6">
                                        <div class="bg-light rounded p-2">
                                            <div class="text-muted small">Loaded Successfully</div>
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
                                ${successful > 0 ? `<p class="text-muted mt-3">Files are now ready for downloading and parsing.</p>` : ''}
                                ${errorCount > 0 && errors.length <= 3 ? `
                                <div class="mt-3">
                                    <h6>Errors:</h6>
                                    <div class="text-start">
                                        ${errors.slice(0, 3).map(error => `<small class="text-danger d-block">• ${error}</small>`).join('')}
                                        ${errors.length > 3 ? `<small class="text-muted d-block">...and ${errors.length - 3} more</small>` : ''}
                                    </div>
                                </div>
                                ` : ''}
                            </div>
                            <div class="modal-footer justify-content-center">
                                <button type="button" class="btn btn-${isSuccess ? 'success' : 'warning'}" data-bs-dismiss="modal">
                                    <i class="fas fa-thumbs-up me-1"></i>${isSuccess ? 'Perfect!' : 'OK'}
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            `;
            
            document.body.insertAdjacentHTML('beforeend', modalHtml);
            var modal = new bootstrap.Modal(document.getElementById('bulkCompleteModal'));
            modal.show();
            
            // Clean up after modal closes
            document.getElementById('bulkCompleteModal').addEventListener('hidden.bs.modal', function() {
                this.remove();
            });
            
        }, 300);
    },
    
    showAllFilesLoadedModal: function() {
        var modalHtml = `
            <div class="modal fade" id="allLoadedModal" tabindex="-1" aria-hidden="true">
                <div class="modal-dialog modal-dialog-centered">
                    <div class="modal-content">
                        <div class="modal-header">
                            <h5 class="modal-title">
                                <i class="fas fa-info-circle text-info me-2"></i>
                                All Files Already Loaded
                            </h5>
                            <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                        </div>
                        <div class="modal-body text-center py-4">
                            <div class="mb-3">
                                <i class="fas fa-check-double text-success" style="font-size: 3rem;"></i>
                            </div>
                            <p class="mb-0">
                                All accounts for <strong>${window.StatementsApp.currentYear}</strong> have already been loaded from Teams.
                            </p>
                            <p class="text-muted mt-2 small">
                                If you're expecting new files, they may not be uploaded to Teams yet, or try refreshing individual accounts.
                            </p>
                        </div>
                        <div class="modal-footer justify-content-center">
                            <button type="button" class="btn btn-primary" data-bs-dismiss="modal">
                                <i class="fas fa-check me-1"></i>Got it!
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        `;
        
        var existing = document.getElementById('allLoadedModal');
        if (existing) existing.remove();
        
        document.body.insertAdjacentHTML('beforeend', modalHtml);
        var modal = new bootstrap.Modal(document.getElementById('allLoadedModal'));
        modal.show();
        
        // Clean up
        document.getElementById('allLoadedModal').addEventListener('hidden.bs.modal', function() {
            this.remove();
        });
    }
};