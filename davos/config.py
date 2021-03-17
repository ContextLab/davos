"""
Module for managing session-wide global objects, switches, and
configurable options for both internal and user settings
"""

from __future__ import annotations


__all__ = []


IPYTHON_SHELL = None
PARSER_ENVIRONMENT = None

CONFIRM_INSTALL = False
SUPPRESS_STDOUT = False
LOCAL_PACKAGES = {}