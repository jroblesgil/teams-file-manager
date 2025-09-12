"""
STP Helpers Module

Utility functions for formatting, validation, and common operations.
"""

import math
from datetime import datetime
from typing import Optional


def get_account_type(account_number: str) -> str:
    """Get account type description"""
    account_types = {
        '646180559700000009': 'STP SA',
        '646990403000000003': 'STP IP - PI', 
        '646180403000000004': 'STP IP - PD'
    }
    return account_types.get(account_number, 'Unknown Account')


def get_file_type(extension: str) -> str:
    """Get human-readable file type"""
    file_types = {
        'pdf': 'PDF Document',
        'xlsx': 'Excel Spreadsheet'
    }
    return file_types.get(extension.lower(), f'{extension.upper()} File')


def format_file_size(size_bytes: int) -> str:
    """Format file size in human readable format"""
    if size_bytes == 0:
        return "0 B"
    
    size_names = ["B", "KB", "MB", "GB", "TB"]
    i = int(math.floor(math.log(size_bytes, 1024)))
    p = math.pow(1024, i)
    s = round(size_bytes / p, 2)
    return f"{s} {size_names[i]}"


def format_datetime(iso_datetime: Optional[str]) -> Optional[str]:
    """Format ISO datetime to readable format"""
    if not iso_datetime:
        return None
    
    try:
        dt = datetime.fromisoformat(iso_datetime.replace('Z', '+00:00'))
        return dt.strftime('%Y-%m-%d %H:%M:%S')
    except:
        return iso_datetime


def get_month_name(month_num: int) -> str:
    """Get month name from number"""
    months = [
        '', 'January', 'February', 'March', 'April', 'May', 'June',
        'July', 'August', 'September', 'October', 'November', 'December'
    ]
    return months[month_num] if 1 <= month_num <= 12 else ''


def validate_account_number(account_number: str) -> bool:
    """Validate if account number is valid for STP processing"""
    valid_accounts = ['646180559700000009', '646990403000000003', '646180403000000004']
    return account_number in valid_accounts


def validate_file_format(filename: str) -> dict:
    """Validate STP file format and extract metadata"""
    import re
    
    # Expected pattern: ec-[18-digit-account]-YYYYMM.ext
    pattern = r'^ec-(\d{18})-(\d{4})(\d{2})\.(pdf|xlsx|xls)$'
    match = re.match(pattern, filename, re.IGNORECASE)
    
    if not match:
        return {
            'valid': False,
            'error': 'Invalid filename format. Expected: ec-[account]-YYYYMM.ext'
        }
    
    account, year, month, extension = match.groups()
    
    # Validate account number
    if not validate_account_number(account):
        return {
            'valid': False,
            'error': f'Invalid account number: {account}'
        }
    
    # Validate month
    month_num = int(month)
    if month_num < 1 or month_num > 12:
        return {
            'valid': False,
            'error': f'Invalid month: {month}. Must be 01-12.'
        }
    
    # Validate year (reasonable range)
    year_num = int(year)
    current_year = datetime.now().year
    if year_num < 2020 or year_num > current_year + 1:
        return {
            'valid': False,
            'error': f'Invalid year: {year}. Must be between 2020 and {current_year + 1}.'
        }
    
    return {
        'valid': True,
        'account': account,
        'year': year,
        'month': month,
        'extension': extension.lower(),
        'account_type': get_account_type(account)
    }


def format_currency(amount: float, currency: str = 'MXN') -> str:
    """Format amount as currency"""
    if amount is None:
        return ''
    
    try:
        if currency == 'MXN':
            return f"${amount:,.2f} MXN"
        else:
            return f"{amount:,.2f} {currency}"
    except (ValueError, TypeError):
        return str(amount)


def sanitize_filename(filename: str) -> str:
    """Sanitize filename for safe file operations"""
    import re
    
    # Remove or replace invalid characters
    filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
    
    # Remove leading/trailing spaces and dots
    filename = filename.strip(' .')
    
    # Limit length
    if len(filename) > 255:
        name, ext = filename.rsplit('.', 1) if '.' in filename else (filename, '')
        max_name_length = 255 - len(ext) - 1 if ext else 255
        filename = name[:max_name_length] + ('.' + ext if ext else '')
    
    return filename


def get_account_folder_mapping() -> dict:
    """Get mapping of account numbers to SharePoint folder names"""
    from collections import OrderedDict

    return OrderedDict([
        ('646180559700000009', 'STP SA New'),
        ('646990403000000003', 'STP IP'),
        ('646180403000000004', 'STP IP')
    ])


def is_excel_file(filename: str) -> bool:
    """Check if file is an Excel file"""
    excel_extensions = ['.xlsx', '.xls']
    return any(filename.lower().endswith(ext) for ext in excel_extensions)


def is_pdf_file(filename: str) -> bool:
    """Check if file is a PDF file"""
    return filename.lower().endswith('.pdf')


def extract_year_month_from_filename(filename: str) -> tuple:
    """Extract year and month from STP filename"""
    import re
    
    pattern = r'ec-\d{18}-(\d{4})(\d{2})\.'
    match = re.search(pattern, filename)
    
    if match:
        year = int(match.group(1))
        month = int(match.group(2))
        return year, month
    
    return None, None


def create_month_key(year: int, month: int) -> str:
    """Create standardized month key for data organization"""
    return f"{year}-{month:02d}"


def parse_month_key(month_key: str) -> tuple:
    """Parse month key back to year and month"""
    try:
        parts = month_key.split('-')
        if len(parts) == 2:
            year = int(parts[0])
            month = int(parts[1])
            return year, month
        return None, None
    except (ValueError, IndexError):
        return None, None


def get_sharepoint_drive_config() -> dict:
    """Get SharePoint drive configuration"""
    return {
        'drive_id': "b!q3bruib_D0WIZS7yprZMBAUi_U53mb1KkFHHY5SmVTuIet9KaCuESqLv_QwsGcVu",
        'bancos_folder_id': "01YH7LZSZL4O2ZOMG4RVH2Y7NLUTM5M33V"
    }