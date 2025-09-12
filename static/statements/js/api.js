// API interaction functions
window.StatementsAPI = {
    // Load account data from server
    loadAccount: function(accountId) {
        return new Promise(function(resolve, reject) {
            var apiUrl = '/api/statements/load-account-data/' + accountId + '?year=' + window.StatementsApp.currentYear;
            
            fetch(apiUrl)
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
                    if (data.error && (data.error.includes('auth') || data.error.includes('login'))) {
                        window.location.href = '/login';
                        return;
                    }
                    
                    if (data.success && data.account_data) {
                        resolve(data.account_data);
                    } else {
                        reject(new Error(data.error || 'Failed to load account data'));
                    }
                })
                .catch(reject);
        });
    },
    
    // Parse account row
    parseAccount: function(accountId) {
        // TODO: Implement parsing API call
        console.log('Parse account:', accountId);
    },
    
    // Upload files to Teams
    uploadFiles: function(files) {
        // TODO: Implement upload API call
        console.log('Upload files:', files);
    },
    
    // Download file
    downloadFile: function(accountId, month, fileType, year) {
        return new Promise(function(resolve, reject) {
            var downloadUrl = '/api/statements/download-file/' + accountId + '/' + month + '/' + fileType + '?year=' + year;
            
            fetch(downloadUrl)
                .then(function(response) {
                    if (response.status === 401 || response.status === 403) {
                        window.location.href = '/login';
                        return;
                    }
                    if (!response.ok) {
                        throw new Error('HTTP ' + response.status + ': ' + response.statusText);
                    }
                    return response.blob();
                })
                .then(function(blob) {
                    // Create download link
                    var url = window.URL.createObjectURL(blob);
                    var link = document.createElement('a');
                    link.href = url;
                    link.download = accountId + '_' + year + '_' + month.toString().padStart(2, '0') + '.' + fileType;
                    document.body.appendChild(link);
                    link.click();
                    document.body.removeChild(link);
                    window.URL.revokeObjectURL(url);
                    resolve();
                })
                .catch(reject);
        });
    }
};