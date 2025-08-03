"""
Embedding generation module for DinoAir 2.0 RAG File Search system.
Provides local vector embedding generation using sentence-transformers.
"""

import os
import numpy as np
from typing import List, Optional, Dict, Any
from functools import lru_cache
import torch

# Import logging from DinoAir's logger
from ..utils.logger import Logger


class EmbeddingGenerator:
    """
    Generates vector embeddings for text using sentence-transformers.
    Uses the lightweight 'all-MiniLM-L6-v2' model for local processing.
    """
    
    # Default model configuration
    DEFAULT_MODEL = 'all-MiniLM-L6-v2'  # ~80MB, 384-dimensional embeddings
    DEFAULT_MAX_LENGTH = 256  # Maximum sequence length for the model
    DEFAULT_BATCH_SIZE = 32  # Default batch size for processing
    
    # Model cache directory
    MODEL_CACHE_DIR = os.path.join(
        os.path.expanduser('~'), '.dinoair', 'models', 'embeddings'
    )
    
    def __init__(self, model_name: Optional[str] = None,
                 max_length: Optional[int] = None,
                 device: Optional[str] = None):
        """
        Initialize the EmbeddingGenerator.
        
        Args:
            model_name: Name of the sentence-transformers model to use
            max_length: Maximum sequence length for input text
            device: Device to use ('cuda', 'cpu', or None for auto-detect)
        """
        self.logger = Logger()
        self.model_name = model_name or self.DEFAULT_MODEL
        self.max_length = max_length or self.DEFAULT_MAX_LENGTH
        
        # Device selection
        if device:
            self.device = device
        else:
            # Auto-detect device
            if torch.cuda.is_available():
                self.device = 'cuda'
                self.logger.info("CUDA available, using GPU for embeddings")
            else:
                self.device = 'cpu'
                self.logger.info("Using CPU for embeddings")
        
        # Initialize model as None (lazy loading)
        self._model = None
        
        # Create cache directory if it doesn't exist
        os.makedirs(self.MODEL_CACHE_DIR, exist_ok=True)
        
        self.logger.info(
            f"EmbeddingGenerator initialized with model={self.model_name}, "
            f"max_length={self.max_length}, device={self.device}"
        )
    
    @property
    def model(self):
        """
        Lazy load the model on first use.
        This helps with memory management and startup time.
        """
        if self._model is None:
            self._load_model()
        return self._model
    
    def _load_model(self):
        """
        Load the sentence-transformers model with caching.
        """
        try:
            self.logger.info(f"Loading embedding model: {self.model_name}")
            
            # Import sentence-transformers only when needed
            try:
                from sentence_transformers import SentenceTransformer
            except ImportError:
                raise ImportError(
                    "sentence-transformers not installed. "
                    "Please install it with: pip install sentence-transformers"
                )
            
            # Load model with custom cache directory
            self._model = SentenceTransformer(
                self.model_name,
                device=self.device,
                cache_folder=self.MODEL_CACHE_DIR
            )
            
            # Set max sequence length
            self._model.max_seq_length = self.max_length
            
            # Get model info
            embedding_dim = self._model.get_sentence_embedding_dimension()
            self.logger.info(
                f"Model loaded successfully. "
                f"Embedding dimension: {embedding_dim}"
            )
            
        except Exception as e:
            self.logger.error(f"Error loading embedding model: {str(e)}")
            raise
    
    def generate_embedding(self, text: str,
                           normalize: bool = True) -> np.ndarray:
        """
        Generate embedding for a single text.
        
        Args:
            text: Input text to embed
            normalize: Whether to normalize the embedding vector
            
        Returns:
            numpy array containing the embedding vector
        """
        if not text or not text.strip():
            self.logger.warning("Empty text provided for embedding")
            # Return zero vector with correct dimension
            if self._model:
                dim = self._model.get_sentence_embedding_dimension()
            else:
                dim = 384  # Default dimension for all-MiniLM-L6-v2
            return np.zeros(dim, dtype=np.float32)
        
        try:
            # Truncate text if needed
            if len(text) > self.max_length * 4:  # Rough character estimate
                self.logger.debug(
                    f"Truncating text from {len(text)} to "
                    f"~{self.max_length * 4} chars"
                )
                text = text[:self.max_length * 4]
            
            # Generate embedding
            embedding = self.model.encode(
                text,
                convert_to_numpy=True,
                normalize_embeddings=normalize,
                show_progress_bar=False
            )
            
            return embedding
            
        except Exception as e:
            self.logger.error(f"Error generating embedding: {str(e)}")
            raise
    
    def generate_embeddings_batch(self, texts: List[str],
                                  batch_size: Optional[int] = None,
                                  normalize: bool = True,
                                  show_progress: bool = True
                                  ) -> List[np.ndarray]:
        """
        Generate embeddings for multiple texts in batch.
        
        Args:
            texts: List of input texts to embed
            batch_size: Batch size for processing (None for auto)
            normalize: Whether to normalize the embedding vectors
            show_progress: Whether to show progress bar
            
        Returns:
            List of numpy arrays containing embedding vectors
        """
        if not texts:
            return []
        
        try:
            # Filter out empty texts and remember their positions
            valid_texts = []
            valid_indices = []
            
            for i, text in enumerate(texts):
                if text and text.strip():
                    # Truncate if needed
                    if len(text) > self.max_length * 4:
                        text = text[:self.max_length * 4]
                    valid_texts.append(text)
                    valid_indices.append(i)
            
            if not valid_texts:
                # All texts were empty
                dim = self.model.get_sentence_embedding_dimension()
                return [np.zeros(dim, dtype=np.float32) for _ in texts]
            
            # Set batch size
            if batch_size is None:
                # Auto batch size based on device
                batch_size = 32 if self.device == 'cpu' else 64
            
            self.logger.info(
                f"Generating embeddings for {len(valid_texts)} texts "
                f"in batches of {batch_size}"
            )
            
            # Generate embeddings
            embeddings = self.model.encode(
                valid_texts,
                batch_size=batch_size,
                convert_to_numpy=True,
                normalize_embeddings=normalize,
                show_progress_bar=show_progress
            )
            
            # Create result list with proper ordering
            dim = embeddings.shape[1]
            result = []
            valid_idx = 0
            
            for i in range(len(texts)):
                if i in valid_indices:
                    result.append(embeddings[valid_idx])
                    valid_idx += 1
                else:
                    # Empty text, use zero vector
                    result.append(np.zeros(dim, dtype=np.float32))
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error generating batch embeddings: {str(e)}")
            raise
    
    def get_model_info(self) -> Dict[str, Any]:
        """
        Get information about the loaded model.
        
        Returns:
            Dictionary containing model information
        """
        try:
            info = {
                'model_name': self.model_name,
                'max_length': self.max_length,
                'device': self.device,
                'model_loaded': self._model is not None
            }
            
            if self._model is not None:
                info.update({
                    'embedding_dimension': (
                        self._model.get_sentence_embedding_dimension()
                    ),
                    'tokenizer_info': {
                        'type': type(self._model.tokenizer).__name__,
                        'vocab_size': len(self._model.tokenizer) if hasattr(
                            self._model.tokenizer, '__len__'
                        ) else 'unknown'
                    }
                })
            
            return info
            
        except Exception as e:
            self.logger.error(f"Error getting model info: {str(e)}")
            return {
                'model_name': self.model_name,
                'error': str(e)
            }
    
    def warmup(self):
        """
        Warm up the model by loading it and generating a test embedding.
        This is useful to ensure the model is ready before processing.
        """
        try:
            self.logger.info("Warming up embedding model...")
            
            # Load model
            _ = self.model
            
            # Generate test embedding
            test_text = "This is a warmup test."
            _ = self.generate_embedding(test_text)
            
            self.logger.info("Model warmup complete")
            
        except Exception as e:
            self.logger.error(f"Error during model warmup: {str(e)}")
            raise
    
    def clear_cache(self):
        """
        Clear the model from memory to free up resources.
        """
        if self._model is not None:
            self._model = None
            
            # Force garbage collection
            import gc
            gc.collect()
            
            # Clear GPU cache if using CUDA
            if self.device == 'cuda' and torch.cuda.is_available():
                torch.cuda.empty_cache()
            
            self.logger.info("Model cache cleared")
    
    @staticmethod
    def cosine_similarity(embedding1: np.ndarray, 
                          embedding2: np.ndarray) -> float:
        """
        Calculate cosine similarity between two embeddings.
        
        Args:
            embedding1: First embedding vector
            embedding2: Second embedding vector
            
        Returns:
            Cosine similarity score between -1 and 1
        """
        # Ensure inputs are numpy arrays
        embedding1 = np.array(embedding1)
        embedding2 = np.array(embedding2)
        
        # Calculate cosine similarity
        dot_product = np.dot(embedding1, embedding2)
        norm1 = np.linalg.norm(embedding1)
        norm2 = np.linalg.norm(embedding2)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return float(dot_product / (norm1 * norm2))
    
    @staticmethod
    def euclidean_distance(embedding1: np.ndarray, 
                           embedding2: np.ndarray) -> float:
        """
        Calculate Euclidean distance between two embeddings.
        
        Args:
            embedding1: First embedding vector
            embedding2: Second embedding vector
            
        Returns:
            Euclidean distance (lower is more similar)
        """
        # Ensure inputs are numpy arrays
        embedding1 = np.array(embedding1)
        embedding2 = np.array(embedding2)
        
        return float(np.linalg.norm(embedding1 - embedding2))
    
    def preprocess_text(self, text: str) -> str:
        """
        Preprocess text before embedding generation.
        This can be overridden for custom preprocessing.
        
        Args:
            text: Input text
            
        Returns:
            Preprocessed text
        """
        # Basic preprocessing
        # Remove excessive whitespace
        text = ' '.join(text.split())
        
        # Ensure text is not too long
        if len(text) > self.max_length * 4:
            text = text[:self.max_length * 4]
        
        return text


# Cached function for getting a singleton embedding generator
@lru_cache(maxsize=1)
def get_embedding_generator(model_name: Optional[str] = None,
                            max_length: Optional[int] = None,
                            device: Optional[str] = None
                            ) -> EmbeddingGenerator:
    """
    Get a cached instance of EmbeddingGenerator.
    This ensures we don't load the model multiple times.
    
    Args:
        model_name: Model name (must be same for caching)
        max_length: Max sequence length (must be same for caching)
        device: Device to use (must be same for caching)
        
    Returns:
        Cached EmbeddingGenerator instance
    """
    return EmbeddingGenerator(model_name, max_length, device)