"""
Integration helpers for the Pseudocode Translator

This module provides high-level APIs, callbacks, and event systems
to facilitate seamless integration with GUI applications and other tools.
"""

from .api import (
    TranslatorAPI,
    SimpleTranslator,
    translate,
    translate_file,
    translate_async,
    batch_translate
)

from .callbacks import (
    TranslationCallback,
    ProgressCallback,
    StatusCallback,
    create_gui_callbacks,
    CallbackManager
)

from .events import (
    TranslationEvent,
    EventType,
    EventDispatcher,
    EventHandler,
    create_event_dispatcher
)

__all__ = [
    # API
    'TranslatorAPI',
    'SimpleTranslator',
    'translate',
    'translate_file',
    'translate_async',
    'batch_translate',
    
    # Callbacks
    'TranslationCallback',
    'ProgressCallback',
    'StatusCallback',
    'create_gui_callbacks',
    'CallbackManager',
    
    # Events
    'TranslationEvent',
    'EventType',
    'EventDispatcher',
    'EventHandler',
    'create_event_dispatcher'
]

# Version info
__version__ = '1.0.0'