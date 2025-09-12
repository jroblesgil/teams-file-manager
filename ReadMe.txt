# Teams File Manager

A professional web application for Microsoft Teams file management and analysis, built with Flask and modern web technologies.

## 🚀 Features

### Core Functionality
- ✅ **SharePoint Link Downloads** - Direct file downloads from SharePoint URLs
- ✅ **Microsoft Authentication** - Secure OAuth integration with Azure AD
- ✅ **File Browser** - Browse team files with search and filter capabilities
- ✅ **Professional UI** - Modern, responsive design with Bootstrap

### Analysis Features (Coming Soon)
- 📊 **Excel Data Analysis** - Comprehensive analysis of financial data
- 📈 **Data Visualization** - Interactive charts and graphs
- 🔍 **Financial Metrics** - Automated calculation of key financial indicators
- 📋 **Report Generation** - Professional analysis reports

## 🏗️ Architecture

```
teams-file-manager/
├── app.py                 # Main Flask application
├── config.py             # Configuration management
├── modules/              # Core business logic
│   ├── auth.py          # Authentication handling
│   ├── teams_api.py     # Microsoft Graph API integration
│   └── analysis.py      # Data analysis engine
├── templates/           # Jinja2 HTML templates
├── static/             # CSS, JS, and static assets
└── tests/              # Unit and integration tests
```

## 🛠️ Setup Instructions

### Prerequisites
- Python 3.8 or higher
- Microsoft Azure App Registration
- Access to Microsoft Teams/SharePoint

### 1. Clone Repository
```bash
git clone <repository-url>
cd teams-file-manager
```

### 2. Create Virtual Environment
```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS/Linux
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure Environment
Create `.env` file in the project root:
```env
# Azure Configuration
AZURE_CLIENT_ID=your_client_id_here
AZURE_TENANT_ID=your_tenant_id_here

# Flask Configuration
SECRET_KEY=your_secret_key_here
FLASK_ENV=development

# Optional: Database Configuration
DATABASE_URL=sqlite:///app.db
```

### 5. Azure App Registration Setup

1. **Go to Azure Portal** → **App registrations** → **New registration**

2. **Configure App:**
   - Name: `Teams File Manager`
   - Supported account types: `Accounts in this organizational directory only`
   - Redirect URI: `http://localhost:5000` (for development)

3. **Add API Permissions:**
   - Microsoft Graph (Delegated):
     - `User.Read`
     - `Files.Read.All`
     - `Sites.Read.All`
     - `Group.Read.All`

4. **Grant Admin Consent** for the permissions

5. **Copy Client ID and Tenant ID** to your `.env` file

### 6. Run Application
```bash
python app.py
```

Navigate to `http://localhost:5000`

## 🔧 Configuration

### Environment Variables
| Variable | Description | Required |
|----------|-------------|----------|
| `AZURE_CLIENT_ID` | Azure App Registration Client ID | ✅ |
| `AZURE_TENANT_ID` | Azure Tenant ID | ✅ |
| `SECRET_KEY` | Flask secret key for sessions | ✅ |
| `FLASK_ENV` | Environment (development/production) | ❌ |
| `PORT` | Application port (default: 5000) | ❌ |

### Teams Configuration
Update `config.py` with your specific Teams settings:
```python
TEAM_ID = 'your-team-id-here'  # Microsoft Teams Group ID
```

## 📊 Usage

### File Downloads
1. **Sign in** with your Microsoft account
2. **Paste SharePoint URL** in the download section
3. **Click Download** - file will be saved to your Downloads folder

### File Analysis (Coming Soon)
1. **Upload Excel/CSV file** in the Analysis section
2. **View automated insights** and metrics
3. **Export analysis reports**

## 🧪 Testing

Run the test suite:
```bash
python -m pytest tests/
```

Run with coverage:
```bash
python -m pytest tests/ --cov=modules --cov-report=html
```

## 🚀 Deployment

### Production Setup
1. **Set environment variables:**
   ```bash
   export FLASK_ENV=production
   export SECRET_KEY=production-secret-key
   ```

2. **Use production WSGI server:**
   ```bash
   gunicorn -w 4 -b 0.0.0.0:5000 app:app
   ```

### Docker Deployment
```dockerfile
FROM python:3.9-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:5000", "app:app"]
```

## 🔒 Security

- **OAuth 2.0** authentication with Microsoft
- **Session management** with secure cookies
- **CSRF protection** for form submissions
- **Input validation** for all user inputs
- **Secure file handling** with type validation

## 🤝 Contributing

1. **Fork the repository**
2. **Create feature branch:** `git checkout -b feature-name`
3. **Commit changes:** `git commit -am 'Add feature'`
4. **Push to branch:** `git push origin feature-name`
5. **Submit pull request**

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Support

### Common Issues

**Authentication Errors:**
- Verify Azure app registration settings
- Check redirect URI matches exactly
- Ensure admin consent is granted

**File Download Issues:**
- Verify SharePoint URL format
- Check file permissions
- Ensure user has access to the file

**Analysis Issues:**
- Verify file format (Excel/CSV)
- Check file size limits
- Ensure pandas dependencies are installed

### Getting Help
- **Documentation:** Check the `docs/` folder for detailed guides
- **Issues:** Create an issue on GitHub with error details
- **Discussions:** Use GitHub Discussions for questions

---

**Built with ❤️ for efficient Teams file management**