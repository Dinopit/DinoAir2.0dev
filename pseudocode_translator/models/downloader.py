"""
Model downloader for the Pseudocode Translator

This module provides functionality to download language models from various
sources with progress tracking, checksum verification, and resume capability.
"""

import os
import shutil
import hashlib
import logging
import time
from pathlib import Path
from typing import Optional, Dict, Any, Callable
from urllib.parse import urlparse
import requests
from tqdm import tqdm


logger = logging.getLogger(__name__)


class DownloadError(Exception):
    """Exception raised for download-related errors"""
    pass


class ModelDownloader:
    """
    Handles downloading of language models with advanced features
    
    Features:
    - Progress tracking with tqdm
    - Resume capability for interrupted downloads
    - Checksum verification
    - Multiple retry attempts
    - Bandwidth limiting (optional)
    """
    
    def __init__(self, 
                 download_dir: str = "./models",
                 chunk_size: int = 8192,
                 max_retries: int = 3,
                 timeout: int = 30):
        """
        Initialize the model downloader
        
        Args:
            download_dir: Directory to save downloaded models
            chunk_size: Size of chunks for streaming download
            max_retries: Maximum number of retry attempts
            timeout: Request timeout in seconds
        """
        self.download_dir = Path(download_dir)
        self.chunk_size = chunk_size
        self.max_retries = max_retries
        self.timeout = timeout
        
        # Create download directory if it doesn't exist
        self.download_dir.mkdir(parents=True, exist_ok=True)
        
        # Session for connection pooling
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'PseudocodeTranslator/1.0'
        })
    
    def download_model(self,
                       url: str,
                       model_name: str,
                       expected_checksum: Optional[str] = None,
                       force_download: bool = False,
                       progress_callback: Optional[
                           Callable[[int, int], None]] = None
                       ) -> Path:
        """
        Download a model from a URL
        
        Args:
            url: URL to download from
            model_name: Name for the model (used for directory/file naming)
            expected_checksum: SHA256 checksum to verify
            force_download: Force re-download even if file exists
            progress_callback: Optional callback for progress updates
            
        Returns:
            Path to the downloaded model file
            
        Raises:
            DownloadError: If download fails
        """
        # Determine file path
        model_dir = self.download_dir / model_name
        model_dir.mkdir(exist_ok=True)
        
        # Get filename from URL or use default
        filename = self._get_filename_from_url(url) or f"{model_name}.gguf"
        file_path = model_dir / filename
        
        # Check if already downloaded
        if file_path.exists() and not force_download:
            logger.info(f"Model already exists at {file_path}")
            
            # Verify checksum if provided
            if expected_checksum:
                if self._verify_checksum(file_path, expected_checksum):
                    logger.info("Checksum verification passed")
                    return file_path
                else:
                    logger.warning(
                        "Checksum verification failed, re-downloading"
                    )
            else:
                return file_path
        
        # Download the model
        logger.info(f"Downloading model from {url}")
        temp_path = file_path.with_suffix('.tmp')
        
        try:
            self._download_with_resume(
                url, temp_path, progress_callback
            )
            
            # Verify checksum if provided
            if expected_checksum:
                if not self._verify_checksum(temp_path, expected_checksum):
                    raise DownloadError(
                        "Downloaded file checksum does not match expected"
                    )
                logger.info("Checksum verification passed")
            
            # Move temp file to final location
            shutil.move(str(temp_path), str(file_path))
            logger.info(f"Model downloaded successfully to {file_path}")
            
            return file_path
            
        except Exception as e:
            # Clean up temp file on error
            if temp_path.exists():
                temp_path.unlink()
            raise DownloadError(f"Failed to download model: {str(e)}")
    
    def download_from_huggingface(self,
                                  repo_id: str,
                                  filename: str,
                                  revision: str = "main",
                                  **kwargs) -> Path:
        """
        Download a model from Hugging Face Hub
        
        Args:
            repo_id: Repository ID (e.g., "Qwen/Qwen-7B-Chat-GGUF")
            filename: Filename in the repository
            revision: Git revision (branch/tag/commit)
            **kwargs: Additional arguments for download_model
            
        Returns:
            Path to downloaded model
        """
        # Construct Hugging Face URL
        url = (
            f"https://huggingface.co/{repo_id}/resolve/{revision}/{filename}"
        )
        
        # Use repo name as model name
        model_name = repo_id.split('/')[-1]
        
        return self.download_model(url, model_name, **kwargs)
    
    def _download_with_resume(self,
                              url: str,
                              file_path: Path,
                              progress_callback: Optional[Callable] = None
                              ) -> None:
        """
        Download with resume capability
        
        Args:
            url: URL to download from
            file_path: Path to save file
            progress_callback: Optional progress callback
        """
        headers = {}
        mode = 'wb'
        resume_pos = 0
        
        # Check if partial download exists
        if file_path.exists():
            resume_pos = file_path.stat().st_size
            headers['Range'] = f'bytes={resume_pos}-'
            mode = 'ab'
            logger.info(f"Resuming download from byte {resume_pos}")
        
        # Make request with retries
        response = None
        for attempt in range(self.max_retries):
            try:
                response = self.session.get(
                    url,
                    headers=headers,
                    stream=True,
                    timeout=self.timeout
                )
                
                # Check if server supports resume
                if resume_pos > 0 and response.status_code != 206:
                    logger.warning(
                        "Server doesn't support resume, starting over"
                    )
                    resume_pos = 0
                    mode = 'wb'
                    response = self.session.get(
                        url, stream=True, timeout=self.timeout
                    )
                
                response.raise_for_status()
                break
                
            except Exception as e:
                logger.warning(f"Download attempt {attempt + 1} failed: {e}")
                if attempt == self.max_retries - 1:
                    raise
                time.sleep(2 ** attempt)  # Exponential backoff
        
        if not response:
            raise DownloadError("Failed to connect after all retries")
        
        # Get total file size
        total_size = int(response.headers.get('content-length', 0))
        if resume_pos > 0:
            total_size += resume_pos
        
        # Download with progress bar
        with open(file_path, mode) as f:
            with tqdm(
                total=total_size,
                initial=resume_pos,
                unit='B',
                unit_scale=True,
                desc=file_path.name
            ) as pbar:
                for chunk in response.iter_content(chunk_size=self.chunk_size):
                    if chunk:
                        f.write(chunk)
                        pbar.update(len(chunk))
                        
                        if progress_callback:
                            progress_callback(pbar.n, total_size)
    
    def _verify_checksum(self,
                         file_path: Path,
                         expected_checksum: str) -> bool:
        """
        Verify file checksum
        
        Args:
            file_path: Path to file
            expected_checksum: Expected SHA256 checksum
            
        Returns:
            True if checksum matches
        """
        logger.info("Verifying checksum...")
        sha256_hash = hashlib.sha256()
        
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(self.chunk_size), b""):
                sha256_hash.update(chunk)
        
        actual_checksum = sha256_hash.hexdigest()
        return actual_checksum.lower() == expected_checksum.lower()
    
    def _get_filename_from_url(self, url: str) -> Optional[str]:
        """
        Extract filename from URL
        
        Args:
            url: URL to parse
            
        Returns:
            Filename or None
        """
        parsed = urlparse(url)
        path = parsed.path
        
        if path:
            return os.path.basename(path)
        return None
    
    def list_downloaded_models(self) -> Dict[str, Dict[str, Any]]:
        """
        List all downloaded models
        
        Returns:
            Dictionary of model information
        """
        models = {}
        
        for model_dir in self.download_dir.iterdir():
            if not model_dir.is_dir():
                continue
                
            model_files = []
            total_size = 0
            
            for file in model_dir.iterdir():
                if file.is_file() and not file.name.endswith('.tmp'):
                    file_info = {
                        'name': file.name,
                        'size': file.stat().st_size,
                        'modified': file.stat().st_mtime
                    }
                    model_files.append(file_info)
                    total_size += file_info['size']
            
            if model_files:
                models[model_dir.name] = {
                    'path': str(model_dir),
                    'files': model_files,
                    'total_size': total_size
                }
        
        return models
    
    def get_download_size(self, url: str) -> Optional[int]:
        """
        Get the size of a file without downloading
        
        Args:
            url: URL to check
            
        Returns:
            File size in bytes or None
        """
        try:
            response = self.session.head(url, timeout=self.timeout)
            response.raise_for_status()
            return int(response.headers.get('content-length', 0))
        except Exception as e:
            logger.warning(f"Failed to get file size: {e}")
            return None
    
    def cleanup_temp_files(self) -> int:
        """
        Clean up incomplete downloads
        
        Returns:
            Number of files cleaned
        """
        cleaned = 0
        
        for temp_file in self.download_dir.rglob('*.tmp'):
            try:
                temp_file.unlink()
                cleaned += 1
                logger.info(f"Removed temp file: {temp_file}")
            except Exception as e:
                logger.warning(f"Failed to remove {temp_file}: {e}")
        
        return cleaned
    
    def estimate_download_time(self,
                               file_size: int,
                               bandwidth_mbps: float = 10.0) -> float:
        """
        Estimate download time
        
        Args:
            file_size: File size in bytes
            bandwidth_mbps: Estimated bandwidth in Mbps
            
        Returns:
            Estimated time in seconds
        """
        bandwidth_bps = bandwidth_mbps * 1024 * 1024 / 8
        return file_size / bandwidth_bps


# Convenience functions
def download_model(url: str,
                   model_name: str,
                   download_dir: str = "./models",
                   **kwargs) -> Path:
    """
    Quick function to download a model
    
    Args:
        url: Download URL
        model_name: Model name
        download_dir: Where to save models
        **kwargs: Additional arguments for ModelDownloader
        
    Returns:
        Path to downloaded model
    """
    downloader = ModelDownloader(download_dir=download_dir)
    return downloader.download_model(url, model_name, **kwargs)


def download_from_huggingface(repo_id: str,
                              filename: str,
                              download_dir: str = "./models",
                              **kwargs) -> Path:
    """
    Quick function to download from Hugging Face
    
    Args:
        repo_id: HF repository ID
        filename: File to download
        download_dir: Where to save models
        **kwargs: Additional arguments
        
    Returns:
        Path to downloaded model
    """
    downloader = ModelDownloader(download_dir=download_dir)
    return downloader.download_from_huggingface(repo_id, filename, **kwargs)