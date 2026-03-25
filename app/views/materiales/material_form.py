"""Formulario de material — stub."""
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QFormLayout, QLabel, QLineEdit,
    QDoubleSpinBox, QComboBox, QTextEdit, QPushButton, QHBoxLayout, QMessageBox)
from PySide6.QtCore import Qt
from app.services.material_service import MaterialService

class MaterialForm(QDialog):
    def __init__(self, material_id=None, parent=None):
        super().__init__(parent)
        self.material_id = material_id
        self.setWindowTitle("Material")
        self.setMinimumSize(480, 460)
        self.setModal(True)
        lay = QVBoxLayout(self); lay.setContentsMargins(20,16,20,16); lay.setSpacing(10)
        form = QFormLayout(); form.setSpacing(9); form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        self.inp_codigo = QLineEdit()
        self.inp_descripcion = QLineEdit()
        self.inp_categoria = QLineEdit()
        self.inp_unidad = QLineEdit(); self.inp_unidad.setText("UN")
        self.inp_stock = QDoubleSpinBox(); self.inp_stock.setRange(0,9999999); self.inp_stock.setDecimals(2)
        self.inp_minimo = QDoubleSpinBox(); self.inp_minimo.setRange(0,9999999); self.inp_minimo.setDecimals(2)
        self.inp_costo = QDoubleSpinBox(); self.inp_costo.setRange(0,9999999); self.inp_costo.setDecimals(2); self.inp_costo.setGroupSeparatorShown(True)
        self.inp_proveedor = QLineEdit()
        self.inp_ubicacion = QLineEdit()
        self.combo_criticidad = QComboBox(); self.combo_criticidad.addItems(["Normal","Crítico","Alto","Bajo"])
        form.addRow("Código *:", self.inp_codigo)
        form.addRow("Descripción *:", self.inp_descripcion)
        form.addRow("Categoría:", self.inp_categoria)
        form.addRow("Unidad:", self.inp_unidad)
        form.addRow("Stock inicial:", self.inp_stock)
        form.addRow("Stock mínimo:", self.inp_minimo)
        form.addRow("Costo unitario:", self.inp_costo)
        form.addRow("Proveedor:", self.inp_proveedor)
        form.addRow("Ubicación almacén:", self.inp_ubicacion)
        form.addRow("Criticidad:", self.combo_criticidad)
        lay.addLayout(form)
        btns = QHBoxLayout()
        btn_c = QPushButton("Cancelar"); btn_c.clicked.connect(self.reject)
        btn_g = QPushButton("Guardar"); btn_g.clicked.connect(self._guardar)
        btns.addStretch(); btns.addWidget(btn_c); btns.addWidget(btn_g)
        lay.addLayout(btns)
        if material_id: self._cargar()

    def _cargar(self):
        m = MaterialService.obtener(self.material_id)
        if not m: return
        self.inp_codigo.setText(m.codigo); self.inp_codigo.setReadOnly(True)
        self.inp_descripcion.setText(m.descripcion)
        self.inp_categoria.setText(m.categoria or "")
        self.inp_unidad.setText(m.unidad)
        self.inp_stock.setValue(m.stock_actual)
        self.inp_minimo.setValue(m.stock_minimo)
        self.inp_costo.setValue(m.costo_unitario)
        self.inp_proveedor.setText(m.proveedor or "")
        self.inp_ubicacion.setText(m.ubicacion_almacen or "")
        self.combo_criticidad.setCurrentText(m.criticidad or "Normal")

    def _guardar(self):
        datos = {
            "codigo": self.inp_codigo.text().strip(),
            "descripcion": self.inp_descripcion.text().strip(),
            "categoria": self.inp_categoria.text().strip() or None,
            "unidad": self.inp_unidad.text().strip() or "UN",
            "stock_actual": self.inp_stock.value(),
            "stock_minimo": self.inp_minimo.value(),
            "costo_unitario": self.inp_costo.value(),
            "proveedor": self.inp_proveedor.text().strip() or None,
            "ubicacion_almacen": self.inp_ubicacion.text().strip() or None,
            "criticidad": self.combo_criticidad.currentText(),
        }
        if self.material_id:
            ok, msg = MaterialService.actualizar(self.material_id, datos)
        else:
            ok, msg, _ = MaterialService.crear(datos)
        if ok: QMessageBox.information(self,"OK",msg); self.accept()
        else: QMessageBox.critical(self,"Error",msg)
