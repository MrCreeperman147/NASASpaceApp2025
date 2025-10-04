"""
Package src pour NASASpaceApp2025

Ce package contient tous les modules de traitement et d'analyse
"""

from .image_processing import ImageProcessor
from .gui import ImageProcessingGUI

# Liste des exports publics
__all__ = [
    'ImageProcessor',
    'ImageProcessingGUI'
]

__version__ = '0.1.0'