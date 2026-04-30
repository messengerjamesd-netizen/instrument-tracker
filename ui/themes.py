from PySide6.QtGui import QPalette, QColor

FONT_SIZES = {"xsmall": "10px", "small": "11px", "medium": "13px", "large": "16px", "xlarge": "19px"}
_TITLE_SIZES = {"xsmall": "14px", "small": "16px", "medium": "20px", "large": "24px", "xlarge": "28px"}
_LABEL_SIZES = {"xsmall": "9px", "small": "10px", "medium": "12px", "large": "14px", "xlarge": "16px"}

# ── Color utilities ────────────────────────────────────────────────────────────

def _hex_to_rgb(h):
    h = h.lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)

def _rgb_to_hex(r, g, b):
    return f"#{int(r):02x}{int(g):02x}{int(b):02x}"

def _luminance(hex_color):
    r, g, b = _hex_to_rgb(hex_color)
    return 0.299 * r + 0.587 * g + 0.114 * b

def _brighten(hex_color, amount):
    r, g, b = _hex_to_rgb(hex_color)
    return _rgb_to_hex(min(255, r+amount), min(255, g+amount), min(255, b+amount))

def _darken(hex_color, amount):
    r, g, b = _hex_to_rgb(hex_color)
    return _rgb_to_hex(max(0, r-amount), max(0, g-amount), max(0, b-amount))

def _mix(hex1, hex2, ratio=0.35):
    r1, g1, b1 = _hex_to_rgb(hex1)
    r2, g2, b2 = _hex_to_rgb(hex2)
    return _rgb_to_hex(
        int(r1*ratio + r2*(1-ratio)),
        int(g1*ratio + g2*(1-ratio)),
        int(b1*ratio + b2*(1-ratio)),
    )

# ── Theme palettes ─────────────────────────────────────────────────────────────

THEMES = {
    "default": {
        "bg":               "#0a1628",
        "text":             "#c8d8f0",
        "input_bg":         "#0f2040",
        "muted":            "#5a7aaa",
        "accent":           "#2d6bc4",
        "btn_bg":           "#142848",
        "border":           "#1a3666",
        "alt_bg":           "#0d1e38",
        "disabled_text":    "#2a4060",
        "primary_bg":       "#1e4a8a",
        "primary_text":     "#e8f0ff",
        "primary_hover":    "#2456a4",
        "primary_pressed":  "#163870",
        "danger_bg":        "#4a1010",
        "danger_border":    "#7a2020",
        "danger_text":      "#ffcccc",
        "danger_hover":     "#6b1818",
        "camera_bg":        "#050e1a",
        "selection_bg":     "#1e3d6e",
        "tab_hover":        "#142848",
        "scrollbar":        "#1a3666",
        "scrollbar_hover":  "#2d6bc4",
    },
    "dark": {
        "bg":               "#1e1e1e",
        "text":             "#e8e8e8",
        "input_bg":         "#252525",
        "muted":            "#888888",
        "accent":           "#0078d4",
        "btn_bg":           "#333333",
        "border":           "#404040",
        "alt_bg":           "#2a2a2a",
        "disabled_text":    "#555555",
        "primary_bg":       "#005a9e",
        "primary_text":     "#ffffff",
        "primary_hover":    "#006cbf",
        "primary_pressed":  "#004880",
        "danger_bg":        "#5a1a1a",
        "danger_border":    "#8a2a2a",
        "danger_text":      "#ffcccc",
        "danger_hover":     "#6b2020",
        "camera_bg":        "#0a0a0a",
        "selection_bg":     "#004080",
        "tab_hover":        "#333333",
        "scrollbar":        "#404040",
        "scrollbar_hover":  "#0078d4",
    },
    "light": {
        "bg":               "#f5f5f5",
        "text":             "#1a1a1a",
        "input_bg":         "#ffffff",
        "muted":            "#666666",
        "accent":           "#0078d4",
        "btn_bg":           "#e0e0e0",
        "border":           "#cccccc",
        "alt_bg":           "#ebebeb",
        "disabled_text":    "#aaaaaa",
        "primary_bg":       "#0078d4",
        "primary_text":     "#ffffff",
        "primary_hover":    "#006cbf",
        "primary_pressed":  "#005a9e",
        "danger_bg":        "#ffd4d4",
        "danger_border":    "#cc4444",
        "danger_text":      "#8b0000",
        "danger_hover":     "#ffbbbb",
        "camera_bg":        "#dddddd",
        "selection_bg":     "#cce4f7",
        "tab_hover":        "#e8e8e8",
        "scrollbar":        "#cccccc",
        "scrollbar_hover":  "#0078d4",
    },
    "high_contrast": {
        "bg":               "#000000",
        "text":             "#ffffff",
        "input_bg":         "#0a0a0a",
        "muted":            "#cccccc",
        "accent":           "#ffff00",
        "btn_bg":           "#1a1a1a",
        "border":           "#ffffff",
        "alt_bg":           "#111111",
        "disabled_text":    "#666666",
        "primary_bg":       "#2a2a00",
        "primary_text":     "#ffff00",
        "primary_hover":    "#3a3a00",
        "primary_pressed":  "#1a1a00",
        "danger_bg":        "#1a0000",
        "danger_border":    "#ff0000",
        "danger_text":      "#ff6666",
        "danger_hover":     "#2a0000",
        "camera_bg":        "#000000",
        "selection_bg":     "#333300",
        "tab_hover":        "#1a1a1a",
        "scrollbar":        "#888888",
        "scrollbar_hover":  "#ffff00",
    },
    "plain": {
        "bg":               "#2b2b2b",
        "text":             "#d4d4d4",
        "input_bg":         "#363636",
        "muted":            "#888888",
        "accent":           "#707070",
        "btn_bg":           "#404040",
        "border":           "#555555",
        "alt_bg":           "#313131",
        "disabled_text":    "#555555",
        "primary_bg":       "#585858",
        "primary_text":     "#ffffff",
        "primary_hover":    "#686868",
        "primary_pressed":  "#484848",
        "danger_bg":        "#4a2020",
        "danger_border":    "#7a4040",
        "danger_text":      "#ffcccc",
        "danger_hover":     "#5a2828",
        "camera_bg":        "#1a1a1a",
        "selection_bg":     "#505050",
        "tab_hover":        "#404040",
        "scrollbar":        "#555555",
        "scrollbar_hover":  "#888888",
    },
}

