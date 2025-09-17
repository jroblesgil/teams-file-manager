// API interaction functions - Production Version
window.StatementsAPI = {
    /**
     * Load account data from server
     * @param {string} accountId - Account identifier
     * @returns {Promise} Promise resolving to account data
     */
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
    
    /**
     * Start parse operation for account
     * @param {string} accountId - Account identifier
     * @returns {Promise} Promise resolving to session information
     */
    parseAccount: function(accountId) {
        return new Promise(function(resolve, reject) {
            fetch('/api/statements/parse/' + accountId, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                }
            })
            .then(function(response) {
                if (response.status === 401 || response.status === 403) {
                    window.location.href = '/login';
                    return;
                }
                
                if (!response.ok) {
                    throw new Error('Parse request failed with status ' + response.status + ': ' + response.statusText);
                }
                
                return response.json();
            })
            .then(function(data) {
                if (data.success && data.session_id) {
                    resolve({
                        success: true,
                        session_id: data.session_id,
                        message: data.message || 'Parse operation started'
                    });
                } else {
                    throw new Error(data.error || 'Failed to start parse operation');
                }
            })
            .catch(reject);
        });
    },

    /**
     * Get parse progress using session ID
     * @param {string} sessionId - Parse session identifier
     * @returns {Promise} Promise resolving to progress data
     */
    getParseProgress: function(sessionId) {
        return new Promise(function(resolve, reject) {
            fetch('/api/statements/parse-progress/' + sessionId)
            .then(function(response) {
                if (response.status === 401 || response.status === 403) {
                    window.location.href = '/login';
                    return;
                }
                
                if (!response.ok) {
                    throw new Error('Failed to get progress: HTTP ' + response.status);
                }
                
                return response.json();
            })
            .then(function(data) {
                if (data.success && data.progress) {
                    resolve(data.progress);
                } else {
                    throw new Error(data.error || 'Failed to get parse progress');
                }
            })
            .catch(reject);
        });
    },    

    /**
     * Upload files to server
     * @param {FormData} formData - Form data containing files
     * @returns {Promise} Promise resolving to upload results
     */
    uploadFiles: function(formData) {
        return new Promise(function(resolve, reject) {
            if (!formData) {
                reject(new Error('No form data provided'));
                return;
            }
            
            fetch('/api/statements/upload', {
                method: 'POST',
                body: formData
            })
            .then(function(response) {
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
                if (data.success !== undefined) {
                    resolve(data);
                } else {
                    reject(new Error('Invalid response format from server'));
                }
            })
            .catch(reject);
        });
    },
    
    /**
     * Validate file format before upload
     * @param {string} filename - Filename to validate
     * @returns {Promise} Promise resolving to validation result
     */
    validateFileFormat: function(filename) {
        return new Promise(function(resolve, reject) {
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
                resolve(data);
            })
            .catch(reject);
        });
    },
    
    /**
     * Get supported upload formats
     * @returns {Promise} Promise resolving to supported formats
     */
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
            .catch(reject);
        });
    },
    
    /**
     * Download file from server
     * @param {string} accountId - Account identifier
     * @param {number} month - Month number
     * @param {string} fileType - File type (pdf/xlsx)
     * @param {number} year - Year
     * @returns {Promise} Promise resolving when download starts
     */
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
    },

    /**
     * Get UI data for specific year
     * @param {number} year - Year to load data for
     * @returns {Promise} Promise resolving to UI data
     */
    getUIData: function(year) {
        return new Promise(function(resolve, reject) {
            fetch('/api/statements/ui-data/' + year)
            .then(function(response) {
                if (response.status === 401 || response.status === 403) {
                    window.location.href = '/login';
                    return;
                }
                
                if (!response.ok) {
                    throw new Error('Failed to load UI data: HTTP ' + response.status);
                }
                
                return response.json();
            })
            .then(function(data) {
                if (data.success) {
                    resolve(data);
                } else {
                    reject(new Error(data.error || 'Failed to load UI data'));
                }
            })
            .catch(reject);
        });
    },

    /**
     * Refresh inventory for specific account
     * @param {string} accountId - Account identifier
     * @returns {Promise} Promise resolving to refresh result
     */
    refreshInventory: function(accountId) {
        return new Promise(function(resolve, reject) {
            fetch('/api/statements/refresh-inventory/' + accountId, {
                method: 'POST'
            })
            .then(function(response) {
                if (response.status === 401 || response.status === 403) {
                    window.location.href = '/login';
                    return;
                }
                
                if (!response.ok) {
                    throw new Error('Failed to refresh inventory: HTTP ' + response.status);
                }
                
                return response.json();
            })
            .then(function(data) {
                if (data.success) {
                    resolve(data);
                } else {
                    reject(new Error(data.error || 'Failed to refresh inventory'));
                }
            })
            .catch(reject);
        });
    },

    /**
     * Refresh all account inventories
     * @returns {Promise} Promise resolving to refresh result
     */
    refreshAllInventories: function() {
        return new Promise(function(resolve, reject) {
            fetch('/api/statements/refresh-all-inventories', {
                method: 'POST'
            })
            .then(function(response) {
                if (response.status === 401 || response.status === 403) {
                    window.location.href = '/login';
                    return;
                }
                
                if (!response.ok) {
                    throw new Error('Failed to refresh all inventories: HTTP ' + response.status);
                }
                
                return response.json();
            })
            .then(function(data) {
                if (data.success) {
                    resolve(data);
                } else {
                    reject(new Error(data.error || 'Failed to refresh all inventories'));
                }
            })
            .catch(reject);
        });
    },

    /**
     * Get application health status
     * @returns {Promise} Promise resolving to health status
     */
    getHealthStatus: function() {
        return new Promise(function(resolve, reject) {
            fetch('/api/statements/health')
            .then(function(response) {
                if (!response.ok) {
                    throw new Error('Health check failed: HTTP ' + response.status);
                }
                
                return response.json();
            })
            .then(function(data) {
                resolve(data);
            })
            .catch(reject);
        });
    }
};