#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Smart Timer Module
Implements a smart timer that can track time spent on various tasks.
Features include starting, stopping, resetting the timer, and running repeats.
"""

import time


class SmartTimer:
    """Smart timer for tracking time spent on tasks."""
    def __init__(self, name):
        self.name = name
        self.start_time = None
        self.elapsed_time = 0
        self.running = False
        self.logs = []

    def start(self):
        if not self.running:
            self.start_time = time.time()
            self.running = True

    def stop(self):
        if self.running and self.start_time is not None:
            elapsed = time.time() - self.start_time
            self.elapsed_time += elapsed
            self.logs.append(elapsed)
            self.start_time = None
            self.running = False

    def reset(self):
        self.start_time = None
        self.elapsed_time = 0
        self.running = False
        self.logs = []

    def get_elapsed_time(self):
        if self.running and self.start_time is not None:
            return self.elapsed_time + (time.time() - self.start_time)
        return self.elapsed_time

    def get_logs(self):
        return self.logs

    def run_repeats(self, repeats, duration_per_run):
        """Run the timer for a specified number of repeats.
        
        Args:
            repeats: Number of times to run the timer
            duration_per_run: Duration in seconds for each run
        """
        for _ in range(repeats):
            self.start()
            time.sleep(duration_per_run)
            self.stop()
    
    def __enter__(self):
        """Context manager entry - starts the timer"""
        self.start()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - stops the timer"""
        self.stop()
        return False


class TimerManager:
    """Manager for multiple timers."""
    def __init__(self):
        self.timers = {}

    def create_timer(self, task_name):
        if task_name not in self.timers:
            self.timers[task_name] = SmartTimer(task_name)

    def get_timer(self, task_name):
        return self.timers.get(task_name)

    def remove_timer(self, task_name):
        if task_name in self.timers:
            del self.timers[task_name]

    def list_timers(self):
        """Get a list of all timer names.
        
        Returns:
            List of timer names
        """
        return list(self.timers.keys())
