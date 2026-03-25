"""
SelectorMaterialDialog — reutilizable desde OTForm, CierreOTForm, etc.
"""
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QDoubleSpinBox, QCheckBox, QLineEdit
)
from PySide6.QtCore import Qt

from app.views.shared.tabla_base import TablaBase
from app.services.material_service import MaterialService
from app.views.shared.styles import COLOR_TEXT_PRIMARY, COLOR_ACCENT_BLUE


COLS_SEL = [
    {"header": "Código",      "key": "codigo",      "width": 90},
    {"header": "Descripción", "key": "descripcion", "width": 220},
    {"header": "Stock",       "key": "stock",       "width": 70},
    {"header": "Unidad",      "key": "unidad",      "width": 60},
    {"header": "Costo U.",    "key": "costo",       "width": 80},
]


class SelectorMaterialDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Seleccionar Material")
        self.setMinimumSize(560, 420)
        self.setModal(True)
        self.material_seleccionado = None
        self.cantidad_seleccionada = 1.0
        self.es_obligatorio = False
        self._materiales = []
        self._construir_ui()
        self._cargar()

    def _construir_ui(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(16, 12, 16, 12)
        lay.setSpacing(10)

        lbl = QLabel("Seleccione el material:")
        lbl.setStyleSheet(
            f"font-size: 14px; font-weight: 700; color: {COLOR_TEXT_PRIMARY};")
        lay.addWidget(lbl)

        self.tabla = TablaBase(columnas=COLS_SEL)
        self.tabla.doble_click.connect(self._confirmar_por_id)
        lay.addWidget(self.tabla)

        row = QHBoxLayout()
        row.addWidget(QLabel("Cantidad:"))
        self.inp_cantidad = QDoubleSpinBox()
        self.inp_cantidad.setRange(0.01, 99999)
        self.inp_cantidad.setValue(1.0)
        self.inp_cantidad.setFixedWidth(100)
        self.chk_obligatorio = QCheckBox("Obligatorio")

        btn_ok = QPushButton("Seleccionar")
        btn_ok.setStyleSheet(
            f"background-color: {COLOR_ACCENT_BLUE}; color: white; "
            f"border-radius: 4px; border: none; padding: 6px 16px;")
        btn_ok.clicked.connect(self._confirmar)
        btn_cancel = QPushButton("Cancelar")
        btn_cancel.clicked.connect(self.reject)

        row.addWidget(self.inp_cantidad)
        row.addWidget(self.chk_obligatorio)
        row.addStretch()
        row.addWidget(btn_cancel)
        row.addWidget(btn_ok)
        lay.addLayout(row)

    def _cargar(self):
        mats = MaterialService.listar(solo_activos=True)
        self._mats_map = {m.id: m for m in mats}
        datos = [{
            "codigo": m.codigo,
            "descripcion": m.descripcion,
            "stock": f"{m.stock_actual:.1f}",
            "unidad": m.unidad,
            "costo": f"{m.costo_unitario:,.2f}",
        } for m in mats]
        self.tabla.cargar(datos, [m.id for m in mats])

    def _confirmar(self):
        mid = self.tabla.id_seleccionado()
        if not mid:
            return
        self._confirmar_por_id(mid)

    def _confirmar_por_id(self, mid: int):
        self.material_seleccionado = self._mats_map.get(mid)
        self.cantidad_seleccionada = self.inp_cantidad.value()
        self.es_obligatorio = self.chk_obligatorio.isChecked()
        if self.material_seleccionado:
            self.accept()