THEME_LABELS = {
    "default":       "Default",
    "dark":          "Dark",
    "light":         "Light",
    "high_contrast": "High Contrast",
    "custom":        "Custom",
}

# ── Custom theme builder ───────────────────────────────────────────────────────

def build_custom_colors(primary: str, secondary: str) -> dict:
    is_dark = _luminance(secondary) < 128
    if is_dark:
        text          = "#e8e8e8"
        input_bg      = _brighten(secondary, 18)
        alt_bg        = _darken(secondary, 8)
        btn_bg        = _brighten(secondary, 28)
        border        = _brighten(secondary, 48)
        muted         = _brighten(secondary, 80)
        disabled      = _brighten(secondary, 40)
        camera_bg     = _darken(secondary, 25)
        tab_hover     = _brighten(secondary, 22)
    else:
        text          = "#1a1a1a"
        input_bg      = "#ffffff"
        alt_bg        = _darken(secondary, 5)
        btn_bg        = _darken(secondary, 14)
        border        = _darken(secondary, 22)
        muted         = "#666666"
        disabled      = "#aaaaaa"
        camera_bg     = _darken(secondary, 18)
        tab_hover     = _darken(secondary, 10)

    primary_text = "#ffffff" if _luminance(primary) < 160 else "#000000"
    p_hover      = _brighten(primary, 20) if is_dark else _darken(primary, 20)
    p_pressed    = _darken(primary, 30)
    selection    = _mix(primary, secondary, 0.4)

    return {
        "bg":               secondary,
        "text":             text,
        "input_bg":         input_bg,
        "muted":            muted,
        "accent":           primary,
        "btn_bg":           btn_bg,
        "border":           border,
        "alt_bg":           alt_bg,
        "disabled_text":    disabled,
        "primary_bg":       primary,
        "primary_text":     primary_text,
        "primary_hover":    p_hover,
        "primary_pressed":  p_pressed,
        "danger_bg":        "#4a1010" if is_dark else "#ffd4d4",
        "danger_border":    "#7a2020" if is_dark else "#cc4444",
        "danger_text":      "#ffcccc" if is_dark else "#8b0000",
        "danger_hover":     "#6b1818" if is_dark else "#ffbbbb",
        "camera_bg":        camera_bg,
        "selection_bg":     selection,
        "tab_hover":        tab_hover,
        "scrollbar":        border,
        "scrollbar_hover":  primary,
    }


# ── Stylesheet generator ───────────────────────────────────────────────────────

