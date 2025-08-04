"""
Parallel Processor module for the Pseudocode Translator

Provides concurrent processing capabilities for handling multiple files
efficiently with thread-safe operations and resource pooling.
"""

import threading
import queue
import multiprocessing
from concurrent.futures import (
    ThreadPoolExecutor, ProcessPoolExecutor, as_completed
)
from typing import List, Dict, Any, Optional, Callable, Union
from dataclasses import dataclass, field
from pathlib import Path
import logging
import time
from enum import Enum

from .parser import ParserModule
from .translator import TranslationManager
from .config import TranslatorConfig

logger = logging.getLogger(__name__)


class ProcessingMode(Enum):
    """Processing mode for parallel execution"""
    THREAD = "thread"
    PROCESS = "process"
    HYBRID = "hybrid"


@dataclass
class FileTask:
    """Represents a file processing task"""
    file_path: Path
    content: Optional[str] = None
    priority: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __lt__(self, other):
        """Priority comparison for queue ordering"""
        return self.priority > other.priority  # Higher priority first


@dataclass
class ProcessingResult:
    """Result of processing a single file"""
    file_path: Path
    success: bool
    output: Optional[str] = None
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    processing_time: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


class ResourcePool:
    """Thread-safe resource pool for shared resources"""
    
    def __init__(self, resource_factory: Callable, max_size: int = 10):
        """
        Initialize resource pool
        
        Args:
            resource_factory: Function to create new resources
            max_size: Maximum pool size
        """
        self.resource_factory = resource_factory
        self.max_size = max_size
        self._pool = queue.Queue(maxsize=max_size)
        self._created_count = 0
        self._lock = threading.Lock()
        
        # Pre-populate pool
        for _ in range(min(3, max_size)):
            self._create_resource()
    
    def _create_resource(self):
        """Create a new resource"""
        try:
            resource = self.resource_factory()
            self._pool.put(resource)
            with self._lock:
                self._created_count += 1
        except Exception as e:
            logger.error(f"Failed to create resource: {e}")
    
    def acquire(self, timeout: Optional[float] = None):
        """
        Acquire a resource from the pool
        
        Args:
            timeout: Maximum time to wait for resource
            
        Returns:
            Resource from pool
        """
        try:
            # Try to get from pool
            return self._pool.get(timeout=timeout)
        except queue.Empty:
            # Create new resource if under limit
            with self._lock:
                if self._created_count < self.max_size:
                    self._create_resource()
                    return self._pool.get(timeout=0.1)
            raise TimeoutError("No resources available")
    
    def release(self, resource):
        """Release resource back to pool"""
        try:
            self._pool.put_nowait(resource)
        except queue.Full:
            # Pool is full, discard resource
            pass


