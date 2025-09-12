# ============================================================================
# components/parsers.py - Reuse parsing logic
# ============================================================================

"""
Parsing components reused from existing system
"""

from modules.stp.stp_parser import parse_excel_file
from modules.bbva.bbva_parser import BBVAParser

class UnifiedParsingManager:
    """Centralized parsing for unified system"""
    
    def __init__(self):
        self.bbva_parser = BBVAParser()
    
    def parse_stp_file(self, file_content, filename):
        """Parse STP Excel file"""
        return parse_excel_file(file_content, filename)
    
    def parse_bbva_file(self, file_path):
        """Parse BBVA PDF file"""
        return self.bbva_parser.parse_pdf(file_path)
