"""
Performance benchmarks for the Pseudocode Translator

Tests the performance improvements including:
- AST caching with TTL and size limits
- Parallel processing for multiple files
- Streaming for large files
- Optimized validation
"""

import time
import tempfile
import threading
import psutil
from pathlib import Path
from typing import Any
import statistics

# Import modules to test
from ..translator import TranslationManager
from ..validator import Validator
from ..config import TranslatorConfig
from ..ast_cache import ASTCache, clear_cache, get_cache_stats
from ..parallel_processor import ParallelProcessor, ProcessingMode
from ..streaming.pipeline import StreamingPipeline


class PerformanceMetrics:
    """Track performance metrics during tests"""
    
    def __init__(self):
        self.start_time = None
        self.end_time = None
        self.start_memory = None
        self.end_memory = None
        self.metrics = {}
    
    def start(self):
        """Start tracking metrics"""
        self.start_time = time.time()
        process = psutil.Process()
        self.start_memory = process.memory_info().rss / 1024 / 1024  # MB
        clear_cache()  # Clear cache for fair comparison
    
    def stop(self):
        """Stop tracking and calculate metrics"""
        self.end_time = time.time()
        process = psutil.Process()
        self.end_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        exec_time = 0.0
        mem_used = 0.0
        if self.start_time is not None:
            exec_time = self.end_time - self.start_time
        if self.start_memory is not None:
            mem_used = self.end_memory - self.start_memory
        
        self.metrics = {
            'execution_time': exec_time,
            'memory_used': mem_used,
            'memory_peak': self.end_memory
        }
        
        return self.metrics
    
    def add_metric(self, name: str, value: Any):
        """Add custom metric"""
        self.metrics[name] = value


def generate_pseudocode(size: str = 'medium') -> str:
    """Generate pseudocode of various sizes for testing"""
    
    base_code = """
# Calculate factorial
create a function to calculate factorial of n:
    if n is 0 or 1:
        return 1
    else:
        return n multiplied by factorial of n-1

# Process list of numbers
define a function process_numbers that takes a list:
    create empty result list
    for each number in the list:
        if number is even:
            add number squared to result
        else:
            add number times 3 to result
    return the result list

# Main program
numbers = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
processed = process_numbers(numbers)
print("Processed numbers:", processed)

# Calculate factorials
for i in range(1, 11):
    print(f"Factorial of {i} is {factorial(i)}")
"""
    
    if size == 'small':
        return base_code
    elif size == 'medium':
        return base_code * 5  # ~1KB
    elif size == 'large':
        return base_code * 50  # ~10KB
    elif size == 'huge':
        return base_code * 500  # ~100KB
    else:
        return base_code


