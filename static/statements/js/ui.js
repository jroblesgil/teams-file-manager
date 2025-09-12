// UI manipulation functions
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
        var isParsed = false;
        var totalTransactionCount = 0;
        
        // Count transactions from both Excel and PDF if they exist
        if (monthData.xlsx && monthData.xlsx.transaction_count) {
            isParsed = true;
            totalTransactionCount += monthData.xlsx.transaction_count;
        }
        
        if (monthData.pdf && monthData.pdf.transaction_count) {
            isParsed = true;
            totalTransactionCount += monthData.pdf.transaction_count;
        }
        
        elements.dbIcon.className = isParsed ? 'database-icon db-parsed' : 'database-icon db-loaded';
        elements.countElement.textContent = isParsed && totalTransactionCount > 0 ? this.formatCount(totalTransactionCount) : '-';
        
        console.log('Parse status - isParsed:', isParsed, 'totalTransactions:', totalTransactionCount);
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
        if (!alertElement) return;
        
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
    }
};