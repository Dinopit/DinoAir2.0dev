"""Watchdog command handler module.

Extracts and modularizes watchdog-related command processing
from the original InputSanitizer implementation.
"""

from typing import Dict, Callable, Optional, Any, Tuple
from dataclasses import dataclass
import re


@dataclass
class CommandResult:
    """Result of command execution."""
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None
    should_display_in_chat: bool = True


class WatchdogCommandHandler:
    """Handles watchdog-related commands.
    
    This class encapsulates all watchdog command logic that was
    previously embedded in the InputSanitizer class.
    """
    
    def __init__(self, watchdog=None, chat_callback=None):
        """Initialize with watchdog instance.
        
        Args:
            watchdog: SystemWatchdog instance
            chat_callback: Callback for displaying messages in chat
        """
        self.watchdog = watchdog
        self.chat_callback = chat_callback
        
        # Command patterns
        self.command_patterns = {
            r'^watchdog\s+status$': self.handle_status,
            r'^watchdog\s+start$': self.handle_start,
            r'^watchdog\s+stop$': self.handle_stop,
            r'^watchdog\s+restart$': self.handle_restart,
            r'^watchdog\s+pause$': self.handle_pause,
            r'^watchdog\s+resume$': self.handle_resume,
            r'^watchdog\s+set\s+threshold\s+(\w+)\s+(\d+(?:\.\d+)?)$': self.handle_set_threshold,
            r'^watchdog\s+get\s+threshold\s+(\w+)$': self.handle_get_threshold,
            r'^watchdog\s+list\s+thresholds$': self.handle_list_thresholds,
            r'^watchdog\s+kill\s+(.+)$': self.handle_kill_process,
            r'^watchdog\s+metrics$': self.handle_metrics,
            r'^watchdog\s+history\s*(\d*)$': self.handle_history,
            r'^watchdog\s+clear\s+history$': self.handle_clear_history,
            r'^watchdog\s+help$': self.handle_help,
        }
        
        # Threshold names for validation
        self.valid_thresholds = {
            'vram', 'ram', 'cpu', 'response_time',
            'check_interval', 'history_size'
        }
    
    def can_handle(self, command: str) -> bool:
        """Check if this handler can process the command.
        
        Args:
            command: Command string to check
            
        Returns:
            True if this handler can process the command
        """
        command_lower = command.lower().strip()
        return any(re.match(pattern, command_lower) 
                  for pattern in self.command_patterns)
    
    def handle_command(self, command: str) -> CommandResult:
        """Handle a watchdog command.
        
        Args:
            command: Command string to process
            
        Returns:
            CommandResult with execution results
        """
        if not self.watchdog:
            return CommandResult(
                success=False,
                message="❌ Watchdog not initialized. Cannot process commands."
            )
        
        command_lower = command.lower().strip()
        
        # Find matching pattern and execute handler
        for pattern, handler in self.command_patterns.items():
            match = re.match(pattern, command_lower)
            if match:
                # Extract arguments from regex groups
                args = match.groups() if match.groups() else ()
                return handler(*args)
        
        return CommandResult(
            success=False,
            message=f"❌ Unknown watchdog command: {command}"
        )
    
    def handle_status(self) -> CommandResult:
        """Handle watchdog status command."""
        try:
            metrics = self.watchdog.get_current_metrics()
            
            if metrics:
                status_lines = ["📊 **Watchdog Status**\n"]
                status_lines.append(f"**Status:** {'🟢 Running' if self.watchdog.monitoring else '🔴 Stopped'}")
                status_lines.append(f"**VRAM:** {metrics['vram_percent']:.1f}% ({metrics['vram_used']:.1f}/{metrics['vram_total']:.1f} GB)")
                status_lines.append(f"**RAM:** {metrics['ram_percent']:.1f}% ({metrics['ram_used']:.1f}/{metrics['ram_total']:.1f} GB)")
                status_lines.append(f"**CPU:** {metrics['cpu_percent']:.1f}%")
                
                return CommandResult(
                    success=True,
                    message="\n".join(status_lines),
                    data={'metrics': metrics}
                )
            else:
                return CommandResult(
                    success=False,
                    message="⚠️ No metrics available. Watchdog may be initializing."
                )
        except Exception as e:
            return CommandResult(
                success=False,
                message=f"❌ Error getting status: {str(e)}"
            )
    
    def handle_start(self) -> CommandResult:
        """Handle watchdog start command."""
        try:
            if self.watchdog.monitoring:
                return CommandResult(
                    success=True,
                    message="ℹ️ Watchdog is already running."
                )
            
            self.watchdog.start_monitoring()
            return CommandResult(
                success=True,
                message="✅ Watchdog monitoring started."
            )
        except Exception as e:
            return CommandResult(
                success=False,
                message=f"❌ Error starting watchdog: {str(e)}"
            )
    
    def handle_stop(self) -> CommandResult:
        """Handle watchdog stop command."""
        try:
            if not self.watchdog.monitoring:
                return CommandResult(
                    success=True,
                    message="ℹ️ Watchdog is already stopped."
                )
            
            self.watchdog.stop_monitoring()
            return CommandResult(
                success=True,
                message="✅ Watchdog monitoring stopped."
            )
        except Exception as e:
            return CommandResult(
                success=False,
                message=f"❌ Error stopping watchdog: {str(e)}"
            )
    
    def handle_restart(self) -> CommandResult:
        """Handle watchdog restart command."""
        try:
            self.watchdog.stop_monitoring()
            self.watchdog.start_monitoring()
            return CommandResult(
                success=True,
                message="✅ Watchdog restarted successfully."
            )
        except Exception as e:
            return CommandResult(
                success=False,
                message=f"❌ Error restarting watchdog: {str(e)}"
            )
    
    def handle_pause(self) -> CommandResult:
        """Handle watchdog pause command."""
        try:
            if not self.watchdog.monitoring:
                return CommandResult(
                    success=False,
                    message="❌ Cannot pause - watchdog is not running."
                )
            
            # Pause functionality would need to be implemented in Watchdog
            # For now, we'll stop monitoring
            self.watchdog.stop_monitoring()
            return CommandResult(
                success=True,
                message="⏸️ Watchdog monitoring paused."
            )
        except Exception as e:
            return CommandResult(
                success=False,
                message=f"❌ Error pausing watchdog: {str(e)}"
            )
    
    def handle_resume(self) -> CommandResult:
        """Handle watchdog resume command."""
        try:
            if self.watchdog.monitoring:
                return CommandResult(
                    success=True,
                    message="ℹ️ Watchdog is already running."
                )
            
            self.watchdog.start_monitoring()
            return CommandResult(
                success=True,
                message="▶️ Watchdog monitoring resumed."
            )
        except Exception as e:
            return CommandResult(
                success=False,
                message=f"❌ Error resuming watchdog: {str(e)}"
            )
    
    def handle_set_threshold(self, threshold_name: str, value: str) -> CommandResult:
        """Handle setting a threshold value.
        
        Args:
            threshold_name: Name of threshold to set
            value: New value for threshold
        """
        try:
            if threshold_name not in self.valid_thresholds:
                return CommandResult(
                    success=False,
                    message=f"❌ Invalid threshold: '{threshold_name}'. Valid options: {', '.join(self.valid_thresholds)}"
                )
            
            float_value = float(value)
            
            # Validate ranges
            if threshold_name in ['vram', 'ram', 'cpu'] and not 0 <= float_value <= 100:
                return CommandResult(
                    success=False,
                    message=f"❌ {threshold_name} threshold must be between 0 and 100"
                )
            
            # Set the threshold (this would need implementation in Watchdog)
            if hasattr(self.watchdog, f'set_{threshold_name}_threshold'):
                setter = getattr(self.watchdog, f'set_{threshold_name}_threshold')
                setter(float_value)
            else:
                # Fallback to modifying thresholds dict if available
                if hasattr(self.watchdog, 'thresholds'):
                    self.watchdog.thresholds[threshold_name] = float_value
                else:
                    return CommandResult(
                        success=False,
                        message=f"❌ Cannot set {threshold_name} threshold - method not available"
                    )
            
            return CommandResult(
                success=True,
                message=f"✅ {threshold_name} threshold set to {float_value}"
            )
        except ValueError:
            return CommandResult(
                success=False,
                message=f"❌ Invalid value: '{value}' is not a number"
            )
        except Exception as e:
            return CommandResult(
                success=False,
                message=f"❌ Error setting threshold: {str(e)}"
            )
    
    def handle_get_threshold(self, threshold_name: str) -> CommandResult:
        """Handle getting a threshold value.
        
        Args:
            threshold_name: Name of threshold to get
        """
        try:
            if threshold_name not in self.valid_thresholds:
                return CommandResult(
                    success=False,
                    message=f"❌ Invalid threshold: '{threshold_name}'. Valid options: {', '.join(self.valid_thresholds)}"
                )
            
            # Get the threshold value
            if hasattr(self.watchdog, 'thresholds') and threshold_name in self.watchdog.thresholds:
                value = self.watchdog.thresholds[threshold_name]
                return CommandResult(
                    success=True,
                    message=f"📊 {threshold_name} threshold: {value}"
                )
            else:
                return CommandResult(
                    success=False,
                    message=f"❌ Cannot get {threshold_name} threshold"
                )
        except Exception as e:
            return CommandResult(
                success=False,
                message=f"❌ Error getting threshold: {str(e)}"
            )
    
    def handle_list_thresholds(self) -> CommandResult:
        """Handle listing all thresholds."""
        try:
            if hasattr(self.watchdog, 'thresholds'):
                lines = ["📊 **Current Thresholds:**"]
                for name, value in self.watchdog.thresholds.items():
                    lines.append(f"  • {name}: {value}")
                
                return CommandResult(
                    success=True,
                    message="\n".join(lines)
                )
            else:
                return CommandResult(
                    success=False,
                    message="❌ Threshold information not available"
                )
        except Exception as e:
            return CommandResult(
                success=False,
                message=f"❌ Error listing thresholds: {str(e)}"
            )
    
    def handle_kill_process(self, process_name: str) -> CommandResult:
        """Handle killing a process.
        
        Args:
            process_name: Name or PID of process to kill
        """
        try:
            # Check if it's a PID
            try:
                pid = int(process_name)
                if hasattr(self.watchdog, 'kill_process_by_pid'):
                    success = self.watchdog.kill_process_by_pid(pid)
                    if success:
                        return CommandResult(
                            success=True,
                            message=f"✅ Killed process with PID {pid}"
                        )
                    else:
                        return CommandResult(
                            success=False,
                            message=f"❌ Failed to kill process with PID {pid}"
                        )
            except ValueError:
                # Not a PID, treat as process name
                if hasattr(self.watchdog, 'kill_process_by_name'):
                    killed_count = self.watchdog.kill_process_by_name(process_name)
                    if killed_count > 0:
                        return CommandResult(
                            success=True,
                            message=f"✅ Killed {killed_count} process(es) named '{process_name}'"
                        )
                    else:
                        return CommandResult(
                            success=False,
                            message=f"❌ No processes found with name '{process_name}'"
                        )
            
            return CommandResult(
                success=False,
                message="❌ Process killing not supported by current watchdog"
            )
        except Exception as e:
            return CommandResult(
                success=False,
                message=f"❌ Error killing process: {str(e)}"
            )
    
    def handle_metrics(self) -> CommandResult:
        """Handle showing current metrics."""
        return self.handle_status()  # Reuse status handler
    
    def handle_history(self, count: str = "10") -> CommandResult:
        """Handle showing metrics history.
        
        Args:
            count: Number of history entries to show
        """
        try:
            num_entries = int(count) if count else 10
            
            if hasattr(self.watchdog, 'get_metrics_history'):
                history = self.watchdog.get_metrics_history(num_entries)
                if history:
                    lines = [f"📊 **Last {num_entries} Metrics Entries:**"]
                    for entry in history:
                        timestamp = entry.get('timestamp', 'Unknown time')
                        lines.append(f"\n**{timestamp}**")
                        lines.append(f"  VRAM: {entry['vram_percent']:.1f}%")
                        lines.append(f"  RAM: {entry['ram_percent']:.1f}%")
                        lines.append(f"  CPU: {entry['cpu_percent']:.1f}%")
                    
                    return CommandResult(
                        success=True,
                        message="\n".join(lines)
                    )
                else:
                    return CommandResult(
                        success=True,
                        message="ℹ️ No metrics history available"
                    )
            else:
                return CommandResult(
                    success=False,
                    message="❌ Metrics history not available"
                )
        except ValueError:
            return CommandResult(
                success=False,
                message=f"❌ Invalid count: '{count}' is not a number"
            )
        except Exception as e:
            return CommandResult(
                success=False,
                message=f"❌ Error getting history: {str(e)}"
            )
    
    def handle_clear_history(self) -> CommandResult:
        """Handle clearing metrics history."""
        try:
            if hasattr(self.watchdog, 'clear_metrics_history'):
                self.watchdog.clear_metrics_history()
                return CommandResult(
                    success=True,
                    message="✅ Metrics history cleared"
                )
            else:
                return CommandResult(
                    success=False,
                    message="❌ Cannot clear history - method not available"
                )
        except Exception as e:
            return CommandResult(
                success=False,
                message=f"❌ Error clearing history: {str(e)}"
            )
    
    def handle_help(self) -> CommandResult:
        """Handle help command."""
        help_text = """
🐕 **Watchdog Commands:**

**Basic Control:**
• `watchdog start` - Start monitoring
• `watchdog stop` - Stop monitoring
• `watchdog restart` - Restart monitoring
• `watchdog pause` - Pause monitoring
• `watchdog resume` - Resume monitoring
• `watchdog status` - Show current status

**Thresholds:**
• `watchdog set threshold <name> <value>` - Set a threshold
• `watchdog get threshold <name>` - Get a threshold value
• `watchdog list thresholds` - List all thresholds

**Monitoring:**
• `watchdog metrics` - Show current metrics
• `watchdog history [count]` - Show metrics history
• `watchdog clear history` - Clear metrics history
• `watchdog kill <process>` - Kill a process by name or PID

**Valid threshold names:** vram, ram, cpu, response_time, check_interval, history_size
"""
        return CommandResult(
            success=True,
            message=help_text.strip()
        )
    
    def set_watchdog(self, watchdog):
        """Update the watchdog instance.
        
        Args:
            watchdog: New SystemWatchdog instance
        """
        self.watchdog = watchdog
    
    def set_chat_callback(self, callback: Callable[[str], None]):
        """Set callback for displaying messages in chat.
        
        Args:
            callback: Function that takes a message string
        """
        self.chat_callback = callback