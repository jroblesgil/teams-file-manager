// Download functionality for statement files
window.Downloads = {
    
    // Handle month cell click for file download
    handleMonthClick: function(accountId, month) {
        var app = window.StatementsApp;
        
        // Check if account data is loaded
        if (!app.accountDataByYear[app.currentYear] || !app.accountDataByYear[app.currentYear][accountId]) {
            window.StatementsUI.showAlert('warning', 'Please load account data first');
            return;
        }
        
        var monthKey = app.currentYear + '-' + (month < 10 ? '0' + month : month);
        var accountData = app.accountDataByYear[app.currentYear][accountId];
        var monthData = accountData.months[monthKey];
        
        if (!monthData || monthData.status === 'missing' || monthData.file_count === 0) {
            window.StatementsUI.showAlert('info', 'No files available for this month');
            return;
        }
        
        var hasExcel = monthData.xlsx && monthData.xlsx !== null;
        var hasPdf = monthData.pdf && monthData.pdf !== null;
        
        // If both files exist, show selection modal
        if (hasExcel && hasPdf) {
            window.Modals.showFileSelection(accountId, month, monthData);
        } else if (hasExcel) {
            this.downloadFile(accountId, month, 'xlsx');
        } else if (hasPdf) {
            this.downloadFile(accountId, month, 'pdf');
        } else {
            window.StatementsUI.showAlert('info', 'No files available for download');
        }
    },
    
    // Download specific file
    downloadFile: function(accountId, month, fileType) {
        // Construct download URL
        var downloadUrl = `/api/statements/download-file/${accountId}/${month}/${fileType}?year=${window.StatementsApp.currentYear}`;
        
        // Show loading state
        window.StatementsUI.showAlert('info', 'Preparing download...');
        
        // Create hidden link and trigger download
        var link = document.createElement('a');
        link.href = downloadUrl;
        link.download = `${accountId}_${window.StatementsApp.currentYear}_${month.toString().padStart(2, '0')}.${fileType}`;
        link.style.display = 'none';
        
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        
        // Show success message after a brief delay
        setTimeout(function() {
            window.StatementsUI.showAlert('success', `${fileType.toUpperCase()} file download started`);
        }, 500);
    }
};