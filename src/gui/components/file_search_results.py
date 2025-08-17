"""
Compatibility shim for tests expecting `file_search_results` module.
Re-exports `EnhancedFileSearchResultsWidget` under the expected name.
"""

from .enhanced_file_search_results import EnhancedFileSearchResultsWidget as FileSearchResultsWidget

__all__ = ["FileSearchResultsWidget"]
