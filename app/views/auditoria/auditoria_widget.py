"""Módulo Auditoría — registro de eventos del sistema."""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFrame, QComboBox, QDateEdit,
    QMessageBox, QFileDialog
)
from PySide6.QtCore import QDate

from app.views.shared.tabla_base import TablaBase
from app.services.auditoria_service import AuditoriaService
from app.views.shared.styles import COLOR_TEXT_PRIMARY, COLOR_TEXT_SECONDARY
from datetime import datetime

COLS = [
    {"header": "Fecha/Hora",  "key": "fecha",    "width": 130},
    {"header": "Usuario",     "key": "usuario",  "width": 110},
    {"header": "Módulo",      "key": "modulo",   "width": 110},
    {"header": "Acción",      "key": "accion",   "width": 220},
    {"header": "Tabla",       "key": "tabla",    "width": 100},
    {"header": "Registro ID", "key": "rid",      "width": 80},
]


class AuditoriaWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._construir_ui()
        self.cargar_datos()

    def _construir_ui(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(16, 12, 16, 12)
        lay.setSpacing(10)

        enc = QHBoxLayout()
        lbl = QLabel("[Aud]  Auditoría del Sistema")
        lbl.setStyleSheet(
            f"font-size: 18px; font-weight: 700; color: {COLOR_TEXT_PRIMARY};")
        enc.addWidget(lbl)
        enc.addStretch()

        btn_exp = QPushButton("[Exp] Exportar")
        btn_exp.setFixedHeight(30)
        btn_exp.clicked.connect(self._exportar)
        enc.addWidget(btn_exp)
        lay.addLayout(enc)

        fil = QHBoxLayout()
        self.fecha_desde = QDateEdit()
        self.fecha_desde.setDate(QDate.currentDate().addDays(-7))
        self.fecha_desde.setCalendarPopup(True)
        self.fecha_hasta = QDateEdit()
        self.fecha_hasta.setDate(QDate.currentDate())
        self.fecha_hasta.setCalendarPopup(True)
        btn_filtrar = QPushButton("Filtrar")
        btn_filtrar.clicked.connect(self.cargar_datos)

        fil.addWidget(QLabel("Desde:"))
        fil.addWidget(self.fecha_desde)
        fil.addWidget(QLabel("Hasta:"))
        fil.addWidget(self.fecha_hasta)
        fil.addWidget(btn_filtrar)
        fil.addStretch()
        lay.addLayout(fil)

        self.tabla = TablaBase(columnas=COLS)
        lay.addWidget(self.tabla)

    def cargar_datos(self):
        fd = self.fecha_desde.date()
        fh = self.fecha_hasta.date()
        desde = datetime(fd.year(), fd.month(), fd.day())
        hasta = datetime(fh.year(), fh.month(), fh.day(), 23, 59, 59)

        registros = AuditoriaService.obtener_registros(
            fecha_desde=desde, fecha_hasta=hasta, limit=500)
        datos, ids = [], []
        for r in registros:
            datos.append({
                "fecha": r.fecha_hora.strftime("%d/%m/%Y %H:%M:%S"),
                "usuario": r.username or "-",
                "modulo": r.modulo or "-",
                "accion": r.accion,
                "tabla": r.tabla_afectada or "-",
                "rid": str(r.registro_id) if r.registro_id else "-",
            })
            ids.append(r.id)
        self.tabla.cargar(datos, ids)

    def _exportar(self):
        ruta, _ = QFileDialog.getSaveFileName(
            self, "Exportar Auditoría", "auditoria.xlsx",
            "Excel (*.xlsx)")
        if not ruta:
            return
        try:
            import pandas as pd
            fd = self.fecha_desde.date()
            fh = self.fecha_hasta.date()
            registros = AuditoriaService.obtener_registros(
                datetime(fd.year(), fd.month(), fd.day()),
                datetime(fh.year(), fh.month(), fh.day(), 23, 59, 59),
                limit=10000)
            datos = [{
                "Fecha/Hora": r.fecha_hora.strftime("%d/%m/%Y %H:%M:%S"),
                "Usuario": r.username,
                "Módulo": r.modulo,
                "Acción": r.accion,
                "Tabla": r.tabla_afectada,
                "Registro ID": r.registro_id,
            } for r in registros]
            pd.DataFrame(datos).to_excel(ruta, index=False)
            QMessageBox.information(self, "Exportado", ruta)
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))
