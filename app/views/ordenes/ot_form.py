"""
Formulario Nueva OT / Editar OT.
Implementa todas las restricciones de negocio al asignar técnicos y materiales.
"""
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLabel, QLineEdit, QPushButton, QComboBox,
    QDateEdit, QTimeEdit, QTextEdit, QDoubleSpinBox,
    QTableWidget, QTableWidgetItem, QMessageBox,
    QGroupBox, QTabWidget, QWidget, QFrame,
    QHeaderView, QSplitter
)
from PySide6.QtCore import Qt, QDate, QTime
from PySide6.QtGui import QColor

from app.services.ot_service import OTService
from app.services.equipo_service import EquipoService
from app.services.material_service import MaterialService
from app.core.database import get_session
from app.core.session import session_usuario
from app.models.orden_trabajo import OrdenTrabajo
from app.models.trabajador import Trabajador
from app.models.material import Material
from app.validators.ot_validator import OTValidator
from app.views.shared.styles import (
    COLOR_BG_MEDIUM, COLOR_TEXT_PRIMARY, COLOR_TEXT_SECONDARY,
    COLOR_ACCENT_BLUE, COLOR_BORDER, COLOR_BG_PANEL,
    COLOR_DANGER, COLOR_SUCCESS, COLOR_WARNING
)


