from PyQt6.QtGui import QColor, QPalette
from qfluentwidgets import Theme, setTheme, setThemeColor


KHAKI_THEME_COLOR = QColor("#b5926a")
KHAKI_WINDOW = QColor("#f4ecde")
KHAKI_PAGE = QColor("#f7f0e4")
KHAKI_CARD = QColor("#fffaf2")
KHAKI_INPUT = QColor("#fffcf7")
KHAKI_BORDER = QColor("#dfcfb8")
KHAKI_TEXT = QColor("#4f4336")
KHAKI_MUTED = QColor("#7b6b58")
KHAKI_ACCENT = QColor("#8a6a46")


GLOBAL_STYLESHEET = """
QWidget {
    color: #4f4336;
    selection-background-color: #d8c2a3;
    selection-color: #3c3026;
}

QWidget[themeWindow="true"] {
    background: #f4ecde;
}

QWidget[themePage="true"] {
    background: #f7f0e4;
}

QWidget[themeNav="true"] {
    background: #efe4d1;
    border-right: 1px solid #ddccb1;
}

QWidget[themeCard="true"] {
    background: #fffaf2;
    border: 1px solid #e0d1bb;
    border-radius: 16px;
}

QWidget[themeLogo="true"] {
    background: #f3ebdd;
    border: 1px solid #d9c8ae;
    border-radius: 30px;
    color: #7b6b58;
}

QLabel[role="muted"] {
    color: #7b6b58;
}

QLabel[role="accent"] {
    color: #8a6a46;
    font-weight: 700;
}

QScrollArea,
QAbstractScrollArea {
    background: transparent;
    border: none;
}

QTextEdit,
QPlainTextEdit,
QLineEdit,
QComboBox,
QTableView,
QTableWidget,
QListWidget,
QTreeWidget {
    background: #fffcf7;
    border: 1px solid #ddceb9;
    border-radius: 10px;
}

QHeaderView::section {
    background: #f1e6d5;
    color: #5c4d3e;
    border: none;
    border-bottom: 1px solid #dbc9ae;
    padding: 8px;
}

QTableView::item,
QTableWidget::item {
    padding: 6px;
}

QScrollBar:vertical {
    background: transparent;
    width: 10px;
    margin: 2px;
}

QScrollBar::handle:vertical {
    background: #d6c3a7;
    min-height: 30px;
    border-radius: 5px;
}

QScrollBar::handle:vertical:hover {
    background: #c8b08f;
}

QScrollBar::add-line:vertical,
QScrollBar::sub-line:vertical,
QScrollBar::add-page:vertical,
QScrollBar::sub-page:vertical {
    background: transparent;
    height: 0px;
}
"""


def apply_global_theme(app):
    """应用全局浅卡其主题。"""
    setTheme(Theme.LIGHT, save=False, lazy=False)
    setThemeColor(KHAKI_THEME_COLOR, save=False, lazy=False)

    palette = app.palette()
    palette.setColor(QPalette.ColorRole.Window, KHAKI_WINDOW)
    palette.setColor(QPalette.ColorRole.Base, KHAKI_INPUT)
    palette.setColor(QPalette.ColorRole.AlternateBase, QColor("#f6edde"))
    palette.setColor(QPalette.ColorRole.Button, KHAKI_CARD)
    palette.setColor(QPalette.ColorRole.ButtonText, KHAKI_TEXT)
    palette.setColor(QPalette.ColorRole.Text, KHAKI_TEXT)
    palette.setColor(QPalette.ColorRole.WindowText, KHAKI_TEXT)
    palette.setColor(QPalette.ColorRole.PlaceholderText, KHAKI_MUTED)
    palette.setColor(QPalette.ColorRole.Highlight, QColor("#d8c2a3"))
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor("#3c3026"))
    app.setPalette(palette)

    app.setStyleSheet(GLOBAL_STYLESHEET)
