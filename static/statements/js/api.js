// API interaction functions with upload implementation
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
    
    // UPLOAD FUNCTIONALITY - IMPLEMENTED
    uploadFiles: function(formData) {
        return new Promise(function(resolve, reject) {
            console.log('=== API UPLOAD STARTED ===');
            
            if (!formData) {
                reject(new Error('No form data provided'));
                return;
            }
            
            console.log('Uploading to /api/statements/upload...');
            
            fetch('/api/statements/upload', {
                method: 'POST',
                body: formData
                // Don't set Content-Type header - let browser set it with boundary for multipart/form-data
            })
            .then(function(response) {
                console.log('Upload response status:', response.status);
                
                // Handle authentication errors
                if (response.status === 401 || response.status === 403) {
                    window.location.href = '/login';
                    return;
                }
                
                if (!response.ok) {
                    throw new Error('Upload failed with status ' + response.status + ': ' + response.statusText);
                }
                
                return response.json();
            })
            .then(function(data) {
                console.log('Upload response data:', data);
                
                if (data.success !== undefined) {
                    // Valid response format
                    resolve(data);
                } else {
                    // Unexpected response format
                    reject(new Error('Invalid response format from server'));
                }
            })
            .catch(function(error) {
                console.error('Upload API error:', error);
                reject(error);
            });
        });
    },
    
    // Validate file format before upload
    validateFileFormat: function(filename) {
        return new Promise(function(resolve, reject) {
            console.log('Validating file format for:', filename);
            
            fetch('/api/statements/upload/validate', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    filename: filename
                })
            })
            .then(function(response) {
                if (response.status === 401 || response.status === 403) {
                    window.location.href = '/login';
                    return;
                }
                
                if (!response.ok) {
                    throw new Error('Validation failed with status ' + response.status);
                }
                
                return response.json();
            })
            .then(function(data) {
                console.log('Validation result:', data);
                resolve(data);
            })
            .catch(function(error) {
                console.error('Validation error:', error);
                reject(error);
            });
        });
    },
    
    // Get supported upload formats
    getSupportedFormats: function() {
        return new Promise(function(resolve, reject) {
            fetch('/api/statements/upload/formats')
            .then(function(response) {
                if (response.status === 401 || response.status === 403) {
                    window.location.href = '/login';
                    return;
                }
                
                if (!response.ok) {
                    throw new Error('Failed to get formats with status ' + response.status);
                }
                
                return response.json();
            })
            .then(function(data) {
                resolve(data);
            })
            .catch(function(error) {
                console.error('Get formats error:', error);
                reject(error);
            });
        });
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