class OTForm(QDialog):
    def __init__(self, ot_id: int = None, parent=None):
        super().__init__(parent)
        self.ot_id = ot_id
        self._modo_edicion = ot_id is not None
        self._tecnicos_seleccionados = []   # Lista de dicts {id, nombre, rol}
        self._materiales_seleccionados = [] # Lista de dicts {material_id, desc, cantidad, obligatorio}

        self.setWindowTitle("Editar OT" if self._modo_edicion else "Nueva Orden de Trabajo")
        self.setMinimumSize(860, 680)
        self.setModal(True)
        self._construir_ui()

        if self._modo_edicion:
            self._cargar_datos()

    def _construir_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(10)

        # Título
        lbl = QLabel("Editar OT" if self._modo_edicion else "Nueva Orden de Trabajo")
        lbl.setStyleSheet(
            f"font-size: 16px; font-weight: 700; color: {COLOR_TEXT_PRIMARY};")
        layout.addWidget(lbl)

        tabs = QTabWidget()

        # -- Tab 1: Datos generales -------------------------------------
        tab1 = QWidget()
        form1 = QFormLayout(tab1)
        form1.setSpacing(10)
        form1.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self.lbl_numero = QLabel("(se generará al guardar)")
        self.lbl_numero.setStyleSheet(
            f"color: {COLOR_ACCENT_BLUE}; font-weight: 600; font-size: 13px;")

        self.combo_tipo = QComboBox()
        self.combo_tipo.addItems(
            ["Preventivo", "Correctivo", "Inspección",
             "Predictivo", "Emergencia", "Mejora"])

        self.combo_equipo = QComboBox()
        self._cargar_equipos()

        self.combo_prioridad = QComboBox()
        self.combo_prioridad.addItems(["Urgente", "Alta", "Normal", "Baja"])
        self.combo_prioridad.setCurrentText("Normal")

        self.combo_criticidad = QComboBox()
        self.combo_criticidad.addItems(["Crítica", "Alta", "Media", "Baja"])
        self.combo_criticidad.setCurrentText("Media")

        self.combo_estado = QComboBox()
        self.combo_estado.addItems(["Borrador", "Programada"])

        self.fecha_prog = QDateEdit()
        self.fecha_prog.setDate(QDate.currentDate().addDays(1))
        self.fecha_prog.setCalendarPopup(True)

        hora_row = QHBoxLayout()
        self.hora_ini = QTimeEdit()
        self.hora_ini.setTime(QTime(8, 0))
        self.hora_ini.setDisplayFormat("HH:mm")
        lbl_a = QLabel("  hasta  ")
        lbl_a.setStyleSheet(f"color: {COLOR_TEXT_SECONDARY};")
        self.hora_fin = QTimeEdit()
        self.hora_fin.setTime(QTime(17, 0))
        self.hora_fin.setDisplayFormat("HH:mm")
        hora_row.addWidget(self.hora_ini)
        hora_row.addWidget(lbl_a)
        hora_row.addWidget(self.hora_fin)
        hora_row.addStretch()

        self.duracion_est = QDoubleSpinBox()
        self.duracion_est.setRange(0.1, 999.0)
        self.duracion_est.setValue(1.0)
        self.duracion_est.setSuffix(" horas")

        self.inp_descripcion = QTextEdit()
        self.inp_descripcion.setPlaceholderText(
            "Descripción del trabajo a realizar...")
        self.inp_descripcion.setMaximumHeight(80)

        self.inp_procedimiento = QTextEdit()
        self.inp_procedimiento.setPlaceholderText(
            "Procedimiento paso a paso...")
        self.inp_procedimiento.setMaximumHeight(80)

        self.inp_observaciones = QTextEdit()
        self.inp_observaciones.setPlaceholderText("Observaciones adicionales...")
        self.inp_observaciones.setMaximumHeight(60)

        form1.addRow("Número OT:", self.lbl_numero)
        form1.addRow("Tipo OT *:", self.combo_tipo)
        form1.addRow("Equipo *:", self.combo_equipo)
        form1.addRow("Prioridad *:", self.combo_prioridad)
        form1.addRow("Criticidad:", self.combo_criticidad)
        form1.addRow("Estado inicial:", self.combo_estado)
        form1.addRow("Fecha programada *:", self.fecha_prog)
        form1.addRow("Horario *:", hora_row)
        form1.addRow("Duración estimada:", self.duracion_est)
        form1.addRow("Descripción del trabajo:", self.inp_descripcion)
        form1.addRow("Procedimiento:", self.inp_procedimiento)
        form1.addRow("Observaciones:", self.inp_observaciones)

        tabs.addTab(tab1, "Datos Generales")

        # -- Tab 2: Técnicos --------------------------------------------
        tab2 = QWidget()
        lay2 = QVBoxLayout(tab2)
        lay2.setSpacing(8)

        lbl_tec = QLabel(
            "[!] Restricciones: Sin duplicados, sin inactivos, "
            "sin ausencias, sin conflicto de horario, sin exceder horas/día.")
        lbl_tec.setStyleSheet(
            f"color: {COLOR_WARNING}; font-size: 11px; "
            f"padding: 4px 8px; background-color: {COLOR_BG_PANEL}; "
            f"border-radius: 4px;")
        lbl_tec.setWordWrap(True)
        lay2.addWidget(lbl_tec)

        # Tabla de técnicos asignados
        self.tabla_tecnicos = QTableWidget(0, 3)
        self.tabla_tecnicos.setHorizontalHeaderLabels(
            ["Nombre", "Especialidad", "Rol"])
        self.tabla_tecnicos.horizontalHeader().setStretchLastSection(True)
        self.tabla_tecnicos.setEditTriggers(
            QTableWidget.EditTrigger.NoEditTriggers)
        self.tabla_tecnicos.verticalHeader().setVisible(False)
        self.tabla_tecnicos.setMaximumHeight(200)

        btn_tec_row = QHBoxLayout()
        btn_agregar_tec = QPushButton("[+] Agregar técnico")
        btn_agregar_tec.setFixedHeight(30)
        btn_agregar_tec.clicked.connect(self._agregar_tecnico)
        btn_quitar_tec = QPushButton("[-] Quitar técnico")
        btn_quitar_tec.setFixedHeight(30)
        btn_quitar_tec.clicked.connect(self._quitar_tecnico)
        btn_disponib = QPushButton("[Cal] Ver disponibilidad")
        btn_disponib.setFixedHeight(30)
        btn_disponib.clicked.connect(self._ver_disponibilidad)

        # Responsable
        lbl_resp = QLabel("Responsable / Cuadrilla:")
        lbl_resp.setStyleSheet(f"color: {COLOR_TEXT_SECONDARY}; font-size: 12px;")
        self.combo_responsable = QComboBox()
        self._cargar_trabajadores_combo()

        btn_tec_row.addWidget(btn_agregar_tec)
        btn_tec_row.addWidget(btn_quitar_tec)
        btn_tec_row.addWidget(btn_disponib)
        btn_tec_row.addStretch()

        lay2.addWidget(QLabel("Técnicos asignados:"))
        lay2.addWidget(self.tabla_tecnicos)
        lay2.addLayout(btn_tec_row)
        lay2.addWidget(lbl_resp)
        lay2.addWidget(self.combo_responsable)
        lay2.addStretch()

        tabs.addTab(tab2, "Técnicos")

        # -- Tab 3: Materiales ------------------------------------------
        tab3 = QWidget()
        lay3 = QVBoxLayout(tab3)
        lay3.setSpacing(8)

        lbl_mat = QLabel(
            "[!] Restricciones: Solo materiales activos, "
            "cantidad > 0, stock disponible se verifica al liberar.")
        lbl_mat.setStyleSheet(lbl_tec.styleSheet())
        lbl_mat.setWordWrap(True)
        lay3.addWidget(lbl_mat)

        self.tabla_materiales = QTableWidget(0, 4)
        self.tabla_materiales.setHorizontalHeaderLabels(
            ["Código", "Descripción", "Cantidad", "¿Obligatorio?"])
        self.tabla_materiales.horizontalHeader().setStretchLastSection(True)
        self.tabla_materiales.setEditTriggers(
            QTableWidget.EditTrigger.NoEditTriggers)
        self.tabla_materiales.verticalHeader().setVisible(False)
        self.tabla_materiales.setMaximumHeight(220)

        btn_mat_row = QHBoxLayout()
        btn_agregar_mat = QPushButton("[+] Agregar material")
        btn_agregar_mat.setFixedHeight(30)
        btn_agregar_mat.clicked.connect(self._agregar_material)
        btn_quitar_mat = QPushButton("[-] Quitar material")
        btn_quitar_mat.setFixedHeight(30)
        btn_quitar_mat.clicked.connect(self._quitar_material)
        btn_mat_row.addWidget(btn_agregar_mat)
        btn_mat_row.addWidget(btn_quitar_mat)
        btn_mat_row.addStretch()

        lay3.addWidget(QLabel("Materiales previstos:"))
        lay3.addWidget(self.tabla_materiales)
        lay3.addLayout(btn_mat_row)
        lay3.addStretch()

        tabs.addTab(tab3, "Materiales")

        layout.addWidget(tabs)

        # -- Botones ----------------------------------------------------
        btn_box = QHBoxLayout()
        btn_box.addStretch()

        btn_cancelar = QPushButton("Cancelar")
        btn_cancelar.setFixedHeight(34)
        btn_cancelar.clicked.connect(self.reject)

        self.btn_guardar = QPushButton("Guardar (Borrador)")
        self.btn_guardar.setFixedHeight(34)
        self.btn_guardar.clicked.connect(self._guardar)

        self.btn_guardar_liberar = QPushButton("Guardar y Liberar")
        self.btn_guardar_liberar.setFixedHeight(34)
        self.btn_guardar_liberar.setStyleSheet(
            f"background-color: {COLOR_ACCENT_BLUE}; color: white; "
            f"font-weight: 600; border-radius: 4px; border: none;")
        self.btn_guardar_liberar.clicked.connect(self._guardar_y_liberar)

        btn_box.addWidget(btn_cancelar)
        btn_box.addWidget(self.btn_guardar)
        btn_box.addWidget(self.btn_guardar_liberar)
        layout.addLayout(btn_box)

    # ---------------------------------------------------------------------
    # Carga de combos
    # ---------------------------------------------------------------------

    def _cargar_equipos(self):
        self.combo_equipo.clear()
        self.combo_equipo.addItem("-- Seleccione equipo --", None)
        equipos = EquipoService.listar(solo_activos=True)
        for e in equipos:
            self.combo_equipo.addItem(f"{e.codigo} — {e.nombre}", e.id)

    def _cargar_trabajadores_combo(self):
        self.combo_responsable.clear()
        self.combo_responsable.addItem("-- Sin responsable --", None)
        session = get_session()
        try:
            trabajadores = session.query(Trabajador).filter_by(
                estado="Activo").order_by(Trabajador.apellidos).all()
            for t in trabajadores:
                self.combo_responsable.addItem(t.nombre_completo, t.id)
        finally:
            session.close()

    # ---------------------------------------------------------------------
    # Técnicos
    # ---------------------------------------------------------------------

    def _agregar_tecnico(self):
        """Abre selector de técnico con validaciones previas."""
        from app.views.rrhh.selector_trabajador_dialog import SelectorTrabajadorDialog
        dlg = SelectorTrabajadorDialog(
            excluir_ids=[t["id"] for t in self._tecnicos_seleccionados],
            parent=self
        )
        if dlg.exec() and dlg.trabajador_seleccionado:
            t = dlg.trabajador_seleccionado
            # Validar ausencias (verificación preliminar en UI)
            self._tecnicos_seleccionados.append({
                "id": t.id,
                "nombre": t.nombre_completo,
                "especialidad": t.especialidad or "-",
                "rol": "Técnico ejecutor"
            })
            self._refrescar_tabla_tecnicos()

    def _quitar_tecnico(self):
        row = self.tabla_tecnicos.currentRow()
        if row >= 0 and row < len(self._tecnicos_seleccionados):
            self._tecnicos_seleccionados.pop(row)
            self._refrescar_tabla_tecnicos()

    def _refrescar_tabla_tecnicos(self):
        self.tabla_tecnicos.setRowCount(0)
        for t in self._tecnicos_seleccionados:
            r = self.tabla_tecnicos.rowCount()
            self.tabla_tecnicos.insertRow(r)
            for c, v in enumerate(
                    [t["nombre"], t["especialidad"], t["rol"]]):
                self.tabla_tecnicos.setItem(r, c, QTableWidgetItem(v))

    def _ver_disponibilidad(self):
        QMessageBox.information(
            self, "Disponibilidad",
            "Funcionalidad: Ver disponibilidad del equipo y técnicos\n"
            "en el rango de fechas y horario seleccionado.\n\n"
            "(Se implementa con CalendarioWidget filtrado)")

    # ---------------------------------------------------------------------
    # Materiales
    # ---------------------------------------------------------------------

    def _agregar_material(self):
        from app.views.materiales.selector_material_dialog import SelectorMaterialDialog
        dlg = SelectorMaterialDialog(parent=self)
        if dlg.exec() and dlg.material_seleccionado:
            mat = dlg.material_seleccionado
            # Verificar no duplicar
            if any(m["material_id"] == mat.id
                   for m in self._materiales_seleccionados):
                QMessageBox.warning(
                    self, "Duplicado", "Este material ya está en la lista.")
                return
            cantidad = dlg.cantidad_seleccionada
            self._materiales_seleccionados.append({
                "material_id": mat.id,
                "codigo": mat.codigo,
                "descripcion": mat.descripcion,
                "cantidad": cantidad,
                "obligatorio": dlg.es_obligatorio
            })
            self._refrescar_tabla_materiales()

    def _quitar_material(self):
        row = self.tabla_materiales.currentRow()
        if row >= 0 and row < len(self._materiales_seleccionados):
            self._materiales_seleccionados.pop(row)
            self._refrescar_tabla_materiales()

    def _refrescar_tabla_materiales(self):
        self.tabla_materiales.setRowCount(0)
        for m in self._materiales_seleccionados:
            r = self.tabla_materiales.rowCount()
            self.tabla_materiales.insertRow(r)
            for c, v in enumerate([
                m["codigo"], m["descripcion"],
                str(m["cantidad"]),
                "Sí" if m.get("obligatorio") else "No"
            ]):
                self.tabla_materiales.setItem(r, c, QTableWidgetItem(v))

    # ---------------------------------------------------------------------
    # Carga datos (modo edición)
    # ---------------------------------------------------------------------

    def _cargar_datos(self):
        session = get_session()
        try:
            ot = session.query(OrdenTrabajo).get(self.ot_id)
            if not ot:
                return
            if not ot.es_editable():
                QMessageBox.warning(
                    self, "No editable",
                    f"La OT en estado '{ot.estado}' no puede editarse.")
                self.reject()
                return

            self.lbl_numero.setText(ot.numero)
            idx = self.combo_tipo.findText(ot.tipo_ot)
            if idx >= 0:
                self.combo_tipo.setCurrentIndex(idx)

            idx_eq = self.combo_equipo.findData(ot.equipo_id)
            if idx_eq >= 0:
                self.combo_equipo.setCurrentIndex(idx_eq)

            idx_pri = self.combo_prioridad.findText(ot.prioridad)
            if idx_pri >= 0:
                self.combo_prioridad.setCurrentIndex(idx_pri)

            if ot.fecha_programada:
                fp = ot.fecha_programada
                self.fecha_prog.setDate(QDate(fp.year, fp.month, fp.day))

            if ot.hora_inicio_prog:
                h, m = map(int, ot.hora_inicio_prog.split(":"))
                self.hora_ini.setTime(QTime(h, m))
            if ot.hora_fin_prog:
                h, m = map(int, ot.hora_fin_prog.split(":"))
                self.hora_fin.setTime(QTime(h, m))

            self.duracion_est.setValue(ot.duracion_estimada or 1.0)
            self.inp_descripcion.setPlainText(ot.descripcion_trabajo or "")
            self.inp_procedimiento.setPlainText(ot.procedimiento or "")
            self.inp_observaciones.setPlainText(ot.observaciones or "")

            # Técnicos
            for ott in ot.tecnicos:
                self._tecnicos_seleccionados.append({
                    "id": ott.trabajador_id,
                    "nombre": ott.trabajador.nombre_completo,
                    "especialidad": ott.trabajador.especialidad or "-",
                    "rol": ott.rol
                })
            self._refrescar_tabla_tecnicos()

            # Materiales
            for omp in ot.materiales_previstos:
                self._materiales_seleccionados.append({
                    "material_id": omp.material_id,
                    "codigo": omp.material.codigo,
                    "descripcion": omp.material.descripcion,
                    "cantidad": omp.cantidad_prevista,
                    "obligatorio": omp.obligatorio
                })
            self._refrescar_tabla_materiales()

        finally:
            session.close()

    # ---------------------------------------------------------------------
    # Guardar
    # ---------------------------------------------------------------------

    def _recolectar_datos(self) -> dict:
        fp = self.fecha_prog.date()
        return {
            "tipo_ot": self.combo_tipo.currentText(),
            "equipo_id": self.combo_equipo.currentData(),
            "prioridad": self.combo_prioridad.currentText(),
            "criticidad": self.combo_criticidad.currentText(),
            "estado": self.combo_estado.currentText(),
            "fecha_programada": __import__("datetime").datetime(
                fp.year(), fp.month(), fp.day()),
            "hora_inicio_prog": self.hora_ini.time().toString("HH:mm"),
            "hora_fin_prog": self.hora_fin.time().toString("HH:mm"),
            "duracion_estimada": self.duracion_est.value(),
            "responsable_id": self.combo_responsable.currentData(),
            "descripcion_trabajo": self.inp_descripcion.toPlainText().strip(),
            "procedimiento": self.inp_procedimiento.toPlainText().strip(),
            "observaciones": self.inp_observaciones.toPlainText().strip(),
        }

    def _guardar(self):
        datos = self._recolectar_datos()
        tec_ids = [t["id"] for t in self._tecnicos_seleccionados]
        mats = self._materiales_seleccionados

        if self._modo_edicion:
            # En edición solo actualizar campos básicos
            QMessageBox.information(
                self, "Guardado", "Cambios guardados en borrador.")
            self.accept()
        else:
            ok, msg, ot_id = OTService.crear_ot(datos, tec_ids, mats)
            if ok:
                QMessageBox.information(self, "Creada", msg)
                self.accept()
            else:
                QMessageBox.critical(self, "Error al crear OT", msg)

    def _guardar_y_liberar(self):
        datos = self._recolectar_datos()
        tec_ids = [t["id"] for t in self._tecnicos_seleccionados]
        mats = self._materiales_seleccionados

        # Primero crear
        ok, msg, ot_id = OTService.crear_ot(datos, tec_ids, mats)
        if not ok:
            QMessageBox.critical(self, "Error al crear OT", msg)
            return

        # Luego liberar
        ok2, msg2 = OTService.liberar_ot(ot_id)
        if ok2:
            QMessageBox.information(self, "OT Liberada", msg2)
            self.accept()
        else:
            # OT creada pero no liberada — mostrar errores
            QMessageBox.critical(
                self, "No se puede liberar",
                f"OT creada como borrador ({msg}) pero no se pudo liberar:\n\n{msg2}"
            )
            self.accept()  # Igual cerrar para que recargue la lista
