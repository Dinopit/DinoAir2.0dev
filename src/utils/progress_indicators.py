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
        """
        Initialize the progress bar.
        
        Parameters:
            total (int): Total number of steps/items the bar represents.
            width (int): Visual width (number of characters) of the bar in the terminal.
            prefix (str): Text shown before the bar (e.g., "Progress").
        
        The initializer sets the current progress to 0 and records the start time for ETA calculations.
        """
        self.total = total
        self.width = width
        self.prefix = prefix
        self.current = 0
        self.start_time = time.time()
    
    def update(self, amount: int = 1, suffix: str = ""):
        """
        Advance the progress bar display by a given amount and redraw it on stdout.
        
        Updates the internal progress counter (clamped to the configured total), recomputes
        the rendered bar and percentage, and writes an in-place progress line to stdout.
        When progress is between 0 and total an ETA (in seconds) is shown; when the total
        is reached a final newline is written.
        
        Parameters:
            amount (int): Number of units to advance the current progress (default 1).
            suffix (str): Optional text appended to the progress line (default "").
        
        Side effects:
            Writes the progress line to stdout and flushes it. Prints a terminating
            newline when progress reaches or exceeds the total. No value is returned.
        """
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
        """
        Mark the progress bar as complete and render a final line with the given message.
        
        Sets the current progress to the total and calls update to print the completed bar and message. `message` is shown as the suffix on the final line.
        """
        self.current = self.total
        self.update(0, message)


class Spinner:
    """Simple spinner for indeterminate progress"""
    
    def __init__(self, message: str = "Working"):
        """
        Initialize the spinner.
        
        Parameters:
            message (str): Text displayed next to the spinner frames (default: "Working").
        
        Description:
            Sets up spinner state including the display message, spinning flag, spinner frame characters,
            and the current frame index.
        """
        self.message = message
        self.spinning = False
        self.chars = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"
        self.index = 0
    
    def start(self):
        """
        Start the spinner animation.
        
        Sets the spinner to a running state and emits the initial spinner frame. Call stop() to end the spinner and print the final message. This method does not block.
        """
        self.spinning = True
        self._spin()
    
    def _spin(self):
        """
        Advance and render a single spinner frame to stdout when spinning.
        
        Writes the next spinner character and the current message in-place (carriage return),
        flushes stdout, and advances the internal frame index (wrapping around).
        No return value.
        """
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
                 Yield items from a collection while displaying a textual progress bar.
                 
                 This function is a generator that iterates over `items`, updates a ProgressBar for each element,
                 and yields either the original item or the value returned by `process_func(item)` if provided.
                 Note: `items` must be a sized iterable (i.e., support len()) because the progress bar is
                 initialized with the collection's length. Progress output is written to stdout.
                 
                 Parameters that need clarification:
                 - process_func: Optional callable applied to each item; its return value is yielded when present.
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
        """
        Initialize a StepProgress with an ordered list of step names.
        
        Parameters:
            steps: List of step names in the order they should be executed; used to track progress and display each step's label.
        """
        self.steps = steps
        self.current_step = 0
        self.total_steps = len(steps)
    
    def next_step(self, status: str = "✓"):
        """
        Advance to the next step and print its status.
        
        If there are remaining steps, prints a single line of the form
        `<status> Step N/T: <step_name>` to stdout and increments the internal step index.
        If all steps are already completed, the method does nothing.
        
        Parameters:
            status (str): Marker shown before the step (e.g., "✓", ">", or "✖"). Default is "✓".
        """
        if self.current_step < self.total_steps:
            step_name = self.steps[self.current_step]
            print(f"{status} Step {self.current_step + 1}/{self.total_steps}: {step_name}")
            self.current_step += 1
    
    def complete(self):
        """
        Advance through and mark all remaining steps as completed.
        
        Calls next_step() repeatedly for any remaining steps (using its default status),
        printing each step as it completes, then prints a final "All steps completed!" message.
        """
        while self.current_step < self.total_steps:
            self.next_step()
        print("✅ All steps completed!")


# Example usage functions
def demo_progress_bar():
    """
    Demonstrate the ProgressBar by running a 100-step simulated task and printing the progress to stdout.
    
    Runs a ProgressBar with a 100-item workload, sleeping briefly between steps to simulate work, updates the bar for each item, and finishes with a final message. This function is intended for interactive/demo use and writes output directly to stdout.
    """
    print("Demo: Progress Bar")
    progress = ProgressBar(100, prefix="Processing")
    
    for i in range(100):
        time.sleep(0.01)  # Simulate work
        progress.update(1, f"Processing item {i+1}")
    
    progress.finish("All items processed!")


def demo_spinner():
    """
    Demonstrate the Spinner utility by running a short simulated workload with a CLI spinner.
    
    This function prints a heading, starts a Spinner labeled "Loading data", performs a brief simulated task while advancing spinner frames, then stops the spinner with a success message. Intended for interactive/demo use only; it writes progress to stdout and blocks while sleeping.
    """
    print("Demo: Spinner")
    spinner = Spinner("Loading data")
    spinner.start()
    
    # Simulate work
    for _ in range(30):
        time.sleep(0.1)
        spinner._spin()
    
    spinner.stop("Data loaded successfully!")


def demo_step_progress():
    """
    Demonstrate the StepProgress indicator with a fixed sequence of steps.
    
    Runs a short illustrative sequence of steps ("Initialize system", "Load configuration",
    "Connect to database", "Process data", "Generate report"), advancing the StepProgress
    instance for each step with a brief simulated delay, then marks completion. Intended
    for CLI demonstration; prints progress lines to stdout and does not return a value.
    """
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