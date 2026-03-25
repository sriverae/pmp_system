"""
Formulario Nuevo / Editar Equipo.
"""
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLabel, QLineEdit, QPushButton, QComboBox,
    QDoubleSpinBox, QTextEdit, QDialogButtonBox,
    QMessageBox, QGroupBox, QTabWidget, QWidget
)
from PySide6.QtCore import Qt

from app.services.equipo_service import EquipoService
from app.views.shared.styles import (
    COLOR_BG_MEDIUM, COLOR_TEXT_PRIMARY, COLOR_ACCENT_BLUE,
    COLOR_BORDER, COLOR_TEXT_SECONDARY
)


class EquipoForm(QDialog):
    def __init__(self, equipo_id: int = None, parent=None):
        super().__init__(parent)
        self.equipo_id = equipo_id
        self._modo_edicion = equipo_id is not None
        self.setWindowTitle(
            "Editar Equipo" if self._modo_edicion else "Nuevo Equipo")
        self.setMinimumSize(620, 560)
        self.setModal(True)
        self._construir_ui()
        if self._modo_edicion:
            self._cargar_datos()

    def _construir_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(12)

        # Título
        lbl = QLabel("Editar Equipo" if self._modo_edicion else "Nuevo Equipo")
        lbl.setStyleSheet(
            f"font-size: 16px; font-weight: 700; color: {COLOR_TEXT_PRIMARY};")
        layout.addWidget(lbl)

        tabs = QTabWidget()

        # -- Tab 1: Datos generales -------------------------------------
        tab1 = QWidget()
        form1 = QFormLayout(tab1)
        form1.setSpacing(10)
        form1.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self.inp_codigo = QLineEdit()
        self.inp_codigo.setPlaceholderText("Ej: EQ-001")
        if self._modo_edicion:
            self.inp_codigo.setReadOnly(True)
            self.inp_codigo.setStyleSheet(
                f"background-color: {COLOR_BG_MEDIUM}; "
                f"color: {COLOR_TEXT_SECONDARY};")

        self.inp_nombre = QLineEdit()
        self.inp_nombre.setPlaceholderText("Nombre descriptivo del equipo")
        self.inp_descripcion = QTextEdit()
        self.inp_descripcion.setPlaceholderText("Descripción detallada...")
        self.inp_descripcion.setMaximumHeight(70)
        self.inp_ubicacion = QLineEdit()
        self.inp_area = QLineEdit()
        self.inp_centro_costo = QLineEdit()
        self.inp_marca = QLineEdit()
        self.inp_modelo = QLineEdit()
        self.inp_serie = QLineEdit()
        self.inp_fabricante = QLineEdit()

        self.combo_criticidad = QComboBox()
        self.combo_criticidad.addItems(["Crítica", "Alta", "Media", "Baja"])
        self.combo_criticidad.setCurrentText("Media")

        self.combo_estado = QComboBox()
        self.combo_estado.addItems(
            ["Activo", "Inactivo", "En mantenimiento"])

        self.inp_costo_repos = QDoubleSpinBox()
        self.inp_costo_repos.setRange(0, 9999999.99)
        self.inp_costo_repos.setDecimals(2)
        self.inp_costo_repos.setGroupSeparatorShown(True)

        form1.addRow("Código *:", self.inp_codigo)
        form1.addRow("Nombre *:", self.inp_nombre)
        form1.addRow("Descripción:", self.inp_descripcion)
        form1.addRow("Ubicación:", self.inp_ubicacion)
        form1.addRow("Área:", self.inp_area)
        form1.addRow("Centro de costo:", self.inp_centro_costo)
        form1.addRow("Marca:", self.inp_marca)
        form1.addRow("Modelo:", self.inp_modelo)
        form1.addRow("Serie:", self.inp_serie)
        form1.addRow("Fabricante:", self.inp_fabricante)
        form1.addRow("Criticidad *:", self.combo_criticidad)
        form1.addRow("Estado:", self.combo_estado)
        form1.addRow("Costo de reposición:", self.inp_costo_repos)

        tabs.addTab(tab1, "Datos Generales")

        # -- Tab 2: Contador --------------------------------------------
        tab2 = QWidget()
        form2 = QFormLayout(tab2)
        form2.setSpacing(10)
        form2.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self.combo_tipo_contador = QComboBox()
        self.combo_tipo_contador.addItems(
            ["Sin contador", "Horas", "Kilómetros", "Ciclos", "Otro"])

        self.inp_lectura_inicial = QDoubleSpinBox()
        self.inp_lectura_inicial.setRange(0, 99999999.0)
        self.inp_lectura_inicial.setDecimals(1)

        form2.addRow("Tipo de contador:", self.combo_tipo_contador)
        form2.addRow("Lectura inicial:", self.inp_lectura_inicial)

        tabs.addTab(tab2, "Contador")

        # -- Tab 3: Observaciones ---------------------------------------
        tab3 = QWidget()
        lay3 = QVBoxLayout(tab3)
        self.inp_observaciones = QTextEdit()
        self.inp_observaciones.setPlaceholderText(
            "Observaciones, historial previo, notas técnicas...")
        lay3.addWidget(self.inp_observaciones)
        tabs.addTab(tab3, "Observaciones")

        layout.addWidget(tabs)

        # -- Botones ----------------------------------------------------
        btn_box = QHBoxLayout()
        btn_box.addStretch()

        btn_cancelar = QPushButton("Cancelar")
        btn_cancelar.setFixedHeight(34)
        btn_cancelar.clicked.connect(self.reject)

        self.btn_guardar_nuevo = QPushButton("Guardar y nuevo")
        self.btn_guardar_nuevo.setFixedHeight(34)
        self.btn_guardar_nuevo.clicked.connect(self._guardar_y_nuevo)

        self.btn_guardar = QPushButton("  Guardar  ")
        self.btn_guardar.setObjectName("btn_primary")
        self.btn_guardar.setFixedHeight(34)
        self.btn_guardar.setStyleSheet(
            f"background-color: {COLOR_ACCENT_BLUE}; color: white; "
            f"font-weight: 600; border-radius: 4px; border: none;")
        self.btn_guardar.clicked.connect(self._guardar)

        if self._modo_edicion:
            self.btn_guardar_nuevo.hide()

        btn_box.addWidget(btn_cancelar)
        if not self._modo_edicion:
            btn_box.addWidget(self.btn_guardar_nuevo)
        btn_box.addWidget(self.btn_guardar)
        layout.addLayout(btn_box)

        # Nota campos obligatorios
        lbl_req = QLabel("* Campos obligatorios")
        lbl_req.setStyleSheet(
            f"color: {COLOR_TEXT_SECONDARY}; font-size: 11px;")
        layout.addWidget(lbl_req)

    def _cargar_datos(self):
        equipo = EquipoService.obtener(self.equipo_id)
        if not equipo:
            return
        self.inp_codigo.setText(equipo.codigo)
        self.inp_nombre.setText(equipo.nombre)
        self.inp_descripcion.setPlainText(equipo.descripcion or "")
        self.inp_ubicacion.setText(equipo.ubicacion or "")
        self.inp_area.setText(equipo.area or "")
        self.inp_centro_costo.setText(equipo.centro_costo or "")
        self.inp_marca.setText(equipo.marca or "")
        self.inp_modelo.setText(equipo.modelo or "")
        self.inp_serie.setText(equipo.serie or "")
        self.inp_fabricante.setText(equipo.fabricante or "")
        idx_crit = self.combo_criticidad.findText(equipo.criticidad)
        if idx_crit >= 0:
            self.combo_criticidad.setCurrentIndex(idx_crit)
        idx_est = self.combo_estado.findText(equipo.estado)
        if idx_est >= 0:
            self.combo_estado.setCurrentIndex(idx_est)
        self.inp_costo_repos.setValue(equipo.costo_reposicion or 0)
        if equipo.tipo_contador:
            idx_cnt = self.combo_tipo_contador.findText(equipo.tipo_contador)
            if idx_cnt >= 0:
                self.combo_tipo_contador.setCurrentIndex(idx_cnt)
        self.inp_lectura_inicial.setValue(equipo.lectura_inicial or 0)
        self.inp_observaciones.setPlainText(equipo.observaciones or "")

    def _recolectar_datos(self) -> dict:
        tipo_cnt = self.combo_tipo_contador.currentText()
        return {
            "codigo": self.inp_codigo.text().strip(),
            "nombre": self.inp_nombre.text().strip(),
            "descripcion": self.inp_descripcion.toPlainText().strip(),
            "ubicacion": self.inp_ubicacion.text().strip(),
            "area": self.inp_area.text().strip(),
            "centro_costo": self.inp_centro_costo.text().strip(),
            "marca": self.inp_marca.text().strip(),
            "modelo": self.inp_modelo.text().strip(),
            "serie": self.inp_serie.text().strip() or None,
            "fabricante": self.inp_fabricante.text().strip(),
            "criticidad": self.combo_criticidad.currentText(),
            "estado": self.combo_estado.currentText(),
            "costo_reposicion": self.inp_costo_repos.value(),
            "tipo_contador": None if tipo_cnt == "Sin contador" else tipo_cnt,
            "lectura_inicial": self.inp_lectura_inicial.value(),
            "observaciones": self.inp_observaciones.toPlainText().strip(),
        }

    def _guardar(self) -> bool:
        datos = self._recolectar_datos()
        if self._modo_edicion:
            ok, msg = EquipoService.actualizar(self.equipo_id, datos)
        else:
            ok, msg, _ = EquipoService.crear(datos)
        if ok:
            QMessageBox.information(self, "Éxito", msg)
            self.accept()
            return True
        else:
            QMessageBox.critical(self, "Error", msg)
            return False

    def _guardar_y_nuevo(self):
        if self._guardar():
            # Reiniciar formulario
            for w in [self.inp_codigo, self.inp_nombre, self.inp_ubicacion,
                       self.inp_area, self.inp_centro_costo, self.inp_marca,
                       self.inp_modelo, self.inp_serie, self.inp_fabricante]:
                w.clear()
            self.inp_descripcion.clear()
            self.inp_observaciones.clear()
            self.inp_costo_repos.setValue(0)
            self.inp_codigo.setFocus()
            # No cerrar el diálogo
            self.setResult(0)  # Reset para evitar accept automático
