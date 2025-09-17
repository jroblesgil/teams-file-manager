// UI manipulation functions - Production Version
window.StatementsUI = {
    /**
     * Update account display after loading data
     * @param {string} accountId - Account identifier
     * @param {Object} accountData - Account data with months information
     */
    updateAccountDisplay: function(accountId, accountData) {
        if (!accountData || !accountData.months) {
            return;
        }
        
        for (var month = 1; month <= 12; month++) {
            var monthKey = window.StatementsApp.currentYear + '-' + (month < 10 ? '0' + month : month);
            var monthData = accountData.months[monthKey];
            this.updateMonthCell(accountId, month, monthData);
        }
        
        this.updateLoadButton(accountId, true);
    },
    
    /**
     * Update load button state
     * @param {string} accountId - Account identifier
     * @param {boolean} isLoaded - Whether account is loaded
     */
    updateLoadButton: function(accountId, isLoaded) {
        var loadBtn = document.getElementById('load-btn-' + accountId);
        if (!loadBtn) return;
        
        if (isLoaded) {
            loadBtn.innerHTML = '<i class="fas fa-download"></i>';
            loadBtn.className = 'btn btn-success btn-sm';
            loadBtn.title = 'Account loaded - click to refresh';
        } else {
            loadBtn.innerHTML = '<i class="fas fa-download"></i>';
            loadBtn.className = 'btn btn-primary btn-sm';
            loadBtn.title = 'Load account data';
        }
    },
    
    /**
     * Update individual month cell
     * @param {string} accountId - Account identifier
     * @param {number} month - Month number (1-12)
     * @param {Object} monthData - Month data or null if no data
     */
    updateMonthCell: function(accountId, month, monthData) {
        var elements = this.getMonthElements(accountId, month);
        if (!elements.valid) return;
        
        if (!monthData || monthData.status === 'missing' || monthData.file_count === 0) {
            this.setEmptyCell(elements);
        } else {
            this.setFileCell(elements, accountId, monthData);
        }
    },
    
    /**
     * Get month cell DOM elements
     * @param {string} accountId - Account identifier
     * @param {number} month - Month number
     * @returns {Object} Object containing DOM elements and validity flag
     */
    getMonthElements: function(accountId, month) {
        var fileIcon = document.getElementById('file-icon-' + accountId + '-' + month);
        var dbIcon = document.getElementById('db-icon-' + accountId + '-' + month);
        var countElement = document.getElementById('count-' + accountId + '-' + month);
        var cell = document.querySelector('[data-account-id="' + accountId + '"][data-month="' + month + '"]');
        
        var valid = fileIcon && dbIcon && countElement && cell;
        
        return {
            fileIcon: fileIcon,
            dbIcon: dbIcon,
            countElement: countElement,
            cell: cell,
            valid: valid
        };
    },
    
    /**
     * Set empty cell state (no files)
     * @param {Object} elements - DOM elements object
     */
    setEmptyCell: function(elements) {
        elements.fileIcon.innerHTML = '';
        elements.dbIcon.className = 'database-icon db-not-loaded';
        elements.countElement.textContent = '-';
        elements.cell.className = 'month-cell no-file';
        elements.cell.style.cursor = 'default';
    },
    
    /**
     * Set file cell state (has files)
     * @param {Object} elements - DOM elements object
     * @param {string} accountId - Account identifier
     * @param {Object} monthData - Month data
     */
    setFileCell: function(elements, accountId, monthData) {
        var accountRow = document.querySelector('[data-account-id="' + accountId + '"]');
        var accountType = accountRow ? accountRow.getAttribute('data-account-type') : 'unknown';
        
        this.setFileIcon(elements.fileIcon, accountType, monthData);
        this.setParseStatus(elements, monthData, accountType);
        
        elements.cell.className = 'month-cell';
        elements.cell.style.cursor = 'pointer';
    },
    
    /**
     * Set file type icon based on available files
     * @param {Element} fileIcon - File icon element
     * @param {string} accountType - Account type (stp/bbva)
     * @param {Object} monthData - Month data
     */
    setFileIcon: function(fileIcon, accountType, monthData) {
        var hasExcel = monthData.xlsx && monthData.xlsx !== null;
        var hasPdf = monthData.pdf && monthData.pdf !== null;
        
        var iconHtml = '';
        
        if (hasExcel && hasPdf) {
            iconHtml = '<i class="fas fa-file-excel text-success me-1"></i><i class="fas fa-file-pdf text-danger"></i>';
        } else if (hasExcel) {
            iconHtml = '<i class="fas fa-file-excel text-success"></i>';
        } else if (hasPdf) {
            iconHtml = '<i class="fas fa-file-pdf text-danger"></i>';
        }
        
        fileIcon.innerHTML = iconHtml;
    },
    
    /**
     * Set parse status and transaction count
     * @param {Object} elements - DOM elements object
     * @param {Object} monthData - Month data
     * @param {string} accountType - Account type
     */
    setParseStatus: function(elements, monthData, accountType) {
        var isParsed = false;
        var totalTransactionCount = 0;
        
        // Handle STP accounts to avoid double-counting transactions
        if (accountType === 'stp') {
            // For STP: Only count XLSX transactions to avoid duplication
            if (monthData.xlsx && (monthData.xlsx.transaction_count > 0 || monthData.xlsx.parse_status === 'parsed')) {
                isParsed = true;
                totalTransactionCount = monthData.xlsx.transaction_count;
            }
            // Check if PDF is also parsed for status
            if (monthData.pdf && monthData.pdf.parse_status === 'parsed') {
                isParsed = true;
            }
        } else {
            // For BBVA and other account types: Sum all file transactions
            if (monthData.xlsx && (monthData.xlsx.transaction_count > 0 || monthData.xlsx.parse_status === 'parsed')) {
                isParsed = true;
                totalTransactionCount += monthData.xlsx.transaction_count;
            }

            if (monthData.pdf && (monthData.pdf.transaction_count > 0 || monthData.pdf.parse_status === 'parsed')) {
                isParsed = true;
                totalTransactionCount += monthData.pdf.transaction_count;
            }
        }
        
        // Fallback to root level transaction count
        if (!isParsed && monthData.transaction_count && monthData.transaction_count > 0) {
            isParsed = true;
            totalTransactionCount = monthData.transaction_count;
        }
        
        elements.dbIcon.className = isParsed ? 'database-icon db-parsed' : 'database-icon db-loaded';
        elements.countElement.textContent = isParsed && totalTransactionCount > 0 ? this.formatCount(totalTransactionCount) : '-';
    },

    /**
     * Reset all UI elements to initial state
     */
    resetAllUI: function() {
        var self = this;
        window.StatementsApp.accountIds.forEach(function(accountId) {
            for (var month = 1; month <= 12; month++) {
                var elements = self.getMonthElements(accountId, month);
                if (elements.valid) {
                    self.setEmptyCell(elements);
                }
            }
            
            self.resetAccountButtons(accountId);
        });
    },
    
    /**
     * Reset account action buttons to initial state
     * @param {string} accountId - Account identifier
     */
    resetAccountButtons: function(accountId) {
        var loadBtn = document.getElementById('load-btn-' + accountId);
        var parseBtn = document.getElementById('parse-btn-' + accountId);
        
        if (loadBtn) {
            this.updateLoadButton(accountId, false);
            loadBtn.disabled = false;
        }
        if (parseBtn) {
            parseBtn.style.display = 'none';
        }
    },
    
    /**
     * Show alert message with auto-dismiss
     * @param {string} type - Alert type (success, danger, warning, info)
     * @param {string} message - Alert message
     */
    showAlert: function(type, message) {
        var alertElement = document.getElementById('statusAlert');
        if (!alertElement) {
            alertElement = document.createElement('div');
            alertElement.id = 'statusAlert';
            alertElement.className = 'alert position-fixed top-0 end-0 m-3';
            alertElement.style.zIndex = '1050';
            alertElement.style.minWidth = '300px';
            alertElement.style.display = 'none';
            document.body.appendChild(alertElement);
        }
        
        alertElement.className = 'alert alert-' + type + ' position-fixed top-0 end-0 m-3';
        alertElement.innerHTML = message + '<button type="button" class="btn-close" data-bs-dismiss="alert"></button>';
        alertElement.style.display = 'block';
        alertElement.style.zIndex = '1050';
        alertElement.style.minWidth = '300px';
        
        setTimeout(function() {
            alertElement.style.display = 'none';
        }, 5000);
    },
    
    /**
     * Format transaction count for display
     * @param {number} count - Transaction count
     * @returns {string} Formatted count string
     */
    formatCount: function(count) {
        if (!count || count === 0) return '-';
        if (count < 1000) return count.toString();
        if (count < 1000000) return (count / 1000).toFixed(1) + 'k';
        return (count / 1000000).toFixed(1) + 'M';
    },
    
    /**
     * Show upload progress in modal
     * @param {number} percentage - Progress percentage (0-100)
     * @param {string} status - Status message
     * @param {string} currentFile - Current file being processed
     */
    showUploadProgress: function(percentage, status, currentFile) {
        var uploadProgress = document.getElementById('uploadProgress');
        var uploadProgressBar = document.getElementById('uploadProgressBar');
        var uploadStatus = document.getElementById('uploadStatus');
        
        if (!uploadProgress || !uploadProgressBar || !uploadStatus) {
            return;
        }
        
        uploadProgress.style.display = 'block';
        uploadProgressBar.style.width = percentage + '%';
        
        var statusText = status || 'Processing...';
        if (currentFile) {
            statusText += ' (' + currentFile + ')';
        }
        uploadStatus.textContent = statusText;
        
        // Color coding based on progress
        uploadProgressBar.className = 'progress-bar';
        if (percentage >= 100) {
            uploadProgressBar.classList.add('bg-success');
        } else if (percentage >= 50) {
            uploadProgressBar.classList.add('bg-info');
        } else {
            uploadProgressBar.classList.add('bg-primary');
        }
    },
    
    /**
     * Show upload results in modal
     * @param {Object} results - Upload results object
     */
    showUploadResults: function(results) {
        var uploadResults = document.getElementById('uploadResults');
        var uploadResultsList = document.getElementById('uploadResultsList');
        
        if (!uploadResults || !uploadResultsList) {
            return;
        }
        
        var successCount = results.successful_uploads || 0;
        var totalCount = results.total_files || 0;
        var failedCount = results.failed_uploads || 0;
        
        var alertClass = results.success ? 'alert-success' : 'alert-danger';
        var iconClass = results.success ? 'fa-check-circle' : 'fa-exclamation-triangle';
        
        var summaryHtml = `
            <div class="alert ${alertClass}" role="alert">
                <h6 class="alert-heading">
                    <i class="fas ${iconClass} me-2"></i>
                    Upload ${results.success ? 'Completed' : 'Failed'}
                </h6>
                <p class="mb-0">
                    ${successCount} of ${totalCount} files uploaded successfully.
                    ${failedCount > 0 ? ` ${failedCount} files failed.` : ''}
                </p>
            </div>
        `;
        
        // Add individual file results
        if (results.results && results.results.length > 0) {
            summaryHtml += '<div class="list-group mt-2">';
            results.results.forEach(function(result) {
                var iconClass = result.success ? 'fa-check-circle text-success' : 'fa-times-circle text-danger';
                var message = result.success ? 
                    `Uploaded to ${result.account_name || result.account_type || 'account'}` : 
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
        
        uploadResultsList.innerHTML = summaryHtml;
        uploadResults.style.display = 'block';
    },
    
    /**
     * Update upload button state
     * @param {string} state - Button state (default, uploading, success, error)
     * @param {string} text - Button text
     * @param {boolean} disabled - Whether button is disabled
     */
    updateUploadButton: function(state, text, disabled) {
        var uploadBtn = document.getElementById('uploadBtn');
        if (!uploadBtn) return;
        
        uploadBtn.disabled = disabled || false;
        
        var iconClass = 'fa-upload';
        if (state === 'uploading') {
            iconClass = 'fa-spinner fa-spin';
        } else if (state === 'success') {
            iconClass = 'fa-check';
        } else if (state === 'error') {
            iconClass = 'fa-exclamation-triangle';
        }
        
        uploadBtn.innerHTML = `<i class="fas ${iconClass} me-1"></i>${text || 'Upload Files'}`;
    },
    
    /**
     * Show file preview in upload modal
     * @param {FileList} files - Selected files
     */
    showFilePreview: function(files) {
        var selectedFilesSection = document.getElementById('selectedFilesSection');
        var selectedFilesList = document.getElementById('selectedFilesList');
        
        if (!selectedFilesSection || !selectedFilesList) {
            return;
        }
        
        selectedFilesList.innerHTML = '';
        
        if (files.length === 0) {
            selectedFilesSection.style.display = 'none';
            return;
        }
        
        var self = this;
        Array.from(files).forEach(function(file, index) {
            var fileItem = document.createElement('div');
            fileItem.className = 'border rounded p-2 mb-2 d-flex justify-content-between align-items-center';
            
            var validation = self.validateFile(file);
            
            if (validation.valid) {
                fileItem.classList.add('border-success', 'bg-light');
            } else {
                fileItem.classList.add('border-danger', 'bg-light');
            }
            
            var iconClass = 'fa-file';
            var iconColorClass = 'text-muted';
            
            if (file.name.toLowerCase().endsWith('.pdf')) {
                iconClass = 'fa-file-pdf';
                iconColorClass = 'text-danger';
            } else if (file.name.toLowerCase().match(/\.(xlsx|xls)$/)) {
                iconClass = 'fa-file-excel';
                iconColorClass = 'text-success';
            }
            
            fileItem.innerHTML = `
                <div class="d-flex align-items-center">
                    <i class="fas ${iconClass} ${iconColorClass} me-2"></i>
                    <div>
                        <div class="fw-bold">${file.name}</div>
                        <small class="text-muted">${(file.size / 1024 / 1024).toFixed(2)} MB</small>
                        ${!validation.valid ? `<br><small class="text-danger">${validation.error}</small>` : ''}
                        ${validation.valid && validation.info ? `<br><small class="text-info">${validation.info}</small>` : ''}
                    </div>
                </div>
                <span class="badge ${validation.valid ? 'bg-success' : 'bg-danger'}">
                    ${validation.valid ? '✓ Valid' : '✗ Invalid'}
                </span>
            `;
            
            selectedFilesList.appendChild(fileItem);
        });
        
        selectedFilesSection.style.display = 'block';
    },
    
    /**
     * Validate upload file
     * @param {File} file - File to validate
     * @returns {Object} Validation result
     */
    validateFile: function(file) {
        var fileName = file.name.toLowerCase();
        var validExtensions = ['.pdf', '.xlsx', '.xls'];
        var hasValidExtension = validExtensions.some(function(ext) {
            return fileName.endsWith(ext);
        });
        
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
    },
    
    /**
     * Clear upload modal state
     */
    clearUploadModal: function() {
        var selectedFilesSection = document.getElementById('selectedFilesSection');
        var uploadProgress = document.getElementById('uploadProgress');
        var uploadResults = document.getElementById('uploadResults');
        var fileInput = document.getElementById('fileInput');
        
        if (selectedFilesSection) selectedFilesSection.style.display = 'none';
        if (uploadProgress) uploadProgress.style.display = 'none';
        if (uploadResults) uploadResults.style.display = 'none';
        if (fileInput) fileInput.value = '';
        
        this.updateUploadButton('default', 'Upload Files', true);
    },
    
    /**
     * Handle drag and drop visual feedback
     * @param {Element} element - Element to apply feedback to
     * @param {string} state - Feedback state (enter, leave, drop)
     */
    handleDragFeedback: function(element, state) {
        if (!element) return;
        
        switch (state) {
            case 'enter':
                element.classList.add('border-success');
                element.classList.remove('btn-outline-primary');
                element.classList.add('btn-outline-success');
                break;
            case 'leave':
                element.classList.remove('border-success', 'btn-outline-success');
                element.classList.add('btn-outline-primary');
                break;
            case 'drop':
                element.classList.remove('border-success', 'btn-outline-success');
                element.classList.add('btn-outline-primary');
                break;
        }
    }
};