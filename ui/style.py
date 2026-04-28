# Stylesheet is now generated dynamically by ui/themes.py.
# This module kept for backward compatibility — import STYLESHEET only if needed
# for a default/fallback context without a running QApplication.
from ui.themes import build_stylesheet, THEMES

STYLESHEET = build_stylesheet(THEMES["default"], "medium")