class ParallelProcessor:
    """
    Handles parallel processing of multiple files with configurable
    concurrency and resource management
    """
    
    def __init__(
        self,
        config: TranslatorConfig,
        mode: ProcessingMode = ProcessingMode.THREAD,
        max_workers: Optional[int] = None,
        use_resource_pool: bool = True
    ):
        """
        Initialize parallel processor
        
        Args:
            config: Translator configuration
            mode: Processing mode (thread/process/hybrid)
            max_workers: Maximum concurrent workers (None = auto)
            use_resource_pool: Enable resource pooling
        """
        self.config = config
        self.mode = mode
        self.use_resource_pool = use_resource_pool
        
        # Determine optimal worker count
        if max_workers is None:
            cpu_count = multiprocessing.cpu_count()
            if mode == ProcessingMode.THREAD:
                # For I/O bound tasks, use more threads
                self.max_workers = min(cpu_count * 2, 16)
            elif mode == ProcessingMode.PROCESS:
                # For CPU bound tasks, use CPU count
                self.max_workers = cpu_count
            else:  # HYBRID
                self.max_workers = cpu_count
        else:
            self.max_workers = max_workers
        
        # Resource pools
        self._parser_pool = None
        self._translator_pool = None
        if use_resource_pool:
            self._setup_resource_pools()
        
        # Statistics
        self._stats_lock = threading.Lock()
        self._stats = {
            'files_processed': 0,
            'files_succeeded': 0,
            'files_failed': 0,
            'total_time': 0.0,
            'errors': []
        }
        
        logger.info(
            f"Initialized ParallelProcessor with mode={mode.value}, "
            f"max_workers={self.max_workers}"
        )
    
    def _setup_resource_pools(self):
        """Setup resource pools for parsers and translators"""
        self._parser_pool = ResourcePool(
            lambda: ParserModule(),
            max_size=self.max_workers
        )
        
        self._translator_pool = ResourcePool(
            lambda: TranslationManager(self.config),
            max_size=max(self.max_workers // 2, 1)
        )
    
    def process_files(
        self,
        file_paths: List[Union[str, Path]],
        progress_callback: Optional[Callable[[float, str], None]] = None,
        error_callback: Optional[Callable[[Path, Exception], None]] = None
    ) -> List[ProcessingResult]:
        """
        Process multiple files in parallel
        
        Args:
            file_paths: List of file paths to process
            progress_callback: Optional callback for progress updates
            error_callback: Optional callback for error handling
            
        Returns:
            List of processing results
        """
        # Convert to Path objects and validate
        tasks = []
        for i, file_path in enumerate(file_paths):
            path = Path(file_path)
            if not path.exists():
                logger.warning(f"File not found: {path}")
                continue
            
            # Create task with priority based on file size
            try:
                file_size = path.stat().st_size
                priority = -file_size  # Smaller files get higher priority
                task = FileTask(file_path=path, priority=priority)
                tasks.append(task)
            except Exception as e:
                logger.error(f"Error accessing file {path}: {e}")
        
        if not tasks:
            return []
        
        # Choose processing strategy
        if self.mode == ProcessingMode.THREAD:
            return self._process_with_threads(
                tasks, progress_callback, error_callback
            )
        elif self.mode == ProcessingMode.PROCESS:
            return self._process_with_processes(
                tasks, progress_callback, error_callback
            )
        else:  # HYBRID
            return self._process_hybrid(
                tasks, progress_callback, error_callback
            )
    
    def _process_with_threads(
        self,
        tasks: List[FileTask],
        progress_callback: Optional[Callable],
        error_callback: Optional[Callable]
    ) -> List[ProcessingResult]:
        """Process files using thread pool"""
        results = []
        completed = 0
        total = len(tasks)
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all tasks
            future_to_task = {
                executor.submit(self._process_single_file, task): task
                for task in tasks
            }
            
            # Process completed tasks
            for future in as_completed(future_to_task):
                task = future_to_task[future]
                try:
                    result = future.result()
                    results.append(result)
                    
                    # Update statistics
                    with self._stats_lock:
                        self._stats['files_processed'] += 1
                        if result.success:
                            self._stats['files_succeeded'] += 1
                        else:
                            self._stats['files_failed'] += 1
                        self._stats['total_time'] += result.processing_time
                    
                except Exception as e:
                    logger.error(f"Error processing {task.file_path}: {e}")
                    
                    # Create error result
                    result = ProcessingResult(
                        file_path=task.file_path,
                        success=False,
                        errors=[str(e)]
                    )
                    results.append(result)
                    
                    if error_callback:
                        error_callback(task.file_path, e)
                
                # Update progress
                completed += 1
                if progress_callback:
                    progress = completed / total
                    message = f"Processed {completed}/{total} files"
                    progress_callback(progress, message)
        
        return results
    
    def _process_with_processes(
        self,
        tasks: List[FileTask],
        progress_callback: Optional[Callable],
        error_callback: Optional[Callable]
    ) -> List[ProcessingResult]:
        """Process files using process pool"""
        results = []
        completed = 0
        total = len(tasks)
        
        # Note: Resource pools don't work well across processes
        # Each process will create its own resources
        with ProcessPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all tasks
            future_to_task = {
                executor.submit(
                    _process_file_in_subprocess,
                    task,
                    self.config
                ): task
                for task in tasks
            }
            
            # Process completed tasks
            for future in as_completed(future_to_task):
                task = future_to_task[future]
                try:
                    result = future.result()
                    results.append(result)
                    
                    # Update statistics
                    with self._stats_lock:
                        self._stats['files_processed'] += 1
                        if result.success:
                            self._stats['files_succeeded'] += 1
                        else:
                            self._stats['files_failed'] += 1
                        self._stats['total_time'] += result.processing_time
                    
                except Exception as e:
                    logger.error(f"Error processing {task.file_path}: {e}")
                    
                    # Create error result
                    result = ProcessingResult(
                        file_path=task.file_path,
                        success=False,
                        errors=[str(e)]
                    )
                    results.append(result)
                    
                    if error_callback:
                        error_callback(task.file_path, e)
                
                # Update progress
                completed += 1
                if progress_callback:
                    progress = completed / total
                    message = f"Processed {completed}/{total} files"
                    progress_callback(progress, message)
        
        return results
    
    def _process_hybrid(
        self,
        tasks: List[FileTask],
        progress_callback: Optional[Callable],
        error_callback: Optional[Callable]
    ) -> List[ProcessingResult]:
        """
        Process files using hybrid approach:
        - Small files in threads
        - Large files in separate processes
        """
        # Separate tasks by size
        small_tasks = []
        large_tasks = []
        
        threshold = 100 * 1024  # 100KB threshold
        
        for task in tasks:
            try:
                size = task.file_path.stat().st_size
                if size < threshold:
                    small_tasks.append(task)
                else:
                    large_tasks.append(task)
            except Exception:
                small_tasks.append(task)  # Default to thread processing
        
        results = []
        
        # Process small files in threads
        if small_tasks:
            thread_results = self._process_with_threads(
                small_tasks, None, error_callback
            )
            results.extend(thread_results)
        
        # Process large files in processes
        if large_tasks:
            process_results = self._process_with_processes(
                large_tasks, None, error_callback
            )
            results.extend(process_results)
        
        # Final progress update
        if progress_callback:
            progress_callback(1.0, f"Completed processing {len(tasks)} files")
        
        return results
    
    def _process_single_file(self, task: FileTask) -> ProcessingResult:
        """Process a single file"""
        start_time = time.time()
        
        try:
            # Read file content if not provided
            if task.content is None:
                with open(task.file_path, 'r', encoding='utf-8') as f:
                    task.content = f.read()
            
            # Get resources from pool or create new ones
            if (self.use_resource_pool and self._parser_pool and
                    self._translator_pool):
                parser = self._parser_pool.acquire(timeout=30)
                translator = self._translator_pool.acquire(timeout=30)
                try:
                    # Process the file
                    result = self._do_processing(
                        task, parser, translator
                    )
                finally:
                    # Release resources back to pool
                    self._parser_pool.release(parser)
                    self._translator_pool.release(translator)
            else:
                # Create temporary resources
                parser = ParserModule()
                translator = TranslationManager(self.config)
                result = self._do_processing(task, parser, translator)
            
            # Calculate processing time
            result.processing_time = time.time() - start_time
            return result
            
        except Exception as e:
            logger.error(f"Failed to process {task.file_path}: {e}")
            return ProcessingResult(
                file_path=task.file_path,
                success=False,
                errors=[str(e)],
                processing_time=time.time() - start_time
            )
    
    def _do_processing(
        self,
        task: FileTask,
        parser: ParserModule,
        translator: TranslationManager
    ) -> ProcessingResult:
        """Perform actual processing with given resources"""
        errors = []
        warnings = []
        
        try:
            # Ensure content is not None
            if task.content is None:
                return ProcessingResult(
                    file_path=task.file_path,
                    success=False,
                    errors=["No content to process"]
                )
            
            # Parse the content
            parse_result = parser.get_parse_result(task.content)
            
            # Check if parsing succeeded
            # ParseResult attributes are correct but Pylance has issues
            if not parse_result.success:  # type: ignore
                errors.extend(
                    [str(e) for e in parse_result.errors]  # type: ignore
                )
                warnings.extend(parse_result.warnings)  # type: ignore
                
                return ProcessingResult(
                    file_path=task.file_path,
                    success=False,
                    errors=errors,
                    warnings=warnings
                )
            
            # Translate the content
            translation_result = translator.translate_pseudocode(task.content)
            
            if translation_result.success:
                return ProcessingResult(
                    file_path=task.file_path,
                    success=True,
                    output=translation_result.code,
                    errors=translation_result.errors,
                    warnings=translation_result.warnings,
                    metadata=translation_result.metadata
                )
            else:
                return ProcessingResult(
                    file_path=task.file_path,
                    success=False,
                    errors=translation_result.errors,
                    warnings=translation_result.warnings,
                    metadata=translation_result.metadata
                )
                
        except Exception as e:
            logger.error(f"Processing error for {task.file_path}: {e}")
            return ProcessingResult(
                file_path=task.file_path,
                success=False,
                errors=[str(e)]
            )
    
    def process_directory(
        self,
        directory: Union[str, Path],
        pattern: str = "*.py",
        recursive: bool = True,
        progress_callback: Optional[Callable] = None
    ) -> List[ProcessingResult]:
        """
        Process all matching files in a directory
        
        Args:
            directory: Directory path
            pattern: File pattern to match
            recursive: Process subdirectories
            progress_callback: Progress callback
            
        Returns:
            List of processing results
        """
        directory = Path(directory)
        if not directory.is_dir():
            raise ValueError(f"Not a directory: {directory}")
        
        # Find matching files
        if recursive:
            files = list(directory.rglob(pattern))
        else:
            files = list(directory.glob(pattern))
        
        logger.info(f"Found {len(files)} files matching '{pattern}'")
        
        return self.process_files(
            [str(f) for f in files],  # Convert Path to str
            progress_callback
        )
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get processing statistics"""
        with self._stats_lock:
            stats = self._stats.copy()
            
            # Calculate averages
            if stats['files_processed'] > 0:
                stats['avg_time_per_file'] = (
                    stats['total_time'] / stats['files_processed']
                )
                stats['success_rate'] = (
                    stats['files_succeeded'] / stats['files_processed'] * 100
                )
            else:
                stats['avg_time_per_file'] = 0
                stats['success_rate'] = 0
            
            return stats
    
    def reset_statistics(self):
        """Reset processing statistics"""
        with self._stats_lock:
            self._stats = {
                'files_processed': 0,
                'files_succeeded': 0,
                'files_failed': 0,
                'total_time': 0.0,
                'errors': []
            }


# Helper function for process pool
def _process_file_in_subprocess(
    task: FileTask,
    config: TranslatorConfig
) -> ProcessingResult:
    """
    Process a file in a subprocess (for process pool)
    
    This function must be at module level to be picklable
    """
    try:
        # Create fresh resources in subprocess
        parser = ParserModule()
        translator = TranslationManager(config)
        
        # Read file if content not provided
        if task.content is None:
            with open(task.file_path, 'r', encoding='utf-8') as f:
                task.content = f.read()
        
        # Process
        start_time = time.time()
        
        # Parse
        if task.content is None:
            return ProcessingResult(
                file_path=task.file_path,
                success=False,
                errors=["No content to process"],
                processing_time=time.time() - start_time
            )
            
        parse_result = parser.get_parse_result(task.content)
        # Type annotations in ParseResult are correct but Pylance has issues
        if not parse_result.success:  # type: ignore
            return ProcessingResult(
                file_path=task.file_path,
                success=False,
                errors=[str(e) for e in parse_result.errors],  # type: ignore
                warnings=parse_result.warnings,  # type: ignore
                processing_time=time.time() - start_time
            )
        
        # Translate
        translation_result = translator.translate_pseudocode(task.content)
        
        result = ProcessingResult(
            file_path=task.file_path,
            success=translation_result.success,
            output=(translation_result.code
                    if translation_result.success else None),
            errors=translation_result.errors,
            warnings=translation_result.warnings,
            processing_time=time.time() - start_time,
            metadata=translation_result.metadata
        )
        
        # Cleanup
        translator.shutdown()
        
        return result
        
    except Exception as e:
        return ProcessingResult(
            file_path=task.file_path,
            success=False,
            errors=[str(e)],
            processing_time=0.0
        )


class BatchProcessor:
    """
    High-level batch processing with advanced features
    """
    
    def __init__(
        self,
        config: TranslatorConfig,
        output_dir: Optional[Union[str, Path]] = None,
        keep_structure: bool = True
    ):
        """
        Initialize batch processor
        
        Args:
            config: Translator configuration
            output_dir: Directory for output files
            keep_structure: Maintain directory structure
        """
        self.config = config
        self.output_dir = Path(output_dir) if output_dir else None
        self.keep_structure = keep_structure
        
        # Create parallel processor
        self.processor = ParallelProcessor(
            config,
            mode=ProcessingMode.HYBRID,
            use_resource_pool=True
        )
        
        if self.output_dir:
            self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def process_batch(
        self,
        input_paths: List[Union[str, Path]],
        output_suffix: str = "_translated",
        dry_run: bool = False
    ) -> Dict[str, Any]:
        """
        Process a batch of files
        
        Args:
            input_paths: List of input file/directory paths
            output_suffix: Suffix for output files
            dry_run: If True, don't write output files
            
        Returns:
            Summary of batch processing
        """
        # Collect all files
        all_files = []
        for path in input_paths:
            path = Path(path)
            if path.is_file():
                all_files.append(path)
            elif path.is_dir():
                all_files.extend(path.rglob("*.py"))
        
        if not all_files:
            return {
                'total_files': 0,
                'processed': 0,
                'succeeded': 0,
                'failed': 0,
                'errors': ['No files found to process']
            }
        
        logger.info(f"Processing batch of {len(all_files)} files")
        
        # Process files
        results = self.processor.process_files(
            all_files,
            progress_callback=lambda p, m: logger.info(
                f"Progress: {p:.1%} - {m}"
            )
        )
        
        # Handle results
        succeeded = 0
        failed = 0
        errors = []
        
        for result in results:
            if result.success and not dry_run:
                # Write output file
                output_path = self._get_output_path(
                    result.file_path, output_suffix
                )
                try:
                    output_path.parent.mkdir(parents=True, exist_ok=True)
                    with open(output_path, 'w', encoding='utf-8') as f:
                        if result.output:
                            f.write(result.output)
                    succeeded += 1
                except Exception as e:
                    failed += 1
                    errors.append(f"Failed to write {output_path}: {e}")
            elif result.success:
                succeeded += 1
            else:
                failed += 1
                errors.extend(result.errors)
        
        # Get statistics
        stats = self.processor.get_statistics()
        
        return {
            'total_files': len(all_files),
            'processed': len(results),
            'succeeded': succeeded,
            'failed': failed,
            'errors': errors,
            'statistics': stats,
            'dry_run': dry_run
        }
    
    def _get_output_path(
        self,
        input_path: Path,
        suffix: str
    ) -> Path:
        """Calculate output path for a file"""
        if not self.output_dir:
            # Write next to input file
            return input_path.with_stem(input_path.stem + suffix)
        
        if self.keep_structure:
            # Try to maintain relative structure
            try:
                rel_path = input_path.relative_to(Path.cwd())
                output_path = self.output_dir / rel_path
            except ValueError:
                # Can't make relative, just use filename
                output_path = self.output_dir / input_path.name
        else:
            # Flat structure
            output_path = self.output_dir / input_path.name
        
        # Add suffix
        return output_path.with_stem(output_path.stem + suffix)