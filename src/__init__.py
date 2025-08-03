"""
DinoAir 2.0 - Main Source Package
Modular note-taking application with AI capabilities
"""

__version__ = "2.0.0"
__author__ = "DinoAir Development Team"

# Core module imports for easy access
from .models import Note, NoteList
from .database import DatabaseManager, initialize_user_databases
from .utils import ConfigLoader, Logger, Enums, DinoPitColors

__all__ = [
    'Note', 
    'NoteList', 
    'DatabaseManager', 
    'initialize_user_databases',
    'ConfigLoader',
    'Logger',
    'Enums',
    'DinoPitColors'
]
