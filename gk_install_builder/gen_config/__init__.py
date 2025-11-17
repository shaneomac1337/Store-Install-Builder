"""
Configuration module for GK Install Builder
"""

from .generator_config import (
    TEMPLATE_DIR,
    HELPER_STRUCTURE,
    DEFAULT_DOWNLOAD_WORKERS,
    DEFAULT_CHUNK_SIZE,
    LAUNCHER_TEMPLATES
)

__all__ = [
    'TEMPLATE_DIR',
    'HELPER_STRUCTURE',
    'DEFAULT_DOWNLOAD_WORKERS',
    'DEFAULT_CHUNK_SIZE',
    'LAUNCHER_TEMPLATES'
]
