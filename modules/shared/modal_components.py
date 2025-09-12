# modules/shared/modal_components.py
"""
Shared modal components for progress tracking and reviews
"""

class ModalManager:
    """Manages modal states and data for both systems"""
    
    @staticmethod
    def get_progress_modal_data(operation_type: str, account_type: str = None) -> Dict:
        """Get data structure for progress modal"""
        return {
            'operation': operation_type,  # 'parse', 'export', 'upload'
            'account': account_type,
            'status': 'initializing',  # 'initializing', 'processing', 'complete', 'error'
            'progress': 0,
            'current_file': '',
            'total_files': 0,
            'processed_files': 0,
            'messages': [],
            'errors': [],
            'results': {}
        }
    
    @staticmethod
    def get_review_modal_data(account_type: str, month_data: Dict) -> Dict:
        """Get data structure for review modal"""
        return {
            'account': account_type,
            'month': month_data.get('month'),
            'year': month_data.get('year'),
            'transactions': [],
            'summary': {
                'total_transactions': 0,
                'total_cargos': 0.0,
                'total_abonos': 0.0,
                'date_range': {'start': None, 'end': None}
            },
            'filters': {
                'date_from': '',
                'date_to': '',
                'min_amount': '',
                'max_amount': '',
                'description_filter': ''
            }
        }