def build_stylesheet(colors: dict, font_size: str = "medium") -> str:
    fs       = FONT_SIZES.get(font_size, "13px")
    fs_small = _LABEL_SIZES.get(font_size, "12px")
    fs_title = _TITLE_SIZES.get(font_size, "20px")
    c = colors
    return f"""
QMainWindow, QDialog {{
    background-color: {c['bg']};
}}
QWidget {{
    background-color: {c['bg']};
    color: {c['text']};
    font-family: Segoe UI, Arial, sans-serif;
    font-size: {fs};
}}

QTabBar::tab {{
    background-color: {c['input_bg']};
    color: {c['muted']};
    padding: 8px 18px;
    border: none;
    border-bottom: 2px solid transparent;
    min-width: 60px;
}}
QTabBar::tab:selected {{
    background-color: {c['bg']};
    color: {c['text']};
    border-bottom: 2px solid {c['accent']};
}}
QTabBar::tab:hover:!selected {{
    background-color: {c['tab_hover']};
    color: {c['text']};
}}
QTabWidget::pane {{
    border: none;
    background-color: {c['bg']};
}}

QGroupBox {{
    border: 1px solid {c['border']};
    border-radius: 6px;
    margin-top: 10px;
    padding-top: 10px;
    color: {c['muted']};
    font-size: {fs_small};
    font-weight: bold;
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 4px;
}}

QLineEdit, QTextEdit, QPlainTextEdit, QComboBox, QSpinBox {{
    background-color: {c['input_bg']};
    border: 1px solid {c['border']};
    border-radius: 5px;
    padding: 6px 8px;
    color: {c['text']};
    selection-background-color: {c['accent']};
}}
QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus, QComboBox:focus {{
    border-color: {c['accent']};
}}

QComboBox::drop-down {{
    border: none;
    width: 24px;
}}
QComboBox::down-arrow {{
    image: none;
    border-left: 5px solid transparent;
    border-right: 5px solid transparent;
    border-top: 6px solid {c['muted']};
    width: 0;
    height: 0;
    margin-right: 6px;
}}
QComboBox QAbstractItemView {{
    background-color: {c['input_bg']};
    border: 1px solid {c['border']};
    selection-background-color: {c['selection_bg']};
    color: {c['text']};
    outline: none;
}}

QPushButton {{
    background-color: {c['btn_bg']};
    color: {c['text']};
    border: 1px solid {c['border']};
    border-radius: 5px;
    padding: 7px 16px;
    font-weight: 500;
}}
QPushButton:hover {{
    background-color: {c['tab_hover']};
    border-color: {c['accent']};
}}
QPushButton:pressed {{
    background-color: {c['accent']};
}}
QPushButton:disabled {{
    color: {c['disabled_text']};
    background-color: {c['alt_bg']};
    border-color: {c['btn_bg']};
}}

QPushButton#primary {{
    background-color: {c['primary_bg']};
    border-color: {c['accent']};
    color: {c['primary_text']};
}}
QPushButton#primary:hover {{
    background-color: {c['primary_hover']};
}}
QPushButton#primary:pressed {{
    background-color: {c['primary_pressed']};
}}

QPushButton#danger {{
    background-color: {c['danger_bg']};
    border-color: {c['danger_border']};
    color: {c['danger_text']};
}}
QPushButton#danger:hover {{
    background-color: {c['danger_hover']};
}}

QTableWidget {{
    background-color: {c['bg']};
    gridline-color: {c['btn_bg']};
    border: 1px solid {c['border']};
    border-radius: 4px;
    alternate-background-color: {c['alt_bg']};
    selection-background-color: {c['selection_bg']};
    selection-color: {c['text']};
}}
QTableWidget::item {{
    padding: 4px 8px;
    border: none;
}}
QTableWidget::item:selected {{
    background-color: {c['selection_bg']};
}}
QHeaderView::section {{
    background-color: {c['input_bg']};
    color: {c['muted']};
    padding: 6px 8px;
    border: none;
    border-right: 1px solid {c['border']};
    border-bottom: 1px solid {c['border']};
    font-weight: bold;
    font-size: {fs_small};
}}
QHeaderView::section:last {{
    border-right: none;
}}

QScrollBar:vertical {{
    background: {c['bg']};
    width: 10px;
    border-radius: 5px;
}}
QScrollBar::handle:vertical {{
    background: {c['scrollbar']};
    border-radius: 5px;
    min-height: 30px;
}}
QScrollBar::handle:vertical:hover {{
    background: {c['scrollbar_hover']};
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
QScrollBar:horizontal {{
    background: {c['bg']};
    height: 10px;
    border-radius: 5px;
}}
QScrollBar::handle:horizontal {{
    background: {c['scrollbar']};
    border-radius: 5px;
    min-width: 30px;
}}
QScrollBar::handle:horizontal:hover {{ background: {c['scrollbar_hover']}; }}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ width: 0; }}

QLabel#status {{
    color: {c['muted']};
    font-size: {fs_small};
    padding: 4px 8px;
    border: 1px solid {c['btn_bg']};
    border-radius: 4px;
    background-color: {c['alt_bg']};
}}
QLabel#section_title {{
    font-size: {fs_title};
    font-weight: bold;
    color: {c['text']};
    padding-bottom: 4px;
}}

QMessageBox {{
    background-color: {c['bg']};
}}
QMessageBox QLabel {{
    color: {c['text']};
}}

QLineEdit#search {{
    background-color: {c['input_bg']};
    border: 1px solid {c['border']};
    border-radius: 5px;
    padding: 6px 10px;
    font-size: {fs};
}}

QLabel#camera_preview {{
    background-color: {c['camera_bg']};
    border: 2px solid {c['border']};
    border-radius: 6px;
}}

QWidget#bottom_bar {{
    background-color: {c['input_bg']};
    border-top: 1px solid {c['border']};
}}

QFrame[frameShape="4"], QFrame[frameShape="5"] {{
    color: {c['border']};
}}

QFrame#sidebar {{
    background-color: {c['alt_bg']};
    border-right: 1px solid {c['border']};
}}

QPushButton#sidebar_item {{
    background-color: transparent;
    border: none;
    border-left: 3px solid transparent;
    border-radius: 0px;
    color: {c['muted']};
    text-align: left;
    padding: 9px 12px;
    min-height: 38px;
    font-size: {fs};
    font-weight: bold;
}}
QPushButton#sidebar_item:hover:!checked {{
    background-color: {c['tab_hover']};
    color: {c['text']};
}}
QPushButton#sidebar_item:checked {{
    background-color: {c['input_bg']};
    color: {c['text']};
    border-left: 3px solid {c['accent']};
}}

QFrame#sidebar_divider {{
    background-color: {c['border']};
    border: none;
    max-height: 1px;
    margin-left: 12px;
    margin-right: 12px;
}}

QCheckBox {{
    spacing: 8px;
}}
QCheckBox::indicator {{
    width: 15px;
    height: 15px;
    border: 1px solid {c['border']};
    border-radius: 3px;
    background-color: {c['input_bg']};
}}
QCheckBox::indicator:checked {{
    background-color: {c['accent']};
    border-color: {c['accent']};
}}

QRadioButton {{
    spacing: 8px;
}}
QRadioButton::indicator {{
    width: 15px;
    height: 15px;
    border: 1px solid {c['border']};
    border-radius: 8px;
    background-color: {c['input_bg']};
}}
QRadioButton::indicator:checked {{
    background-color: {c['accent']};
    border-color: {c['accent']};
}}
"""


