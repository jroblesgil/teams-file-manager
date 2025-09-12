# ============================================================================
# components/cache.py - Reuse caching system
# ============================================================================

"""
Caching components reused from existing system
"""

from modules.shared.performance_cache import unified_cache

class UnifiedCacheManager:
    """Centralized cache management for unified system"""
    
    @staticmethod
    def clear_cache(pattern=None):
        """Clear cache entries"""
        if pattern:
            unified_cache.invalidate_pattern(pattern)
        else:
            unified_cache.cache.clear()
    
    @staticmethod
    def get_cache_stats():
        """Get cache statistics"""
        return {
            'total_entries': len(unified_cache.cache),
            'cache_keys': list(unified_cache.cache.keys())
        }
    
    @staticmethod
    def warm_cache(access_token, year):
        """Warm cache for performance"""
        from modules.shared.performance_cache import warm_cache_for_user
        return warm_cache_for_user(access_token, year)