def generate_python_code(complexity: str = 'medium') -> str:
    """Generate Python code of various complexities"""
    
    if complexity == 'simple':
        return """
def add(a, b):
    return a + b

def multiply(a, b):
    return a * b

result = add(5, 3)
print(result)
"""
    
    elif complexity == 'medium':
        return """
import math

class Calculator:
    def __init__(self):
        self.history = []
    
    def add(self, a, b):
        result = a + b
        self.history.append(f"{a} + {b} = {result}")
        return result
    
    def factorial(self, n):
        if n < 0:
            raise ValueError("Factorial not defined for negative numbers")
        if n == 0 or n == 1:
            return 1
        return n * self.factorial(n - 1)
    
    def process_list(self, numbers):
        return [n**2 if n % 2 == 0 else n*3 for n in numbers]

calc = Calculator()
print(calc.add(10, 20))
print(calc.factorial(5))
print(calc.process_list([1, 2, 3, 4, 5]))
"""
    
    else:  # complex
        return """
import asyncio
import threading
from typing import List, Dict, Optional, Union
from dataclasses import dataclass

@dataclass
class DataPoint:
    x: float
    y: float
    label: Optional[str] = None
    
class DataProcessor:
    def __init__(self, thread_count: int = 4):
        self.thread_count = thread_count
        self.data: List[DataPoint] = []
        
    async def process_async(self, data: List[DataPoint]) -> Dict[str, float]:
        tasks = []
        chunk_size = len(data) // self.thread_count
        
        for i in range(self.thread_count):
            start = i * chunk_size
            if i < self.thread_count - 1:
                end = start + chunk_size
            else:
                end = len(data)
            chunk = data[start:end]
            tasks.append(asyncio.create_task(self._process_chunk(chunk)))
        
        results = await asyncio.gather(*tasks)
        return self._merge_results(results)
    
    async def _process_chunk(self, chunk: List[DataPoint]) -> Dict[str, float]:
        await asyncio.sleep(0.01)  # Simulate work
        return {
            'sum_x': sum(p.x for p in chunk),
            'sum_y': sum(p.y for p in chunk),
            'count': len(chunk)
        }
    
    def _merge_results(self, results):
        total_x = sum(r['sum_x'] for r in results)
        total_y = sum(r['sum_y'] for r in results)
        total_count = sum(r['count'] for r in results)
        
        return {
            'mean_x': total_x / total_count if total_count > 0 else 0,
            'mean_y': total_y / total_count if total_count > 0 else 0,
            'total_points': total_count
        }

# Test the processor
async def main():
    processor = DataProcessor()
    data = [DataPoint(x=i, y=i*2) for i in range(1000)]
    result = await processor.process_async(data)
    print(result)

if __name__ == "__main__":
    asyncio.run(main())
"""


class TestASTCachePerformance:
    """Test AST cache performance improvements"""
    
    def test_cache_hit_performance(self):
        """Test performance improvement with cache hits"""
        code = generate_python_code('complex')
        cache = ASTCache(max_size=100, ttl_seconds=300)
        
        # First parse (cache miss)
        metrics1 = PerformanceMetrics()
        metrics1.start()
        
        for _ in range(10):
            cache.parse(code)
        
        metrics1.stop()
        cache.get_stats()  # First stats check
        
        # Second run (cache hits)
        metrics2 = PerformanceMetrics()
        metrics2.start()
        
        for _ in range(100):
            cache.parse(code)  # Use cache
        
        metrics2.stop()
        stats2 = cache.get_stats()
        
        # Cache should provide significant speedup
        time1 = metrics1.metrics['execution_time']
        time2 = metrics2.metrics['execution_time']
        speedup = time1 / time2 if time2 > 0 else 0
        
        print("\nCache Performance Test:")
        print(f"First run (10 parses): {time1:.3f}s")
        print(f"Second run (100 parses): {time2:.3f}s")
        print(f"Speedup: {speedup:.1f}x")
        print(f"Cache hit rate: {stats2['hit_rate']}%")
        
        assert stats2['hit_rate'] > 90  # High hit rate
        assert speedup > 5  # At least 5x speedup
    
    def test_ttl_eviction_performance(self):
        """Test TTL-based eviction performance"""
        cache = ASTCache(max_size=1000, ttl_seconds=0.1)  # 100ms TTL
        
        # Add entries
        for i in range(100):
            code = f"x = {i}"
            cache.parse(code)
        
        initial_size = len(cache)
        
        # Wait for TTL expiry
        time.sleep(0.2)
        
        # Access should trigger cleanup
        cache.parse("y = 1")
        
        # Check cleanup happened
        final_size = len(cache)
        
        print("\nTTL Eviction Test:")
        print(f"Initial cache size: {initial_size}")
        print(f"Final cache size: {final_size}")
        
        assert final_size < initial_size
    
    def test_memory_limit_performance(self):
        """Test memory-based eviction performance"""
        cache = ASTCache(max_size=1000, max_memory_mb=1.0)  # 1MB limit
        
        metrics = PerformanceMetrics()
        metrics.start()
        
        # Add entries until memory limit
        added_count = 0
        for i in range(1000):
            code = generate_python_code('complex') + f"\n# Unique {i}"
            cache.parse(code)
            added_count += 1
            
            # Check if evictions started
            stats = cache.get_stats()
            if stats['size_evictions'] > 0:
                break
        
        metrics.stop()
        stats = cache.get_stats()
        
        print("\nMemory Limit Test:")
        print(f"Added {added_count} entries before eviction")
        print(f"Memory usage: {stats['memory_usage_mb']:.2f}MB")
        print(f"Size evictions: {stats['size_evictions']}")
        
        assert stats['size_evictions'] > 0  # Evictions occurred
        assert stats['memory_usage_mb'] <= 1.5  # Within reasonable limit


