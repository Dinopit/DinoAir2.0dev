"""
CLI Progress Indicators for DinoAir 2.0
Provides simple progress indicators for command-line operations
"""

import sys
import time
from typing import Optional, Callable, Any


class ProgressBar:
    """Simple progress bar for command-line operations"""
    
    def __init__(self, total: int, width: int = 50, prefix: str = "Progress"):
        self.total = total
        self.width = width
        self.prefix = prefix
        self.current = 0
        self.start_time = time.time()
    
    def update(self, amount: int = 1, suffix: str = ""):
        """Update progress bar"""
        self.current += amount
        if self.current > self.total:
            self.current = self.total
            
        percent = 100 * (self.current / float(self.total))
        filled_length = int(self.width * self.current // self.total)
        bar = '█' * filled_length + '-' * (self.width - filled_length)
        
        elapsed = time.time() - self.start_time
        if self.current > 0 and self.current < self.total:
            eta = elapsed * (self.total - self.current) / self.current
            eta_str = f" ETA: {eta:.1f}s"
        else:
            eta_str = ""
        
        sys.stdout.write(f'\r{self.prefix}: |{bar}| {percent:.1f}% ({self.current}/{self.total}){eta_str} {suffix}')
        sys.stdout.flush()
        
        if self.current >= self.total:
            sys.stdout.write('\n')
    
    def finish(self, message: str = "Complete!"):
        """Finish progress bar with message"""
        self.current = self.total
        self.update(0, message)


class Spinner:
    """Simple spinner for indeterminate progress"""
    
    def __init__(self, message: str = "Working"):
        self.message = message
        self.spinning = False
        self.chars = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"
        self.index = 0
    
    def start(self):
        """Start spinner"""
        self.spinning = True
        self._spin()
    
    def _spin(self):
        """Show spinner animation"""
        if self.spinning:
            sys.stdout.write(f'\r{self.chars[self.index]} {self.message}')
            sys.stdout.flush()
            self.index = (self.index + 1) % len(self.chars)
    
    def stop(self, message: str = "Done!"):
        """Stop spinner with message"""
        self.spinning = False
        sys.stdout.write(f'\r✓ {message}\n')
        sys.stdout.flush()


def with_progress(items, description: str = "Processing", 
                 process_func: Optional[Callable] = None):
    """
    Context manager for processing items with progress bar
    
    Args:
        items: List of items to process
        description: Description for progress bar
        process_func: Optional function to apply to each item
    """
    progress = ProgressBar(len(items), prefix=description)
    
    for i, item in enumerate(items):
        if process_func:
            result = process_func(item)
        else:
            result = item
            
        progress.update(1, f"Item {i+1}")
        
        if process_func:
            yield result
        else:
            yield item
    
    progress.finish()


class StepProgress:
    """Multi-step progress indicator"""
    
    def __init__(self, steps: list[str]):
        self.steps = steps
        self.current_step = 0
        self.total_steps = len(steps)
    
    def next_step(self, status: str = "✓"):
        """Move to next step"""
        if self.current_step < self.total_steps:
            step_name = self.steps[self.current_step]
            print(f"{status} Step {self.current_step + 1}/{self.total_steps}: {step_name}")
            self.current_step += 1
    
    def complete(self):
        """Mark all steps as complete"""
        while self.current_step < self.total_steps:
            self.next_step()
        print("✅ All steps completed!")


# Example usage functions
def demo_progress_bar():
    """Demo progress bar functionality"""
    print("Demo: Progress Bar")
    progress = ProgressBar(100, prefix="Processing")
    
    for i in range(100):
        time.sleep(0.01)  # Simulate work
        progress.update(1, f"Processing item {i+1}")
    
    progress.finish("All items processed!")


def demo_spinner():
    """Demo spinner functionality"""
    print("Demo: Spinner")
    spinner = Spinner("Loading data")
    spinner.start()
    
    # Simulate work
    for _ in range(30):
        time.sleep(0.1)
        spinner._spin()
    
    spinner.stop("Data loaded successfully!")


def demo_step_progress():
    """Demo step progress functionality"""
    print("Demo: Step Progress")
    steps = [
        "Initialize system",
        "Load configuration",
        "Connect to database",
        "Process data", 
        "Generate report"
    ]
    
    progress = StepProgress(steps)
    
    for _ in range(len(steps)):
        time.sleep(0.5)  # Simulate work
        progress.next_step()
    
    progress.complete()


if __name__ == "__main__":
    print("DinoAir CLI Progress Indicators Demo\n")
    
    demo_progress_bar()
    print()
    
    demo_spinner()
    print()
    
    demo_step_progress()