"""
Rate limiting attack testing module.

Tests for DoS vulnerabilities and rate limiting effectiveness.
"""

import time
from typing import List, Tuple, Optional, Callable
from tests.security.core.base_tester import BaseSecurityTester


class RateLimitingTester(BaseSecurityTester):
    """Tests for rate limiting and DoS prevention."""
    
    def __init__(self):
        """Initialize rate limiting tester."""
        super().__init__()
        self.request_times = []
        
    def get_test_name(self) -> str:
        """Get the name of this test category."""
        return "Rate Limiting"
    
    def get_payloads(self) -> List[Tuple[str, str]]:
        """Get rate limiting test scenarios."""
        return [
            # Rapid fire requests
            ("RAPID_FIRE_10", "10 requests in 1 second"),
            ("RAPID_FIRE_50", "50 requests in 1 second"),
            ("RAPID_FIRE_100", "100 requests in 1 second"),
            
            # Sustained load
            ("SUSTAINED_10_PER_SEC", "10 req/sec for 10 seconds"),
            ("SUSTAINED_20_PER_SEC", "20 req/sec for 10 seconds"),
            
            # Burst patterns
            ("BURST_THEN_WAIT", "Burst of 50, wait 5s, repeat"),
            ("INCREASING_RATE", "Gradually increase request rate"),
            
            # Different endpoints
            ("MULTI_ENDPOINT", "Hit multiple endpoints rapidly"),
            ("SINGLE_ENDPOINT", "Focus on single endpoint"),
            
            # Large payloads
            ("LARGE_PAYLOAD_1MB", "1MB payload requests"),
            ("LARGE_PAYLOAD_10MB", "10MB payload requests"),
            
            # Slow requests
            ("SLOWLORIS", "Very slow request completion"),
            ("SLOW_POST", "Slow POST data transmission"),
            
            # Connection flooding
            ("CONN_FLOOD_100", "100 concurrent connections"),
            ("CONN_FLOOD_1000", "1000 concurrent connections"),
            
            # Resource exhaustion
            ("CPU_INTENSIVE", "Requests triggering CPU work"),
            ("MEMORY_INTENSIVE", "Requests using lots of memory"),
        ]
    
    def execute_rate_test(
        self,
        test_type: str,
        target_func: Callable
    ) -> Optional[dict]:
        """Execute specific rate limiting test."""
        
        if test_type.startswith("RAPID_FIRE_"):
            count = int(test_type.split("_")[-1])
            return self._rapid_fire_test(count, target_func)
            
        elif test_type.startswith("SUSTAINED_"):
            rate = int(test_type.split("_")[1])
            return self._sustained_load_test(rate, 10, target_func)
            
        elif test_type == "BURST_THEN_WAIT":
            return self._burst_pattern_test(target_func)
            
        elif test_type == "SLOWLORIS":
            return self._slowloris_test(target_func)
            
        else:
            # For other tests, use base payload testing
            return None
    
    def _rapid_fire_test(
        self,
        count: int,
        target_func: Callable
    ) -> dict:
        """Test rapid fire requests."""
        start_time = time.time()
        successes = 0
        failures = 0
        
        for i in range(count):
            try:
                result = target_func(f"test_request_{i}")
                if result:
                    successes += 1
                else:
                    failures += 1
            except Exception:
                failures += 1
                
        duration = time.time() - start_time
        
        return {
            "test_type": f"RAPID_FIRE_{count}",
            "total_requests": count,
            "successes": successes,
            "failures": failures,
            "duration": duration,
            "requests_per_second": count / duration if duration > 0 else 0
        }
    
    def _sustained_load_test(
        self,
        rate: int,
        duration: int,
        target_func: Callable
    ) -> dict:
        """Test sustained load over time."""
        start_time = time.time()
        request_count = 0
        successes = 0
        failures = 0
        
        while time.time() - start_time < duration:
            batch_start = time.time()
            
            # Send 'rate' requests
            for i in range(rate):
                try:
                    result = target_func(f"sustained_{request_count}")
                    if result:
                        successes += 1
                    else:
                        failures += 1
                    request_count += 1
                except Exception:
                    failures += 1
                    request_count += 1
            
            # Wait for remainder of the second
            elapsed = time.time() - batch_start
            if elapsed < 1.0:
                time.sleep(1.0 - elapsed)
                
        total_duration = time.time() - start_time
        
        return {
            "test_type": f"SUSTAINED_{rate}_PER_SEC",
            "total_requests": request_count,
            "successes": successes,
            "failures": failures,
            "duration": total_duration,
            "target_rate": rate,
            "actual_rate": request_count / total_duration
        }
    
    def _burst_pattern_test(self, target_func: Callable) -> dict:
        """Test burst pattern attacks."""
        results = []
        
        for burst_num in range(3):
            # Send burst
            burst_result = self._rapid_fire_test(50, target_func)
            results.append(burst_result)
            
            # Wait between bursts
            time.sleep(5)
            
        return {
            "test_type": "BURST_PATTERN",
            "bursts": results,
            "total_requests": sum(r["total_requests"] for r in results),
            "total_successes": sum(r["successes"] for r in results),
            "total_failures": sum(r["failures"] for r in results)
        }
    
    def _slowloris_test(self, target_func: Callable) -> dict:
        """Test slowloris-style attack."""
        # Simulate slow request by sending data very slowly
        slow_payload = "X" * 1000  # 1KB payload
        chunks = [slow_payload[i:i+10]
                  for i in range(0, len(slow_payload), 10)]
        
        start_time = time.time()
        success = True
        
        try:
            # Send chunks slowly
            for chunk in chunks:
                target_func(chunk)
                time.sleep(0.5)  # 500ms between chunks
        except Exception:
            success = False
            
        duration = time.time() - start_time
        
        return {
            "test_type": "SLOWLORIS",
            "success": success,
            "duration": duration,
            "chunks_sent": len(chunks),
            "total_bytes": len(slow_payload)
        }