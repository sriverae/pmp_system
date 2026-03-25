"""
SelectorTrabajadorDialog — reutilizable desde OTForm, etc.
"""
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton
)
from PySide6.QtCore import Qt

from app.views.shared.tabla_base import TablaBase
from app.core.database import get_session
from app.models.trabajador import Trabajador
from app.views.shared.styles import COLOR_TEXT_PRIMARY, COLOR_ACCENT_BLUE


COLS = [
    {"header": "Código",       "key": "codigo",       "width": 80},
    {"header": "Nombre",       "key": "nombre",       "width": 200},
    {"header": "Especialidad", "key": "especialidad", "width": 140},
    {"header": "Turno",        "key": "turno",        "width": 80},
    {"header": "Estado",       "key": "estado",       "width": 80},
]


class SelectorTrabajadorDialog(QDialog):
    def __init__(self, excluir_ids: list = None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Seleccionar Técnico")
        self.setMinimumSize(560, 400)
        self.setModal(True)
        self.excluir_ids = excluir_ids or []
        self.trabajador_seleccionado = None
        self._mapa = {}
        self._construir_ui()
        self._cargar()

    def _construir_ui(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(16, 12, 16, 12)
        lay.setSpacing(10)

        lbl = QLabel("Seleccione el técnico a asignar:")
        lbl.setStyleSheet(
            f"font-weight: 700; color: {COLOR_TEXT_PRIMARY};")
        lay.addWidget(lbl)

        self.tabla = TablaBase(columnas=COLS, columna_estado="estado")
        self.tabla.doble_click.connect(self._confirmar_por_id)
        lay.addWidget(self.tabla)

        btns = QHBoxLayout()
        btn_ok = QPushButton("Asignar")
        btn_ok.setStyleSheet(
            f"background-color: {COLOR_ACCENT_BLUE}; color: white; "
            f"border-radius: 4px; border: none; padding: 6px 20px;")
        btn_ok.clicked.connect(self._confirmar)
        btn_cancel = QPushButton("Cancelar")
        btn_cancel.clicked.connect(self.reject)
        btns.addStretch()
        btns.addWidget(btn_cancel)
        btns.addWidget(btn_ok)
        lay.addLayout(btns)

    def _cargar(self):
        session = get_session()
        try:
            trabajadores = (session.query(Trabajador)
                            .filter(Trabajador.estado == "Activo")
                            .order_by(Trabajador.apellidos).all())
            self._mapa = {}
            datos, ids = [], []
            for t in trabajadores:
                if t.id in self.excluir_ids:
                    continue
                self._mapa[t.id] = t
                datos.append({
                    "codigo": t.codigo,
                    "nombre": t.nombre_completo,
                    "especialidad": t.especialidad or "-",
                    "turno": t.turno or "-",
                    "estado": t.estado,
                })
                ids.append(t.id)
            self.tabla.cargar(datos, ids)
        finally:
            session.close()

    def _confirmar(self):
        tid = self.tabla.id_seleccionado()
        if tid:
            self._confirmar_por_id(tid)

    def _confirmar_por_id(self, tid: int):
        self.trabajador_seleccionado = self._mapa.get(tid)
        if self.trabajador_seleccionado:
            self.accept()
