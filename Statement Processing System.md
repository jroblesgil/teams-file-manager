# Bank Statement Processing System

A comprehensive web application for processing and managing bank statements from multiple financial institutions, with automated parsing, SharePoint integration, and transaction extraction capabilities.

## Overview

This system streamlines the processing of bank statements from STP (Santander) and BBVA accounts by providing:

- **Multi-format file support**: PDF and Excel statement processing
- **Automated parsing**: Extract transactions from statements automatically
- **Calendar interface**: Visual overview of available statements by month
- **SharePoint integration**: Direct upload to Microsoft Teams/SharePoint
- **Real-time progress tracking**: Monitor parsing and upload operations
- **Multi-account management**: Handle multiple bank accounts simultaneously

## Architecture

### Frontend
- **HTML5/CSS3** with Bootstrap 5 for responsive design
- **Vanilla JavaScript** with modular architecture
- **Real-time UI updates** via polling and WebSocket-style progress tracking
- **Modal-based interactions** for uploads, file selection, and progress display

### Backend
- **RESTful API** for all operations
- **Session-based progress tracking** for long-running operations
- **File processing pipeline** with validation and parsing
- **Database integration** for transaction storage and tracking

### External Integrations
- **Microsoft SharePoint/Teams** for file storage and collaboration
- **Multi-bank API support** for statement retrieval and validation

## Supported Account Types

### STP (Santander) Accounts
- **STP SA**: Santander savings account
- **STP IP - PD**: Investment portfolio - Personal Development
- **STP IP - PI**: Investment portfolio - Personal Investment

**File Format**: `ec-[18-digit-account]-YYYYMM.[pdf|xlsx]`

### BBVA Accounts
- **BBVA MX MXN/USD**: Mexico accounts (Pesos/Dollars)
- **BBVA SA MXN/USD**: Servicios Administrativos (Pesos/Dollars)
- **BBVA IP Corp/Clientes**: Investment portfolios

**File Format**: `YYMM [Account Name].pdf` or auto-detected PDF files

## Key Features

### File Upload System
- **Drag-and-drop interface** with visual feedback
- **File validation** with format and size checks
- **Multi-file batch uploads** with progress tracking
- **Automatic account detection** based on filename patterns

### Statement Calendar
- **Monthly grid view** showing file availability and transaction counts
- **Visual indicators** for file types (PDF/Excel) and parsing status
- **One-click downloads** with automatic file type selection
- **Year navigation** with dynamic data loading

### Parsing Operations
- **Automated transaction extraction** from PDF and Excel files
- **Duplicate detection** and smart file skipping
- **Progress monitoring** with detailed status updates
- **Error handling** with comprehensive reporting

### Real-time Progress Tracking
- **Session-based operations** for parse and upload tracking
- **Live progress updates** with percentage completion
- **File-by-file status** showing current processing
- **Success/failure reporting** with detailed results

## Installation

### Prerequisites
```bash
# Backend dependencies (adjust based on your stack)
python >= 3.8  # or Node.js >= 14
database system (PostgreSQL/MySQL/SQLite)
```

### Setup
```bash
# Clone repository
git clone [repository-url]
cd bank-statement-processor

# Install dependencies
# [Add your specific installation commands]

# Configure environment
cp .env.example .env
# Edit .env with your configuration

# Database setup
# [Add your database setup commands]

# Start application
# [Add your start commands]
```

### Environment Configuration
```env
# SharePoint Integration
SHAREPOINT_CLIENT_ID=your_client_id
SHAREPOINT_CLIENT_SECRET=your_client_secret
SHAREPOINT_TENANT_ID=your_tenant_id

# Database Configuration
DATABASE_URL=your_database_url

# Application Settings
DEBUG=false
LOG_LEVEL=info
MAX_FILE_SIZE=50MB
```

## API Documentation

### Core Endpoints

#### File Upload
```http
POST /api/statements/upload
Content-Type: multipart/form-data

Parameters:
- files: Array of statement files

Response:
{
  "success": true,
  "total_files": 3,
  "successful_uploads": 3,
  "failed_uploads": 0,
  "results": [...]
}
```

#### Parse Account
```http
POST /api/statements/parse/{account_id}

Response:
{
  "success": true,
  "session_id": "parse_session_id",
  "message": "Parse operation started"
}
```

#### Progress Tracking
```http
GET /api/statements/progress/{session_id}

Response:
{
  "status": "in_progress",
  "progress_percentage": 45,
  "files_processed": 2,
  "total_files": 5,
  "current_file": "statement.pdf",
  "details": "Processing transactions..."
}
```

#### Account Data
```http
GET /api/statements/ui-data/{year}
GET /api/statements/load-account/{account_id}

Response:
{
  "success": true,
  "ui_data": {
    "account_id": {
      "months": [...],
      "total_files": 12,
      "total_transactions": 450
    }
  }
}
```

### File Download
```http
GET /statements/download/{account_id}/{month}/{file_type}?year={year}

Parameters:
- account_id: Account identifier
- month: Month number (1-12)
- file_type: 'pdf' or 'xlsx'
- year: Target year
```

## Usage Guide

### Uploading Files