class TestParallelProcessing:
    """Test parallel processing performance"""
    
    def setup_method(self):
        """Create test files"""
        self.test_dir = tempfile.mkdtemp()
        self.test_files = []
        
        # Create test files
        for i in range(20):
            file_path = Path(self.test_dir) / f"test_{i}.pseudo"
            content = generate_pseudocode('medium')
            file_path.write_text(content)
            self.test_files.append(file_path)
    
    def teardown_method(self):
        """Clean up test files"""
        import shutil
        shutil.rmtree(self.test_dir)
    
    def test_parallel_vs_sequential_performance(self):
        """Compare parallel vs sequential processing"""
        config = TranslatorConfig()
        
        # Sequential processing
        processor_seq = ParallelProcessor(
            config, 
            mode=ProcessingMode.THREAD,
            max_workers=1
        )
        
        metrics_seq = PerformanceMetrics()
        metrics_seq.start()
        processor_seq.process_files(self.test_files)
        metrics_seq.stop()
        
        # Parallel processing
        processor_par = ParallelProcessor(
            config,
            mode=ProcessingMode.THREAD,
            max_workers=4
        )
        
        metrics_par = PerformanceMetrics()
        metrics_par.start()
        results_par = processor_par.process_files(self.test_files)
        metrics_par.stop()
        
        # Calculate speedup
        speedup = (
            metrics_seq.metrics['execution_time'] / 
            metrics_par.metrics['execution_time']
        )
        
        print("\nParallel Processing Test:")
        print(f"Sequential time: {metrics_seq.metrics['execution_time']:.3f}s")
        print(f"Parallel time: {metrics_par.metrics['execution_time']:.3f}s")
        print(f"Speedup: {speedup:.2f}x")
        print(f"Files processed: {len(self.test_files)}")
        
        assert speedup > 1.5  # At least 1.5x speedup
        assert len(results_par) == len(self.test_files)
    
    def test_hybrid_mode_performance(self):
        """Test hybrid processing mode"""
        config = TranslatorConfig()
        
        # Add some large files
        for i in range(5):
            file_path = Path(self.test_dir) / f"large_{i}.pseudo"
            content = generate_pseudocode('large')
            file_path.write_text(content)
            self.test_files.append(file_path)
        
        processor = ParallelProcessor(
            config,
            mode=ProcessingMode.HYBRID
        )
        
        metrics = PerformanceMetrics()
        metrics.start()
        
        processor.process_files(self.test_files)
        
        metrics.stop()
        stats = processor.get_statistics()
        
        print("\nHybrid Mode Test:")
        print(f"Total files: {stats['files_processed']}")
        print(f"Success rate: {stats['success_rate']:.1f}%")
        print(f"Avg time per file: {stats['avg_time_per_file']:.3f}s")
        
        assert stats['success_rate'] > 90


