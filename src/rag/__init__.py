"""RAG package initializer (lightweight).

Avoids eager re-exports to prevent import-time side effects and reduce
the risk of circular imports. Import submodules directly, e.g.:

    from src.rag.vector_search import VectorSearchEngine
    from src.rag.file_processor import FileProcessor

"""

__all__: list[str] = []
__version__ = '1.0.0'