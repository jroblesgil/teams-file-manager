// UI manipulation functions
// UI manipulation functions with upload support
window.StatementsUI = {
    // Update account display after loading data
    updateAccountDisplay: function(accountId, accountData) {
        console.log('=== UPDATING ACCOUNT DISPLAY ===');
        console.log('Account ID:', accountId);
        console.log('Account Data:', accountData);
        
        if (!accountData || !accountData.months) {
            console.error('Invalid account data for', accountId);
            return;
        }
        
        console.log('Months available:', Object.keys(accountData.months));
        
        for (var month = 1; month <= 12; month++) {
            var monthKey = window.StatementsApp.currentYear + '-' + (month < 10 ? '0' + month : month);
            var monthData = accountData.months[monthKey];
            
            console.log('Processing month', month, 'key:', monthKey, 'data:', monthData);
            this.updateMonthCell(accountId, month, monthData);
        }
        
        // IMPORTANT: Update load button to green state for loaded accounts
        this.updateLoadButton(accountId, true);
        console.log('Set load button to green for loaded account:', accountId);
    },
    
    // Update load button state
    updateLoadButton: function(accountId, isLoaded) {
        var loadBtn = document.getElementById('load-btn-' + accountId);
        if (!loadBtn) return;
        
        if (isLoaded) {
            loadBtn.innerHTML = '<i class="fas fa-download"></i>';  // Keep download icon
            loadBtn.className = 'btn btn-success btn-sm';           // Green color
            loadBtn.title = 'Account loaded - click to refresh';
        } else {
            loadBtn.innerHTML = '<i class="fas fa-download"></i>';
            loadBtn.className = 'btn btn-primary btn-sm';           // Blue color
            loadBtn.title = 'Load account data';
        }
    },
    
    // Update individual month cell
    updateMonthCell: function(accountId, month, monthData) {
        var elements = this.getMonthElements(accountId, month);
        if (!elements.valid) return;
        
        if (!monthData || monthData.status === 'missing' || monthData.file_count === 0) {
            this.setEmptyCell(elements);
        } else {
            this.setFileCell(elements, accountId, monthData);
        }
    },
    
    // Get month cell elements
    getMonthElements: function(accountId, month) {
        var fileIcon = document.getElementById('file-icon-' + accountId + '-' + month);
        var dbIcon = document.getElementById('db-icon-' + accountId + '-' + month);
        var countElement = document.getElementById('count-' + accountId + '-' + month);
        var cell = document.querySelector('[data-account-id="' + accountId + '"][data-month="' + month + '"]');
        
        var valid = fileIcon && dbIcon && countElement && cell;
        
        if (!valid) {
            console.error('Missing elements for', accountId + '-' + month, {
                fileIcon: !!fileIcon,
                dbIcon: !!dbIcon,
                countElement: !!countElement,
                cell: !!cell
            });
        }
        
        return {
            fileIcon: fileIcon,
            dbIcon: dbIcon,
            countElement: countElement,
            cell: cell,
            valid: valid
        };
    },
    
    // Set empty cell state
    setEmptyCell: function(elements) {
        elements.fileIcon.innerHTML = '';
        elements.dbIcon.className = 'database-icon db-not-loaded';
        elements.countElement.textContent = '-';
        elements.cell.className = 'month-cell no-file';
        elements.cell.style.cursor = 'default';
    },
    
    // Set file cell state
    setFileCell: function(elements, accountId, monthData) {
        var accountRow = document.querySelector('[data-account-id="' + accountId + '"]');
        var accountType = accountRow ? accountRow.getAttribute('data-account-type') : 'unknown';
        
        // Set file icon
        this.setFileIcon(elements.fileIcon, accountType, monthData);
        
        // Set parse status
        this.setParseStatus(elements, monthData);
        
        elements.cell.className = 'month-cell';
        elements.cell.style.cursor = 'pointer';
    },
    
    // Set file type icon
    setFileIcon: function(fileIcon, accountType, monthData) {
        var hasExcel = monthData.xlsx && monthData.xlsx !== null;
        var hasPdf = monthData.pdf && monthData.pdf !== null;
        
        var iconHtml = '';
        
        // Show both file types if they exist
        if (hasExcel && hasPdf) {
            // Both files present - show both icons
            iconHtml = '<i class="fas fa-file-excel text-success me-1"></i><i class="fas fa-file-pdf text-danger"></i>';
            console.log('Set both Excel and PDF icons');
        } else if (hasExcel) {
            // Only Excel file
            iconHtml = '<i class="fas fa-file-excel text-success"></i>';
            console.log('Set Excel icon only');
        } else if (hasPdf) {
            // Only PDF file  
            iconHtml = '<i class="fas fa-file-pdf text-danger"></i>';
            console.log('Set PDF icon only');
        } else {
            // No files
            iconHtml = '';
            console.log('No files found');
        }
        
        fileIcon.innerHTML = iconHtml;
    },
    
    // Set parse status
    setParseStatus: function(elements, monthData) {
        var accountRow = elements.cell.closest('[data-account-id]');
        var accountType = accountRow ? accountRow.getAttribute('data-account-type') : 'unknown';
        
        if (accountType === 'stp') console.log('DEBUG monthData:', monthData); // SINGLE DEBUG LINE

        var isParsed = false;
        var totalTransactionCount = 0;
        
        // Get account type to handle STP differently
        var accountRow = elements.cell.closest('[data-account-id]');
        var accountType = accountRow ? accountRow.getAttribute('data-account-type') : 'unknown';
        
        // FIXED: For STP accounts, avoid double-counting transactions
        if (accountType === 'stp') {
            // For STP: Only count XLSX transactions to avoid duplication
            // (PDF inherits the same count but shouldn't be added)
            if (monthData.xlsx && (monthData.xlsx.transaction_count > 0 || monthData.xlsx.parse_status === 'parsed')) {
                isParsed = true;
                totalTransactionCount = monthData.xlsx.transaction_count;
            }
            // Check if PDF is also parsed (for icon status)
            if (monthData.pdf && monthData.pdf.parse_status === 'parsed') {
                isParsed = true;
                // Don't add PDF count for STP - it's the same as XLSX
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
        
        // Also check if there's a transaction count at the root level (fallback)
        if (!isParsed && monthData.transaction_count && monthData.transaction_count > 0) {
            isParsed = true;
            totalTransactionCount = monthData.transaction_count;
        }
        
        elements.dbIcon.className = isParsed ? 'database-icon db-parsed' : 'database-icon db-loaded';
        elements.countElement.textContent = isParsed && totalTransactionCount > 0 ? this.formatCount(totalTransactionCount) : '-';
        
        console.log('Parse status - accountType:', accountType, 'isParsed:', isParsed, 'totalTransactions:', totalTransactionCount);
    },

    // Reset all UI elements
    resetAllUI: function() {
        window.StatementsApp.accountIds.forEach(function(accountId) {
            for (var month = 1; month <= 12; month++) {
                var elements = window.StatementsUI.getMonthElements(accountId, month);
                if (elements.valid) {
                    window.StatementsUI.setEmptyCell(elements);
                }
            }
            
            window.StatementsUI.resetAccountButtons(accountId);
        });
    },
    
    // Reset account action buttons
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
    
    // Show alert message
    showAlert: function(type, message) {
        var alertElement = document.getElementById('statusAlert');
        if (!alertElement) {
            // Create alert element if it doesn't exist
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
    
    // Format transaction count
    formatCount: function(count) {
        if (!count || count === 0) return '-';
        if (count < 1000) return count.toString();
        if (count < 1000000) return (count / 1000).toFixed(1) + 'k';
        return (count / 1000000).toFixed(1) + 'M';
    },
    
    // === UPLOAD UI FUNCTIONS === //
    
    // Show upload progress in modal
    showUploadProgress: function(percentage, status, currentFile) {
        var uploadProgress = document.getElementById('uploadProgress');
        var uploadProgressBar = document.getElementById('uploadProgressBar');
        var uploadStatus = document.getElementById('uploadStatus');
        
        if (!uploadProgress || !uploadProgressBar || !uploadStatus) {
            console.warn('Upload progress elements not found');
            return;
        }
        
        // Show progress section
        uploadProgress.style.display = 'block';
        
        // Update progress bar
        uploadProgressBar.style.width = percentage + '%';
        
        // Update status text
        var statusText = status || 'Processing...';
        if (currentFile) {
            statusText += ' (' + currentFile + ')';
        }
        uploadStatus.textContent = statusText;
        
        // Color coding based on progress
        if (percentage >= 100) {
            uploadProgressBar.classList.add('bg-success');
        } else if (percentage >= 50) {
            uploadProgressBar.classList.add('bg-info');
        }
    },
    
    // Show upload results in modal
    showUploadResults: function(results) {
        var uploadResults = document.getElementById('uploadResults');
        var uploadResultsList = document.getElementById('uploadResultsList');
        
        if (!uploadResults || !uploadResultsList) {
            console.warn('Upload results elements not found');
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
            summaryHtml += '<div class="mt-2">';
            results.results.forEach(function(result) {
                var itemClass = result.success ? 'upload-result-item success' : 'upload-result-item error';
                var iconClass = result.success ? 'fa-check-circle text-success' : 'fa-times-circle text-danger';
                var message = result.success ? 
                    `Uploaded to ${result.account_name || result.account_type || 'account'}` : 
                    `Failed: ${result.error || 'Unknown error'}`;
                    
                summaryHtml += `
                    <div class="${itemClass}">
                        <div class="d-flex justify-content-between align-items-center">
                            <div>
                                <strong>${result.filename || 'Unknown file'}</strong>
                                <small class="text-muted d-block">${message}</small>
                            </div>
                            <i class="fas ${iconClass}"></i>
                        </div>
                    </div>
                `;
            });
            summaryHtml += '</div>';
        }
        
        uploadResultsList.innerHTML = summaryHtml;
        uploadResults.style.display = 'block';
    },
    
    // Update upload button state
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
    
    // Show file preview in upload modal
    showFilePreview: function(files) {
        var selectedFilesSection = document.getElementById('selectedFilesSection');
        var selectedFilesList = document.getElementById('selectedFilesList');
        
        if (!selectedFilesSection || !selectedFilesList) {
            console.warn('File preview elements not found');
            return;
        }
        
        // Clear previous files
        selectedFilesList.innerHTML = '';
        
        if (files.length === 0) {
            selectedFilesSection.style.display = 'none';
            return;
        }
        
        // Process each file
        Array.from(files).forEach(function(file, index) {
            var fileItem = document.createElement('div');
            fileItem.className = 'selected-file-item';
            
            // Validate file
            var validation = window.StatementsUI.validateFile(file);
            
            if (validation.valid) {
                fileItem.classList.add('valid');
            } else {
                fileItem.classList.add('invalid');
            }
            
            // File icon
            var iconClass = 'fa-file';
            var iconColorClass = 'unknown';
            
            if (file.name.toLowerCase().endsWith('.pdf')) {
                iconClass = 'fa-file-pdf';
                iconColorClass = 'pdf';
            } else if (file.name.toLowerCase().match(/\.(xlsx|xls)$/)) {
                iconClass = 'fa-file-excel';
                iconColorClass = 'excel';
            }
            
            fileItem.innerHTML = `
                <div class="d-flex justify-content-between align-items-center">
                    <div class="d-flex align-items-center">
                        <i class="fas ${iconClass} upload-file-icon ${iconColorClass}"></i>
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
                </div>
            `;
            
            selectedFilesList.appendChild(fileItem);
        });
        
        // Show selected files section
        selectedFilesSection.style.display = 'block';
    },
    
    // Validate upload file
    validateFile: function(file) {
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
    },
    
    // Clear upload modal
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
    
    // Handle drag and drop visual feedback
    handleDragFeedback: function(element, state) {
        if (!element) return;
        
        switch (state) {
            case 'enter':
                element.classList.add('drag-over');
                element.classList.remove('btn-outline-primary');
                element.classList.add('btn-outline-success');
                break;
            case 'leave':
                element.classList.remove('drag-over', 'btn-outline-success');
                element.classList.add('btn-outline-primary');
                break;
            case 'drop':
                element.classList.remove('drag-over', 'btn-outline-success');
                element.classList.add('btn-outline-primary');
                break;
        }
    }
};