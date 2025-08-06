"""
System Command Tool for DinoAir 2.0

Safe command execution with output capture and security restrictions.
"""

import subprocess
import shlex
import logging
from typing import Dict, Any, List, Optional

from src.tools.base import (
    BaseTool, ToolMetadata, ToolParameter, ToolResult,
    ToolCategory, ParameterType
)


logger = logging.getLogger(__name__)


class SystemCommandTool(BaseTool):
    """Tool for executing safe system commands with output capture."""
    
    def _create_metadata(self) -> ToolMetadata:
        """Create tool metadata."""
        return ToolMetadata(
            name="system_command",
            version="1.0.0",
            description="Execute safe system commands with output capture",
            author="DinoAir Team",
            category=ToolCategory.SYSTEM,
            tags=["system", "command", "execution", "shell"],
            parameters=[
                ToolParameter(
                    name="command",
                    type=ParameterType.STRING,
                    description="The command to execute",
                    required=True,
                    example="ls -la"
                ),
                ToolParameter(
                    name="working_directory",
                    type=ParameterType.STRING,
                    description="Working directory for command execution",
                    required=False,
                    example="/home/user/projects"
                ),
                ToolParameter(
                    name="timeout",
                    type=ParameterType.INTEGER,
                    description="Command timeout in seconds (max 300)",
                    required=False,
                    default=30,
                    min_value=1,
                    max_value=300,
                    example=30
                ),
                ToolParameter(
                    name="capture_output",
                    type=ParameterType.BOOLEAN,
                    description="Whether to capture command output",
                    required=False,
                    default=True,
                    example=True
                )
            ],
            capabilities={
                "async_support": False,
                "streaming": False,
                "cancellable": True,
                "progress_reporting": False,
                "batch_processing": False,
                "caching": False,
                "stateful": False
            },
            examples=[
                {
                    "name": "List directory contents",
                    "description": "List current directory contents",
                    "parameters": {
                        "command": "ls -la",
                        "capture_output": True
                    }
                },
                {
                    "name": "Check Git status",
                    "description": "Check Git repository status",
                    "parameters": {
                        "command": "git status",
                        "working_directory": "/path/to/repo",
                        "timeout": 10
                    }
                },
                {
                    "name": "Get system information",
                    "description": "Get system information",
                    "parameters": {
                        "command": "uname -a",
                        "capture_output": True
                    }
                }
            ]
        )
    
    def initialize(self):
        """Initialize the tool."""
        logger.info("SystemCommandTool initialized")
        self._timeout = 30  # Default timeout in seconds
        self._allowed_commands = {
            'dir', 'ls', 'pwd', 'whoami', 'echo', 'cat', 'head', 'tail',
            'find', 'grep', 'wc', 'sort', 'uniq', 'date', 'hostname',
            'ping', 'curl', 'wget', 'git', 'npm', 'pip', 'python',
            'node', 'java', 'javac', 'gcc', 'make', 'cmake'
        }
        self._blocked_commands = {
            'rm', 'del', 'rmdir', 'rd', 'format', 'fdisk', 'mkfs',
            'shutdown', 'reboot', 'halt', 'poweroff', 'init',
            'su', 'sudo', 'passwd', 'chmod', 'chown', 'kill',
            'killall', 'pkill', 'taskkill'
        }
        
        # Apply config overrides
        config = self._config
        if config:
            self._timeout = config.get('default_timeout', self._timeout)
            
            if 'allowed_commands' in config:
                self._allowed_commands.update(config['allowed_commands'])
            
            if 'blocked_commands' in config:
                self._blocked_commands.update(config['blocked_commands'])
    
    def execute(self, **kwargs) -> ToolResult:
        """Execute a system command safely."""
        try:
            # Extract parameters
            command = kwargs.get('command', '').strip()
            working_dir = kwargs.get('working_directory')
            timeout = min(kwargs.get('timeout', self._timeout), 300)
            capture_output = kwargs.get('capture_output', True)
            
            # Validate command
            if not command:
                return ToolResult(
                    success=False,
                    errors=["Command cannot be empty"]
                )
            
            # Security check
            security_result = self._check_command_security(command)
            if not security_result['allowed']:
                return ToolResult(
                    success=False,
                    errors=[f"Command not allowed: "
                            f"{security_result['reason']}"]
                )
            
            # Parse command for execution
            try:
                cmd_parts = shlex.split(command)
            except ValueError as e:
                return ToolResult(
                    success=False,
                    errors=[f"Invalid command syntax: {str(e)}"]
                )
            
            # Execute command
            result = self._execute_command(
                cmd_parts, working_dir, timeout, capture_output
            )
            
            return ToolResult(
                success=True,
                output={
                    'command': command,
                    'return_code': result['return_code'],
                    'stdout': result['stdout'],
                    'stderr': result['stderr'],
                    'execution_time': result['execution_time'],
                    'working_directory': working_dir or "current"
                },
                metadata={
                    'operation': 'command_execution',
                    'command': command,
                    'return_code': result['return_code']
                }
            )
            
        except Exception as e:
            logger.error(f"Command execution failed: {e}")
            return ToolResult(
                success=False,
                errors=[f"Command execution failed: {str(e)}"]
            )
    
    def _check_command_security(self, command: str) -> Dict[str, Any]:
        """Check if command is safe to execute."""
        cmd_parts = command.split()
        if not cmd_parts:
            return {'allowed': False, 'reason': 'Empty command'}
        
        base_command = cmd_parts[0].lower()
        
        # Remove path components to get base command
        if '/' in base_command or '\\' in base_command:
            base_command = base_command.split('/')[-1].split('\\')[-1]
        
        # Check blocked commands
        if base_command in self._blocked_commands:
            return {
                'allowed': False,
                'reason': f'Command "{base_command}" is blocked for security'
            }
        
        # Check for dangerous patterns
        dangerous_patterns = [
            '&&', '||', ';', '|', '>', '>>', '<', '`', '$(',
            'eval', 'exec', 'import', '__import__'
        ]
        for pattern in dangerous_patterns:
            if pattern in command:
                return {
                    'allowed': False,
                    'reason': f'Dangerous pattern "{pattern}" detected'
                }
        
        # Allow if in allowed list or if it's a safe command pattern
        if (base_command in self._allowed_commands or
                base_command.endswith('.py') or
                base_command.endswith('.js') or
                base_command.endswith('.sh')):
            return {'allowed': True, 'reason': 'Command is in allowed list'}
        
        # Default: allow with warning for unknown commands
        return {
            'allowed': True,
            'reason': 'Unknown command - proceed with caution'
        }
    
    def _execute_command(self, cmd_parts: List[str],
                         working_dir: Optional[str], timeout: int,
                         capture_output: bool) -> Dict[str, Any]:
        """Execute the command and return results."""
        import time
        
        start_time = time.time()
        
        try:
            if capture_output:
                process = subprocess.run(
                    cmd_parts,
                    cwd=working_dir,
                    timeout=timeout,
                    capture_output=True,
                    text=True,
                    shell=False
                )
                stdout = process.stdout
                stderr = process.stderr
            else:
                process = subprocess.run(
                    cmd_parts,
                    cwd=working_dir,
                    timeout=timeout,
                    shell=False
                )
                stdout = ""
                stderr = ""
            
            execution_time = time.time() - start_time
            
            return {
                'return_code': process.returncode,
                'stdout': stdout,
                'stderr': stderr,
                'execution_time': round(execution_time, 3)
            }
            
        except subprocess.TimeoutExpired:
            execution_time = time.time() - start_time
            return {
                'return_code': -1,
                'stdout': "",
                'stderr': f"Command timed out after {timeout} seconds",
                'execution_time': round(execution_time, 3)
            }
        except FileNotFoundError:
            execution_time = time.time() - start_time
            return {
                'return_code': -1,
                'stdout': "",
                'stderr': f"Command not found: {cmd_parts[0]}",
                'execution_time': round(execution_time, 3)
            }
        except PermissionError:
            execution_time = time.time() - start_time
            return {
                'return_code': -1,
                'stdout': "",
                'stderr': f"Permission denied: {cmd_parts[0]}",
                'execution_time': round(execution_time, 3)
            }
    
    def shutdown(self):
        """Cleanup tool resources."""
        logger.info("SystemCommandTool shutting down")
        # No persistent resources to clean up