class TestStreamingPerformance:
    """Test streaming performance for large files"""
    
    def test_streaming_vs_regular_performance(self):
        """Compare streaming vs regular processing for large files"""
        config = TranslatorConfig()
        large_code = generate_pseudocode('huge')
        
        # Regular processing
        translator = TranslationManager(config)
        
        metrics_regular = PerformanceMetrics()
        metrics_regular.start()
        
        translator.translate_pseudocode(large_code)
        
        metrics_regular.stop()
        translator.shutdown()
        
        # Streaming processing
        pipeline = StreamingPipeline(config)
        
        metrics_stream = PerformanceMetrics()
        metrics_stream.start()
        
        chunks_processed = 0
        for chunk_result in pipeline.stream_translate(large_code):
            chunks_processed += 1
        
        metrics_stream.stop()
        
        print("\nStreaming Performance Test:")
        reg_time = metrics_regular.metrics['execution_time']
        reg_mem = metrics_regular.metrics['memory_used']
        stream_time = metrics_stream.metrics['execution_time']
        stream_mem = metrics_stream.metrics['memory_used']
        print(f"Regular processing: {reg_time:.3f}s")
        print(f"Regular memory: {reg_mem:.1f}MB")
        print(f"Streaming processing: {stream_time:.3f}s")
        print(f"Streaming memory: {stream_mem:.1f}MB")
        print(f"Chunks processed: {chunks_processed}")
        
        # Streaming should use less memory
        # Streaming should use less memory
        assert stream_mem < reg_mem
    
    def test_streaming_progress_tracking(self):
        """Test streaming progress tracking"""
        config = TranslatorConfig()
        code = generate_pseudocode('large')
        
        pipeline = StreamingPipeline(config)
        progress_updates = []
        
        def track_progress(progress):
            progress_updates.append({
                'percentage': progress.progress_percentage,
                'chunks': progress.processed_chunks
            })
        
        list(pipeline.stream_translate(code, progress_callback=track_progress))
        
        print("\nProgress Tracking Test:")
        print(f"Progress updates: {len(progress_updates)}")
        if progress_updates:
            print(f"Final progress: {progress_updates[-1]['percentage']:.1f}%")
        
        assert len(progress_updates) > 0
        assert progress_updates[-1]['percentage'] == 100.0


class TestValidatorPerformance:
    """Test validator performance optimizations"""
    
    def test_validation_caching(self):
        """Test validation result caching"""
        config = TranslatorConfig()
        validator = Validator(config)
        code = generate_python_code('complex')
        
        # First validation (no cache)
        metrics1 = PerformanceMetrics()
        metrics1.start()
        
        for _ in range(10):
            validator.validate_syntax(code)
        
        metrics1.stop()
        
        # Second validation (with cache)
        metrics2 = PerformanceMetrics()
        metrics2.start()
        
        for _ in range(100):
            validator.validate_syntax(code)
        
        metrics2.stop()
        
        speedup = (
            (metrics1.metrics['execution_time'] * 10) /
            metrics2.metrics['execution_time']
        )
        
        print("\nValidation Caching Test:")
        time1 = metrics1.metrics['execution_time']
        time2 = metrics2.metrics['execution_time']
        print(f"First run (10 validations): {time1:.3f}s")
        print(f"Second run (100 validations): {time2:.3f}s")
        print(f"Speedup: {speedup:.1f}x")
        
        assert speedup > 5  # Significant speedup from caching
    
    def test_optimized_pattern_matching(self):
        """Test optimized regex pattern matching"""
        config = TranslatorConfig()
        validator = Validator(config)
        
        # Generate code with many patterns to check
        code_lines = []
        for i in range(1000):
            code_lines.append("try:")
            code_lines.append(f"    x = {i}")
            code_lines.append("except:")  # Bare except
            code_lines.append("    pass")
            code_lines.append("import *")  # Wildcard import
            code_lines.append(f"global var_{i}")  # Global usage
        
        code = '\n'.join(code_lines)
        
        metrics = PerformanceMetrics()
        metrics.start()
        
        result = validator.validate_syntax(code)
        
        metrics.stop()
        
        print("\nPattern Matching Test:")
        print(f"Code size: {len(code)} chars")
        print(f"Validation time: {metrics.metrics['execution_time']:.3f}s")
        print(f"Issues found: {len(result.warnings)}")
        
        # Should complete quickly despite large code
        assert metrics.metrics['execution_time'] < 1.0


