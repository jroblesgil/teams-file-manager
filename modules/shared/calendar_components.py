"""
Shared calendar grid logic for both STP and BBVA systems
"""

import calendar
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional

class CalendarManager:
    """Manages calendar grid logic for both STP and BBVA systems"""
    
    def __init__(self, system_type: str = "bbva"):
        self.system_type = system_type  # "stp" or "bbva"
        self.current_year = datetime.now().year
        
    def get_month_data(self, year: int, month: int) -> Dict:
        """Get calendar data for a specific month"""
        cal = calendar.Calendar(firstweekday=0)  # Monday = 0
        month_days = list(cal.itermonthdays(year, month))
        
        # Group days into weeks
        weeks = []
        week = []
        for day in month_days:
            week.append(day)
            if len(week) == 7:
                weeks.append(week)
                week = []
        
        return {
            'year': year,
            'month': month,
            'month_name': calendar.month_name[month],
            'weeks': weeks,
            'total_days': calendar.monthrange(year, month)[1]
        }
    
    def get_year_overview(self, year: int) -> List[Dict]:
        """Get overview data for all months in a year"""
        months = []
        for month in range(1, 13):
            month_data = self.get_month_data(year, month)
            months.append(month_data)
        return months
    
    def get_status_summary(self, account_data: Dict, year: int, month: int) -> Dict:
        """Get status summary for a specific month"""
        # This will be implemented based on database data
        return {
            'total_files': 0,
            'parsed_files': 0,
            'unparsed_files': 0,
            'missing_files': 0,
            'total_transactions': 0,
            'status': 'missing'  # 'complete', 'partial', 'missing'
        }
