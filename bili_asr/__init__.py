# -*- coding: utf-8 -*-
"""
bili-asr: Zero-cost, high-speed CLI & SDK for audio transcription using Bilibili Cloud AI.
"""

from .core import transcribe, TranscribeResult

__version__ = "0.1.0"
__all__ = ["transcribe", "TranscribeResult"]