1. **Click "Upload to Teams"** button to open upload modal
2. **Drag files** onto drop zone or click to browse
3. **Validate files** - system checks format and naming
4. **Monitor progress** - real-time upload status
5. **Review results** - see success/failure for each file

### Parsing Statements

1. **Load account data** using the sync button for each account
2. **Click parse button** when files are available
3. **Monitor progress** - parsing status and file processing
4. **Review results** - transaction counts and any errors

### Downloading Statements

1. **Navigate to desired month** in the calendar
2. **Click on file icons** to download
3. **Select file type** for STP accounts (PDF/Excel choice)
4. **Automatic download** for BBVA accounts (PDF priority)

## File Processing Logic

### STP File Processing
```javascript
// File naming pattern
ec-123456789012345678-202501.pdf
ec-123456789012345678-202501.xlsx

// Processing priority
1. If both PDF and Excel exist → Show selection modal
2. If only one type exists → Direct download
3. Excel files contain detailed transaction data
4. PDF files are official bank statements
```

### BBVA File Processing
```javascript
// File naming patterns
2501 BBVA Account Name.pdf
auto-detected-statement.pdf

// Processing priority
1. Always prefer PDF files
2. Auto-detect account from content if naming unclear
3. Extract transactions using PDF parsing
4. Store with standardized naming
```

### Parse Tracking System
```javascript
// Parse session lifecycle
1. Initiate parse → Generate session ID
2. Track progress → File-by-file processing
3. Skip duplicates → Check modification dates
4. Extract transactions → Store in database
5. Complete session → Return results
```

## Error Handling

### Common Upload Errors
- **Invalid file format**: Only PDF, XLSX, XLS allowed
- **File size exceeded**: Maximum 50MB per file
- **Naming pattern mismatch**: Files must follow expected patterns
- **SharePoint connection failed**: Check authentication

### Common Parse Errors
- **File not found**: Statement file missing from SharePoint
- **Parse failed**: Corrupted or unreadable file content
- **Database error**: Transaction storage issues
- **Duplicate detection**: File already processed

### Troubleshooting
```bash
# Check backend logs
tail -f logs/application.log

# Verify SharePoint connection
curl -X GET /api/health/sharepoint

# Test file upload
curl -X POST /api/statements/debug-upload

# Clear parse cache
DELETE /api/statements/cache/{account_id}
```

## Development

### File Structure
```
/
├── frontend/
│   ├── templates/
│   │   └── statements_table.html
│   ├── static/
│   │   ├── js/
│   │   │   ├── main.js
│   │   │   ├── api.js
│   │   │   └── ui.js
│   │   └── css/
│   └── uploads/
├── backend/
│   ├── api/
│   ├── parsers/
│   ├── database/
│   └── integrations/
└── docs/
```

### Adding New Account Types

1. **Define account configuration**
```javascript
const newAccountConfig = {
  id: 'new_bank_account',
  name: 'New Bank Account',
  type: 'new_bank',
  file_pattern: /^pattern-.*\.pdf$/,
  parser_class: 'NewBankParser'
};
```

2. **Implement parser class**
3. **Add UI configuration**
4. **Update account mappings**
5. **Test with sample files**

### Running Tests
```bash
# Frontend tests
npm test

# Backend tests
python -m pytest

# Integration tests
npm run test:integration
```

## Production Deployment

### Pre-deployment Checklist
- [ ] Remove all debug logging and console.log statements
- [ ] Set environment variables for production
- [ ] Configure secure SharePoint authentication
- [ ] Set up database backups
- [ ] Configure monitoring and alerting
- [ ] Test all account types with real data
- [ ] Verify file upload size limits
- [ ] Check error handling for edge cases

### Monitoring
- **Application health**: Monitor API response times
- **File processing**: Track parse success rates
- **SharePoint integration**: Monitor upload failures
- **Database performance**: Track query times
- **Error rates**: Alert on unusual error patterns

### Backup Strategy
- **Database backups**: Daily automated backups
- **File storage**: SharePoint provides built-in redundancy
- **Configuration**: Version control for all settings
- **Recovery procedures**: Documented restoration steps

## Security Considerations

### Data Protection
- **File validation**: Strict format and content checking
- **Authentication**: Secure SharePoint integration
- **Input sanitization**: All user inputs validated
- **Session management**: Secure session handling

### Access Control
- **Role-based permissions**: Different access levels
- **Account isolation**: Users only access authorized accounts
- **Audit logging**: Track all significant operations
- **File access**: Controlled download permissions

## Support and Maintenance

### Regular Maintenance
- **Log rotation**: Prevent disk space issues
- **Database optimization**: Regular index maintenance
- **Cache cleanup**: Clear old session data
- **Security updates**: Keep dependencies current

### Common Issues
- **SharePoint authentication expiry**: Refresh tokens periodically
- **Parse failures**: Usually due to file format changes
- **Upload timeouts**: Check file sizes and network
- **UI freezing**: Clear browser cache and cookies

## License

[Add your license information]

## Contributing

[Add contribution guidelines if applicable]

## Changelog

### Version 1.0.0 (Production Release)
- Initial production release
- Support for STP and BBVA accounts
- Complete parsing and upload functionality
- Real-time progress tracking
- Comprehensive error handling