def build_palette(colors: dict) -> QPalette:
    p = QPalette()
    p.setColor(QPalette.Window,          QColor(colors["bg"]))
    p.setColor(QPalette.WindowText,      QColor(colors["text"]))
    p.setColor(QPalette.Base,            QColor(colors["input_bg"]))
    p.setColor(QPalette.AlternateBase,   QColor(colors["alt_bg"]))
    p.setColor(QPalette.Text,            QColor(colors["text"]))
    p.setColor(QPalette.Button,          QColor(colors["btn_bg"]))
    p.setColor(QPalette.ButtonText,      QColor(colors["text"]))
    p.setColor(QPalette.Highlight,       QColor(colors["accent"]))
    p.setColor(QPalette.HighlightedText, QColor(colors["primary_text"]))
    p.setColor(QPalette.PlaceholderText, QColor(colors["disabled_text"]))
    return p


def get_colors(theme: str, custom_primary: str = "#2d6bc4",
               custom_secondary: str = "#0a1628") -> dict:
    if theme == "custom":
        return build_custom_colors(custom_primary, custom_secondary)
    return THEMES.get(theme, THEMES["default"])


def apply_theme(app, theme: str, font_size: str = "medium",
                custom_primary: str = "#2d6bc4",
                custom_secondary: str = "#0a1628"):
    colors = get_colors(theme, custom_primary, custom_secondary)
    app.setPalette(build_palette(colors))
    app.setStyleSheet(build_stylesheet(colors, font_size))
