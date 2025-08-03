"""
Enums and constants for DinoAir
Centralized location for application constants
"""

from enum import Enum, auto


class AppState(Enum):
    """Application state enumeration"""
    STARTING = auto()
    RUNNING = auto()
    PAUSED = auto()
    SHUTTING_DOWN = auto()
    ERROR = auto()


class DatabaseState(Enum):
    """Database state enumeration"""
    CONNECTED = auto()
    DISCONNECTED = auto()
    INITIALIZING = auto()
    ERROR = auto()
    BACKUP_IN_PROGRESS = auto()


class NoteStatus(Enum):
    """Note status enumeration"""
    DRAFT = auto()
    ACTIVE = auto()
    ARCHIVED = auto()
    DELETED = auto()


class InputType(Enum):
    """Input type enumeration for input processing"""
    TEXT = auto()
    VOICE = auto()
    FILE = auto()
    CLIPBOARD = auto()


class ProcessingStage(Enum):
    """Input processing stage enumeration"""
    VALIDATION = auto()
    ESCAPING = auto()
    PATTERN_NOTIFY = auto()
    PROFANITY_FILTER = auto()
    INTENT_CLASSIFIER = auto()
    TRANSLATION = auto()
    COMPLETE = auto()


class AgentType(Enum):
    """AI Agent type enumeration"""
    LLM_WRAPPER = auto()
    ORCHESTRATOR = auto()
    TRANSLATOR = auto()
    CLASSIFIER = auto()


class ToolType(Enum):
    """Tool type enumeration"""
    MEMORY_TOOL = auto()
    TIMER_TOOL = auto()
    CODE_AGENT = auto()
    FILE_TOOL = auto()


class UITheme(Enum):
    """UI Theme enumeration"""
    LIGHT = "light"
    DARK = "dark"
    AUTO = "auto"


class LogLevel(Enum):
    """Logging level enumeration"""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class Enums:
    """Container class for all enums"""
    AppState = AppState
    DatabaseState = DatabaseState
    NoteStatus = NoteStatus
    InputType = InputType
    ProcessingStage = ProcessingStage
    AgentType = AgentType
    ToolType = ToolType
    UITheme = UITheme
    LogLevel = LogLevel


# Constants
DEFAULT_CONFIG = {
    "APP_NAME": "DinoAir 2.0",
    "VERSION": "2.0.0",
    "DATABASE_TIMEOUT": 30,
    "MAX_RETRIES": 3,
    "BACKUP_RETENTION_DAYS": 30,
    "SESSION_TIMEOUT": 3600,
    "MAX_NOTE_SIZE": 1048576,  # 1MB
    "SUPPORTED_FILE_TYPES": [".txt", ".md", ".json", ".py", ".js", ".html", ".css"],
    "AI_MAX_TOKENS": 2000,
    "UI_UPDATE_INTERVAL": 100,  # milliseconds
}
