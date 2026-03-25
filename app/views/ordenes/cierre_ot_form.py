"""
Formulario de Cierre de OT.
Registra: horas reales, materiales consumidos,
causa raíz, tiempo fuera de servicio y observaciones finales.
"""
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLabel, QLineEdit, QPushButton, QComboBox,
    QDoubleSpinBox, QTextEdit, QTableWidget,
    QTableWidgetItem, QMessageBox, QTabWidget,
    QWidget, QFrame, QCheckBox, QSpinBox
)
from PySide6.QtCore import Qt, QDate, QTime
from PySide6.QtGui import QColor

from app.core.database import get_session
from app.models.orden_trabajo import OrdenTrabajo, OTMaterialConsumido
from app.services.ot_service import OTService
from app.services.material_service import MaterialService
from app.views.shared.styles import (
    COLOR_TEXT_PRIMARY, COLOR_TEXT_SECONDARY, COLOR_ACCENT_BLUE,
    COLOR_BORDER, COLOR_BG_PANEL, COLOR_WARNING, COLOR_DANGER, COLOR_SUCCESS
)


class CierreOTForm(QDialog):
    def __init__(self, ot_id: int, parent=None):
        super().__init__(parent)
        self.ot_id = ot_id
        self._materiales_consumidos = []  # [{material_id, codigo, desc, cantidad, costo}]
        self.setWindowTitle("Cierre de Orden de Trabajo")
        self.setMinimumSize(780, 620)
        self.setModal(True)
        self._ot = self._cargar_ot()
        if not self._ot:
            QMessageBox.critical(parent, "Error", "OT no encontrada.")
            self.reject()
            return
        self._construir_ui()
        self._precargar_materiales_previstos()

    def _cargar_ot(self):
        session = get_session()
        try:
            ot = session.query(OrdenTrabajo).get(self.ot_id)
            if ot:
                session.expunge(ot)
            return ot
        finally:
            session.close()

    def _construir_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(10)

        # Encabezado
        enc = QHBoxLayout()
        lbl_tit = QLabel(f"Cierre de OT — {self._ot.numero}")
        lbl_tit.setStyleSheet(
            f"font-size: 16px; font-weight: 700; color: {COLOR_TEXT_PRIMARY};")
        lbl_estado = QLabel(f"Estado actual: {self._ot.estado}")
        lbl_estado.setStyleSheet(
            f"font-size: 12px; color: {COLOR_WARNING}; font-weight: 600;")
        enc.addWidget(lbl_tit)
        enc.addStretch()
        enc.addWidget(lbl_estado)
        layout.addLayout(enc)

        # Advertencia si no está En proceso
        if self._ot.estado != "En proceso":
            lbl_adv = QLabel(
                f"[!]  Esta OT está en estado '{self._ot.estado}'. "
                "Solo se pueden cerrar OTs en estado 'En proceso'.")
            lbl_adv.setStyleSheet(
                f"background-color: #B71C1C30; color: {COLOR_DANGER}; "
                f"border: 1px solid {COLOR_DANGER}; border-radius: 4px; "
                f"padding: 6px 10px; font-size: 12px;")
            lbl_adv.setWordWrap(True)
            layout.addWidget(lbl_adv)

        tabs = QTabWidget()

        # -- Tab 1: Resumen y Tiempos -----------------------------------
        tab1 = QWidget()
        form1 = QFormLayout(tab1)
        form1.setSpacing(10)
        form1.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        # Info de la OT (solo lectura)
        self._agregar_campo_ro(form1, "Número OT:", self._ot.numero)
        self._agregar_campo_ro(
            form1, "Equipo:",
            self._ot.equipo.nombre if hasattr(self._ot, 'equipo') and self._ot.equipo else "-"
        )
        self._agregar_campo_ro(form1, "Tipo:", self._ot.tipo_ot)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet(f"border: none; border-top: 1px solid {COLOR_BORDER};")
        form1.addRow(sep)

        # Campos de cierre
        self.inp_horas_reales = QDoubleSpinBox()
        self.inp_horas_reales.setRange(0.1, 9999.0)
        self.inp_horas_reales.setDecimals(2)
        self.inp_horas_reales.setValue(self._ot.duracion_estimada or 1.0)
        self.inp_horas_reales.setSuffix(" horas")

        self.inp_tiempo_fuera = QDoubleSpinBox()
        self.inp_tiempo_fuera.setRange(0, 9999.0)
        self.inp_tiempo_fuera.setDecimals(2)
        self.inp_tiempo_fuera.setSuffix(" horas")

        self.combo_resultado = QComboBox()
        self.combo_resultado.addItems([
            "Trabajo completado",
            "Completado con observaciones",
            "Trabajo parcial — requiere seguimiento",
            "Equipo no disponible — reprogramar",
        ])

        self.combo_causa_raiz = QComboBox()
        self.combo_causa_raiz.addItems([
            "N/A (preventivo / no aplica)",
            "Desgaste normal",
            "Rotura / fractura",
            "Corrosión",
            "Contaminación",
            "Error de operación",
            "Falta de lubricación",
            "Falla eléctrica",
            "Falla mecánica",
            "Causa desconocida",
            "Otra",
        ])

        self.inp_causa_raiz_desc = QLineEdit()
        self.inp_causa_raiz_desc.setPlaceholderText(
            "Descripción detallada de la causa raíz (si aplica)...")

        self.inp_costo_mano_obra = QDoubleSpinBox()
        self.inp_costo_mano_obra.setRange(0, 9999999.99)
        self.inp_costo_mano_obra.setDecimals(2)
        self.inp_costo_mano_obra.setGroupSeparatorShown(True)

        self.inp_costo_externo = QDoubleSpinBox()
        self.inp_costo_externo.setRange(0, 9999999.99)
        self.inp_costo_externo.setDecimals(2)
        self.inp_costo_externo.setGroupSeparatorShown(True)

        self.chk_requiere_seguimiento = QCheckBox(
            "Requiere seguimiento / generar nueva OT correctiva")

        self.inp_observaciones = QTextEdit()
        self.inp_observaciones.setPlaceholderText(
            "Observaciones finales, trabajos realizados, hallazgos...")
        self.inp_observaciones.setMinimumHeight(80)

        form1.addRow("Horas reales trabajadas *:", self.inp_horas_reales)
        form1.addRow("Tiempo fuera de servicio *:", self.inp_tiempo_fuera)
        form1.addRow("Resultado del trabajo *:", self.combo_resultado)
        form1.addRow("Causa raíz (fallas):", self.combo_causa_raiz)
        form1.addRow("Detalle causa raíz:", self.inp_causa_raiz_desc)
        form1.addRow("Costo mano de obra:", self.inp_costo_mano_obra)
        form1.addRow("Costo servicio externo:", self.inp_costo_externo)
        form1.addRow("", self.chk_requiere_seguimiento)
        form1.addRow("Observaciones finales:", self.inp_observaciones)

        tabs.addTab(tab1, "Resumen y Tiempos")

        # -- Tab 2: Materiales Consumidos -------------------------------
        tab2 = QWidget()
        lay2 = QVBoxLayout(tab2)
        lay2.setSpacing(8)

        lbl_mat = QLabel(
            "Registre los materiales efectivamente consumidos. "
            "Se actualizará el stock automáticamente al cerrar.")
        lbl_mat.setStyleSheet(
            f"color: {COLOR_WARNING}; font-size: 11px; "
            f"background-color: {COLOR_BG_PANEL}; "
            f"padding: 4px 8px; border-radius: 4px;")
        lbl_mat.setWordWrap(True)
        lay2.addWidget(lbl_mat)

        self.tabla_consumidos = QTableWidget(0, 5)
        self.tabla_consumidos.setHorizontalHeaderLabels(
            ["Código", "Descripción", "Cant. Prevista",
             "Cant. Consumida", "Costo Unit."])
        self.tabla_consumidos.horizontalHeader().setStretchLastSection(True)
        self.tabla_consumidos.setEditTriggers(
            QTableWidget.EditTrigger.DoubleClicked)
        self.tabla_consumidos.verticalHeader().setVisible(False)
        self.tabla_consumidos.setMinimumHeight(200)
        lay2.addWidget(self.tabla_consumidos)

        btn_mat_row = QHBoxLayout()
        btn_agregar_cons = QPushButton("[+] Agregar material")
        btn_agregar_cons.setFixedHeight(30)
        btn_agregar_cons.clicked.connect(self._agregar_material_consumido)
        btn_quitar_cons = QPushButton("[-] Quitar")
        btn_quitar_cons.setFixedHeight(30)
        btn_quitar_cons.clicked.connect(self._quitar_material_consumido)

        self.lbl_costo_materiales = QLabel("Costo materiales: 0.00")
        self.lbl_costo_materiales.setStyleSheet(
            f"color: {COLOR_ACCENT_BLUE}; font-weight: 600; font-size: 12px;")

        btn_mat_row.addWidget(btn_agregar_cons)
        btn_mat_row.addWidget(btn_quitar_cons)
        btn_mat_row.addStretch()
        btn_mat_row.addWidget(self.lbl_costo_materiales)
        lay2.addLayout(btn_mat_row)
        lay2.addStretch()

        tabs.addTab(tab2, "Materiales Consumidos")

        layout.addWidget(tabs)

        # -- Totales ----------------------------------------------------
        total_frame = QFrame()
        total_frame.setStyleSheet(
            f"background-color: {COLOR_BG_PANEL}; border-radius: 6px; "
            f"border: 1px solid {COLOR_BORDER}; padding: 8px;")
        total_lay = QHBoxLayout(total_frame)
        lbl_tot_tit = QLabel("Costo Total estimado:")
        lbl_tot_tit.setStyleSheet(
            f"color: {COLOR_TEXT_SECONDARY}; font-weight: 600;")
        self.lbl_costo_total = QLabel("0.00")
        self.lbl_costo_total.setStyleSheet(
            f"color: {COLOR_ACCENT_BLUE}; font-size: 18px; font-weight: 700;")

        total_lay.addStretch()
        total_lay.addWidget(lbl_tot_tit)
        total_lay.addWidget(self.lbl_costo_total)
        layout.addWidget(total_frame)

        # Conectar para actualizar totales
        self.inp_costo_mano_obra.valueChanged.connect(self._actualizar_total)
        self.inp_costo_externo.valueChanged.connect(self._actualizar_total)

        # -- Botones ----------------------------------------------------
        btn_box = QHBoxLayout()
        btn_box.addStretch()

        btn_cancelar = QPushButton("Cancelar")
        btn_cancelar.setFixedHeight(34)
        btn_cancelar.clicked.connect(self.reject)

        self.btn_cerrar_ot = QPushButton("  [OK] Cerrar OT  ")
        self.btn_cerrar_ot.setFixedHeight(38)
        self.btn_cerrar_ot.setStyleSheet(
            f"background-color: #2E7D32; color: white; font-weight: 700; "
            f"font-size: 14px; border-radius: 6px; border: none;")
        self.btn_cerrar_ot.clicked.connect(self._cerrar_ot)

        if self._ot.estado != "En proceso":
            self.btn_cerrar_ot.setEnabled(False)
            self.btn_cerrar_ot.setStyleSheet(
                "background-color: #555; color: #999; border-radius: 6px; "
                "border: none; font-size: 14px;")

        btn_box.addWidget(btn_cancelar)
        btn_box.addWidget(self.btn_cerrar_ot)
        layout.addLayout(btn_box)

    def _agregar_campo_ro(self, form: QFormLayout, label: str, valor: str):
        """Agrega fila de solo lectura al formulario."""
        lbl_val = QLabel(valor)
        lbl_val.setStyleSheet(
            f"color: {COLOR_TEXT_PRIMARY}; font-weight: 500;")
        lbl_key = QLabel(label)
        lbl_key.setStyleSheet(f"color: {COLOR_TEXT_SECONDARY};")
        form.addRow(lbl_key, lbl_val)

    # ---------------------------------------------------------------------
    # Materiales consumidos
    # ---------------------------------------------------------------------

    def _precargar_materiales_previstos(self):
        """Precarga los materiales previstos como punto de partida."""
        session = get_session()
        try:
            ot = session.query(OrdenTrabajo).get(self.ot_id)
            if not ot:
                return
            for mp in ot.materiales_previstos:
                mat = mp.material
                if not mat:
                    continue
                self._materiales_consumidos.append({
                    "material_id": mat.id,
                    "codigo": mat.codigo,
                    "descripcion": mat.descripcion,
                    "cantidad_prevista": mp.cantidad_prevista,
                    "cantidad_consumida": mp.cantidad_prevista,
                    "costo_unitario": mat.costo_unitario,
                })
        finally:
            session.close()
        self._refrescar_tabla_consumidos()

    def _agregar_material_consumido(self):
        from app.views.materiales.selector_material_dialog import SelectorMaterialDialog
        dlg = SelectorMaterialDialog(parent=self)
        if dlg.exec() and dlg.material_seleccionado:
            mat = dlg.material_seleccionado
            if any(m["material_id"] == mat.id
                   for m in self._materiales_consumidos):
                QMessageBox.warning(self, "Duplicado",
                                     "Este material ya está en la lista.")
                return
            self._materiales_consumidos.append({
                "material_id": mat.id,
                "codigo": mat.codigo,
                "descripcion": mat.descripcion,
                "cantidad_prevista": 0,
                "cantidad_consumida": dlg.cantidad_seleccionada,
                "costo_unitario": mat.costo_unitario,
            })
            self._refrescar_tabla_consumidos()

    def _quitar_material_consumido(self):
        row = self.tabla_consumidos.currentRow()
        if row >= 0 and row < len(self._materiales_consumidos):
            self._materiales_consumidos.pop(row)
            self._refrescar_tabla_consumidos()

    def _refrescar_tabla_consumidos(self):
        self.tabla_consumidos.setRowCount(0)
        total_mats = 0.0
        for m in self._materiales_consumidos:
            r = self.tabla_consumidos.rowCount()
            self.tabla_consumidos.insertRow(r)
            costo = m["costo_unitario"] * m["cantidad_consumida"]
            total_mats += costo
            valores = [
                m["codigo"],
                m["descripcion"],
                str(m["cantidad_prevista"]),
                str(m["cantidad_consumida"]),
                f"{m['costo_unitario']:.2f}",
            ]
            for c, v in enumerate(valores):
                item = QTableWidgetItem(v)
                if c == 3:
                    # La cantidad consumida es editable
                    item.setFlags(
                        item.flags() | Qt.ItemFlag.ItemIsEditable)
                self.tabla_consumidos.setItem(r, c, item)

        self.lbl_costo_materiales.setText(
            f"Costo materiales: {total_mats:,.2f}")
        self._actualizar_total()

    def _actualizar_total(self):
        total_mats = sum(
            m["costo_unitario"] * m["cantidad_consumida"]
            for m in self._materiales_consumidos
        )
        total = (total_mats +
                 self.inp_costo_mano_obra.value() +
                 self.inp_costo_externo.value())
        self.lbl_costo_total.setText(f"{total:,.2f}")

    # ---------------------------------------------------------------------
    # Leer cantidades consumidas editadas en tabla
    # ---------------------------------------------------------------------

    def _leer_cantidades_editadas(self):
        """Sincroniza las cantidades consumidas editadas en la tabla."""
        for row, m in enumerate(self._materiales_consumidos):
            item = self.tabla_consumidos.item(row, 3)
            if item:
                try:
                    m["cantidad_consumida"] = float(item.text().replace(",", "."))
                except ValueError:
                    pass

    # ---------------------------------------------------------------------
    # Cerrar OT
    # ---------------------------------------------------------------------

    def _cerrar_ot(self):
        self._leer_cantidades_editadas()

        horas_reales = self.inp_horas_reales.value()
        tiempo_fuera = self.inp_tiempo_fuera.value()
        resultado = self.combo_resultado.currentText()

        if horas_reales <= 0:
            QMessageBox.warning(
                self, "Campo requerido",
                "Ingrese las horas reales trabajadas (mayor a 0).")
            return

        causa_raiz = self.combo_causa_raiz.currentText()
        causa_desc = self.inp_causa_raiz_desc.text().strip()
        costo_mo = self.inp_costo_mano_obra.value()
        costo_ext = self.inp_costo_externo.value()
        observaciones = self.inp_observaciones.toPlainText().strip()
        requiere_seguimiento = self.chk_requiere_seguimiento.isChecked()

        # Construir lista de materiales consumidos para el servicio
        mats_cons = []
        for m in self._materiales_consumidos:
            if m["cantidad_consumida"] > 0:
                mats_cons.append({
                    "material_id": m["material_id"],
                    "cantidad_consumida": m["cantidad_consumida"],
                    "costo_unitario": m["costo_unitario"],
                })

        datos_cierre = {
            "horas_reales": horas_reales,
            "tiempo_fuera_servicio": tiempo_fuera,
            "resultado": resultado,
            "causa_raiz": causa_raiz,
            "causa_raiz_descripcion": causa_desc,
            "costo_mano_obra": costo_mo,
            "costo_externo": costo_ext,
            "observaciones_cierre": observaciones,
            "requiere_seguimiento": requiere_seguimiento,
        }

        resp = QMessageBox.question(
            self,
            "Confirmar cierre",
            f"¿Desea cerrar la OT {self._ot.numero}?\n\n"
            f"Horas reales: {horas_reales:.2f} h\n"
            f"Tiempo fuera de servicio: {tiempo_fuera:.2f} h\n"
            f"Materiales a descontar: {len(mats_cons)} ítem(s)\n"
            f"Resultado: {resultado}\n\n"
            "Esta acción no se puede deshacer.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if resp != QMessageBox.StandardButton.Yes:
            return

        ok, msg = OTService.cerrar_ot(self.ot_id, datos_cierre, mats_cons)
        if ok:
            QMessageBox.information(self, "OT Cerrada", msg)
            # Si requiere seguimiento, ofrecer crear nueva OT correctiva
            if requiere_seguimiento:
                resp2 = QMessageBox.question(
                    self,
                    "Nueva OT Correctiva",
                    "La OT indica seguimiento requerido.\n"
                    "¿Desea generar una nueva OT correctiva ahora?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                )
                if resp2 == QMessageBox.StandardButton.Yes:
                    from app.views.ordenes.ot_form import OTForm
                    dlg = OTForm(parent=self)
                    dlg.combo_tipo.setCurrentText("Correctivo")
                    dlg.exec()
            self.accept()
        else:
            QMessageBox.critical(self, "Error al cerrar", msg)
