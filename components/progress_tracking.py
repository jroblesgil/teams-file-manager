# ============================================================================
# components/progress_tracking.py - Simple progress tracking
# ============================================================================

"""
Progress tracking for unified system (simplified version)
"""

import time
import threading
from datetime import datetime
from typing import Dict, Callable

class ProgressTracker:
    """Simple progress tracking for parse operations"""
    
    def __init__(self):
        self.sessions = {}
        self.cleanup_interval = 300  # 5 minutes
    
    def create_session(self, account_id: str, account_type: str) -> str:
        """Create new progress session"""
        session_id = f"{account_id}_{datetime.now().timestamp()}"
        
        self.sessions[session_id] = {
            'status': 'initializing',
            'account_id': account_id,
            'account_type': account_type,
            'progress_percentage': 0,
            'current_file': None,
            'files_processed': 0,
            'total_files': 0,
            'transactions_added': 0,
            'errors': [],
            'start_time': datetime.now().isoformat(),
            'last_update': datetime.now().isoformat()
        }
        
        # Schedule cleanup
        cleanup_timer = threading.Timer(self.cleanup_interval, self._cleanup_session, [session_id])
        cleanup_timer.daemon = True
        cleanup_timer.start()
        
        return session_id
    
    def update_session(self, session_id: str, progress_data: Dict):
        """Update progress session"""
        if session_id in self.sessions:
            self.sessions[session_id].update(progress_data)
            self.sessions[session_id]['last_update'] = datetime.now().isoformat()
    
    def get_session(self, session_id: str) -> Dict:
        """Get progress session data"""
        return self.sessions.get(session_id, {})
    
    def _cleanup_session(self, session_id: str):
        """Clean up expired session"""
        if session_id in self.sessions:
            del self.sessions[session_id]

# Global progress tracker instance
progress_tracker = ProgressTracker()