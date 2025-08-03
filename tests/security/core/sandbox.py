"""
Security sandbox for isolated test execution.

Provides a secure environment for running potentially dangerous tests.
"""

import os
import time
import multiprocessing
import tempfile
import hashlib
from datetime import datetime
from typing import Any, Dict, Optional, Callable
from pathlib import Path
import pickle
import base64
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC


class SecuritySandbox:
    """Isolated environment for security test execution."""
    
    def __init__(self, 
                 max_cpu_time: int = 30,
                 max_memory_mb: int = 512,
                 max_processes: int = 10,
                 temp_dir: Optional[str] = None):
        """
        Initialize sandbox with resource limits.
        
        Args:
            max_cpu_time: Maximum CPU seconds allowed
            max_memory_mb: Maximum memory in MB
            max_processes: Maximum number of processes
            temp_dir: Temporary directory for sandbox files
        """
        self.max_cpu_time = max_cpu_time
        self.max_memory_mb = max_memory_mb
        self.max_processes = max_processes
        self.temp_dir = temp_dir or tempfile.gettempdir()
        
        # Generate encryption key for secure storage
        self._init_encryption()
        
        # Track active processes
        self.active_processes = []
        
    def _init_encryption(self):
        """Initialize encryption for secure result storage."""
        # Use a derived key from system info (local only)
        salt = b'DinoAirSecuritySandbox'
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(
            kdf.derive(b'LocalOnlySecurityTests')
        )
        self.cipher = Fernet(key)
        
    def execute_in_sandbox(
        self,
        func: Callable,
        args: tuple = (),
        kwargs: Optional[dict] = None
    ) -> Dict[str, Any]:
        """
        Execute function in sandboxed environment.
        
        Args:
            func: Function to execute
            args: Function arguments
            kwargs: Function keyword arguments
            
        Returns:
            Dict with execution results
        """
        kwargs = kwargs or {}
        
        # Create isolated process
        queue = multiprocessing.Queue()
        process = multiprocessing.Process(
            target=self._sandbox_worker,
            args=(func, args, kwargs, queue)
        )
        
        # Track process
        self.active_processes.append(process)
        
        # Start with timeout
        start_time = time.time()
        process.start()
        process.join(timeout=self.max_cpu_time)
        
        # Check if process completed
        if process.is_alive():
            process.terminate()
            process.join(timeout=5)
            if process.is_alive():
                process.kill()
            
            result = {
                'success': False,
                'error': 'Process timeout exceeded',
                'timeout': True,
                'duration': self.max_cpu_time
            }
        else:
            # Get result from queue
            try:
                result = queue.get_nowait()
                result['duration'] = time.time() - start_time
            except Exception:
                result = {
                    'success': False,
                    'error': 'Failed to retrieve result',
                    'duration': time.time() - start_time
                }
        
        # Clean up
        self.active_processes.remove(process)
        
        return result
        
    def _sandbox_worker(
        self,
        func: Callable,
        args: tuple,
        kwargs: dict,
        queue: multiprocessing.Queue
    ):
        """Worker process with resource limits."""
        try:
            # Set resource limits (Unix only, skip on Windows)
            try:
                import resource
                if hasattr(resource, 'RLIMIT_CPU'):
                    resource.setrlimit(
                        resource.RLIMIT_CPU,
                        (self.max_cpu_time, self.max_cpu_time)
                    )
                
                if hasattr(resource, 'RLIMIT_AS'):
                    max_memory = self.max_memory_mb * 1024 * 1024
                    resource.setrlimit(
                        resource.RLIMIT_AS,
                        (max_memory, max_memory)
                    )
                    
                if hasattr(resource, 'RLIMIT_NPROC'):
                    resource.setrlimit(
                        resource.RLIMIT_NPROC,
                        (self.max_processes, self.max_processes)
                    )
            except ImportError:
                # Resource module not available on Windows
                pass
            
            # Execute function
            result = func(*args, **kwargs)
            
            queue.put({
                'success': True,
                'result': result,
                'error': None
            })
            
        except Exception as e:
            queue.put({
                'success': False,
                'result': None,
                'error': str(e)
            })
            
    def store_result_securely(
        self,
        test_id: str,
        result: Dict[str, Any]
    ) -> str:
        """
        Store test result with encryption.
        
        Args:
            test_id: Unique test identifier
            result: Test result dictionary
            
        Returns:
            Path to encrypted result file
        """
        # Add metadata
        result['stored_at'] = datetime.now().isoformat()
        result['test_id'] = test_id
        
        # Serialize and encrypt
        serialized = pickle.dumps(result)
        encrypted = self.cipher.encrypt(serialized)
        
        # Generate filename with hash
        filename_hash = hashlib.sha256(test_id.encode()).hexdigest()[:16]
        filepath = Path(self.temp_dir) / f"sandbox_result_{filename_hash}.enc"
        
        # Write encrypted data
        with open(filepath, 'wb') as f:
            f.write(encrypted)
            
        return str(filepath)
        
    def load_result_securely(self, filepath: str) -> Dict[str, Any]:
        """
        Load and decrypt test result.
        
        Args:
            filepath: Path to encrypted result file
            
        Returns:
            Decrypted result dictionary
        """
        with open(filepath, 'rb') as f:
            encrypted = f.read()
            
        # Decrypt and deserialize
        decrypted = self.cipher.decrypt(encrypted)
        result = pickle.loads(decrypted)
        
        return result
        
    def cleanup_sandbox(self):
        """Clean up sandbox resources."""
        # Terminate any remaining processes
        for process in self.active_processes:
            if process.is_alive():
                process.terminate()
                process.join(timeout=5)
                if process.is_alive():
                    process.kill()
                    
        self.active_processes.clear()
        
        # Clean up temporary files
        pattern = Path(self.temp_dir) / "sandbox_result_*.enc"
        for filepath in pattern.parent.glob(pattern.name):
            try:
                filepath.unlink()
            except Exception:
                pass
                
    def create_restricted_namespace(self) -> dict:
        """Create restricted namespace for code execution."""
        # Only allow safe built-ins
        safe_builtins = {
            'abs': abs,
            'bool': bool,
            'dict': dict,
            'float': float,
            'int': int,
            'len': len,
            'list': list,
            'max': max,
            'min': min,
            'str': str,
            'tuple': tuple,
            'type': type,
        }
        
        return {
            '__builtins__': safe_builtins,
            '__name__': 'sandbox',
            '__doc__': None,
            '__package__': None,
        }
        
    def validate_test_input(self, test_input: str) -> bool:
        """
        Validate test input before execution.
        
        Args:
            test_input: Input to validate
            
        Returns:
            True if input appears safe
        """
        # Check for dangerous patterns
        dangerous_patterns = [
            '__import__',
            'eval',
            'exec',
            'compile',
            'open',
            'file',
            'input',
            'raw_input',
            '__builtins__',
            'globals',
            'locals',
            'vars',
            'dir',
        ]
        
        test_lower = test_input.lower()
        for pattern in dangerous_patterns:
            if pattern in test_lower:
                return False
                
        return True
        
    def __enter__(self):
        """Context manager entry."""
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit with cleanup."""
        self.cleanup_sandbox()