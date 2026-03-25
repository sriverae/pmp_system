"""Widget placeholder para módulos en desarrollo."""
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PySide6.QtCore import Qt
from app.views.shared.styles import COLOR_TEXT_SECONDARY


class PlaceholderWidget(QWidget):
    def __init__(self, nombre: str = "Módulo", parent=None):
        super().__init__(parent)
        lay = QVBoxLayout(self)
        lay.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl = QLabel(f"{nombre}\n\n(Módulo en desarrollo — próxima versión)")
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl.setStyleSheet(
            f"font-size: 18px; color: {COLOR_TEXT_SECONDARY};")
        lbl.setWordWrap(True)
        lay.addWidget(lbl)