class TestEndToEndPerformance:
    """Test end-to-end translation performance"""
    
    def test_complete_translation_performance(self):
        """Test complete translation pipeline performance"""
        config = TranslatorConfig()
        
        test_cases = [
            ('small', generate_pseudocode('small')),
            ('medium', generate_pseudocode('medium')),
            ('large', generate_pseudocode('large'))
        ]
        
        results = {}
        
        for name, code in test_cases:
            translator = TranslationManager(config)
            
            metrics = PerformanceMetrics()
            metrics.start()
            
            result = translator.translate_pseudocode(code)
            
            metrics.stop()
            cache_stats = get_cache_stats()
            
            translator.shutdown()
            
            results[name] = {
                'time': metrics.metrics['execution_time'],
                'memory': metrics.metrics['memory_used'],
                'success': result.success,
                'cache_hits': cache_stats['hits']
            }
        
        print("\nEnd-to-End Performance Test:")
        for name, result in results.items():
            print(f"\n{name.capitalize()} code:")
            print(f"  Time: {result['time']:.3f}s")
            print(f"  Memory: {result['memory']:.1f}MB")
            print(f"  Success: {result['success']}")
            print(f"  Cache hits: {result['cache_hits']}")
        
        # All should succeed
        assert all(r['success'] for r in results.values())
        
        # Time should scale reasonably
        assert results['large']['time'] < results['small']['time'] * 20
    
    def test_performance_under_load(self):
        """Test performance under concurrent load"""
        config = TranslatorConfig()
        code = generate_pseudocode('medium')
        
        results = []
        errors = []
        
        def translate_task():
            try:
                translator = TranslationManager(config)
                start = time.time()
                result = translator.translate_pseudocode(code)
                end = time.time()
                translator.shutdown()
                
                results.append({
                    'time': end - start,
                    'success': result.success
                })
            except Exception as e:
                errors.append(str(e))
        
        # Run concurrent translations
        threads = []
        thread_count = 10
        
        start_time = time.time()
        
        for _ in range(thread_count):
            t = threading.Thread(target=translate_task)
            threads.append(t)
            t.start()
        
        for t in threads:
            t.join()
        
        total_time = time.time() - start_time
        
        # Calculate statistics
        avg_time = 0.0
        std_dev = 0.0
        if results:
            times = [r['time'] for r in results]
            avg_time = statistics.mean(times)
            std_dev = statistics.stdev(times) if len(times) > 1 else 0
        
        print("\nConcurrent Load Test:")
        print(f"Threads: {thread_count}")
        print(f"Total time: {total_time:.3f}s")
        print(f"Successful: {len(results)}")
        print(f"Errors: {len(errors)}")
        if results:
            print(f"Avg time per translation: {avg_time:.3f}s")
            print(f"Std deviation: {std_dev:.3f}s")
        
        assert len(results) >= thread_count * 0.8  # At least 80% success
        assert len(errors) < thread_count * 0.2  # Less than 20% errors


def run_performance_suite():
    """Run the complete performance test suite"""
    print("=" * 60)
    print("Pseudocode Translator Performance Test Suite")
    print("=" * 60)
    
    test_classes = [
        TestASTCachePerformance,
        TestParallelProcessing,
        TestStreamingPerformance,
        TestValidatorPerformance,
        TestEndToEndPerformance
    ]
    
    for test_class in test_classes:
        print(f"\n\nRunning {test_class.__name__}...")
        print("-" * 40)
        
        instance = test_class()
        
        # Run all test methods
        for method_name in dir(instance):
            if method_name.startswith('test_'):
                method = getattr(instance, method_name)
                
                # Setup if needed
                if hasattr(instance, 'setup_method'):
                    instance.setup_method()
                
                try:
                    print(f"\nRunning {method_name}...")
                    method()
                    print(f"✓ {method_name} passed")
                except Exception as e:
                    print(f"✗ {method_name} failed: {e}")
                
                # Teardown if needed
                if hasattr(instance, 'teardown_method'):
                    instance.teardown_method()
    
    print("\n" + "=" * 60)
    print("Performance Test Suite Completed")
    print("=" * 60)


if __name__ == "__main__":
    run_performance_suite()