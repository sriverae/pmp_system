"""Historial equipo — stub."""
from PySide6.QtWidgets import QDialog, QVBoxLayout, QTableWidget, QTableWidgetItem, QPushButton
from app.core.database import get_session
from app.models.historial import HistorialEquipo

class HistorialEquipoDialog(QDialog):
    def __init__(self, equipo_id, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Historial del Equipo"); self.setMinimumSize(640,400); self.setModal(True)
        lay = QVBoxLayout(self); lay.setContentsMargins(16,12,16,12)
        self.tabla = QTableWidget(0,4); self.tabla.setHorizontalHeaderLabels(["Fecha","Tipo","Descripción","Usuario"])
        self.tabla.horizontalHeader().setStretchLastSection(True); self.tabla.verticalHeader().setVisible(False)
        lay.addWidget(self.tabla)
        btn = QPushButton("Cerrar"); btn.clicked.connect(self.accept); lay.addWidget(btn)
        session = get_session()
        try:
            eventos = session.query(HistorialEquipo).filter_by(equipo_id=equipo_id).order_by(HistorialEquipo.fecha.desc()).limit(100).all()
            for e in eventos:
                r = self.tabla.rowCount(); self.tabla.insertRow(r)
                for c,v in enumerate([e.fecha.strftime("%d/%m/%Y %H:%M"),e.tipo_evento,e.descripcion or "",str(e.usuario_id or "")]):
                    self.tabla.setItem(r,c,QTableWidgetItem(v))
        finally: session.close()
