"""
Modulo Planes de Mantenimiento - completo.
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFrame, QMessageBox, QComboBox,
    QDialog, QFormLayout, QLineEdit, QDoubleSpinBox,
    QSpinBox, QTextEdit, QComboBox, QTabWidget,
    QTableWidget, QTableWidgetItem, QHeaderView,
    QDateEdit, QCheckBox
)
from PySide6.QtCore import Qt, QDate
from app.views.shared.tabla_base import TablaBase
from app.services.plan_service import PlanService
from app.services.equipo_service import EquipoService
from app.core.session import session_usuario
from app.views.shared.styles import (
    COLOR_TEXT_PRIMARY, COLOR_TEXT_SECONDARY, COLOR_ACCENT_BLUE,
    COLOR_BORDER, COLOR_BG_PANEL, COLOR_SUCCESS, COLOR_DANGER, COLOR_WARNING
)

COLS = [
    {"header": "Codigo",      "key": "codigo",      "width": 110},
    {"header": "Equipo",      "key": "equipo",      "width": 200},
    {"header": "Descripcion", "key": "descripcion", "width": 220},
    {"header": "Tipo",        "key": "tipo",        "width": 100},
    {"header": "Frecuencia",  "key": "frecuencia",  "width": 100},
    {"header": "Proxima Ejec.","key": "proxima",    "width": 100},
    {"header": "Estado",      "key": "estado",      "width": 80},
]

class PlanesWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._construir_ui()
        self.cargar_datos()

    def _construir_ui(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(16,12,16,12)
        lay.setSpacing(10)

        enc = QHBoxLayout()
        lbl = QLabel("Planes de Mantenimiento")
        lbl.setStyleSheet(f"font-size:18px; font-weight:700; color:{COLOR_TEXT_PRIMARY};")
        self.lbl_cnt = QLabel()
        self.lbl_cnt.setStyleSheet(f"color:{COLOR_TEXT_SECONDARY}; font-size:12px;")
        enc.addWidget(lbl); enc.addWidget(self.lbl_cnt); enc.addStretch()
        lay.addLayout(enc)

        # Filtros
        fil = QHBoxLayout(); fil.setSpacing(8)
        self.combo_estado = QComboBox()
        self.combo_estado.addItems(["Todos","Activo","Pausado","Inactivo"])
        self.combo_estado.setFixedWidth(110)
        self.combo_estado.currentIndexChanged.connect(self.cargar_datos)
        self.combo_tipo = QComboBox()
        self.combo_tipo.addItems(["Todos los tipos","Preventivo","Predictivo","Lubricacion","Inspeccion"])
        self.combo_tipo.setFixedWidth(140)
        self.combo_tipo.currentIndexChanged.connect(self.cargar_datos)
        fil.addWidget(QLabel("Estado:")); fil.addWidget(self.combo_estado)
        fil.addWidget(QLabel("Tipo:")); fil.addWidget(self.combo_tipo)
        fil.addStretch()
        lay.addLayout(fil)

        self.tabla = TablaBase(columnas=COLS, columna_estado="estado")
        self.tabla.doble_click.connect(self._ver_detalle)
        lay.addWidget(self.tabla)

        btn_frame = QFrame()
        btn_frame.setStyleSheet(f"background-color:{COLOR_BG_PANEL}; border-radius:6px; border:1px solid {COLOR_BORDER}; padding:6px;")
        bl = QHBoxLayout(btn_frame); bl.setSpacing(6)
        for txt, cb, est in [
            ("+ Nuevo Plan",       self._nuevo,      "primary"),
            ("Editar",             self._editar,     "normal"),
            ("Ver Detalle",        self._ver_detalle_btn, "normal"),
            ("Pausar",             self._pausar,     "normal"),
            ("Reactivar",          self._reactivar,  "success"),
            ("Duplicar",           self._duplicar,   "normal"),
            ("Generar OTs ahora",  self._gen_ots,    "primary"),
            ("Exportar",           self._exportar,   "normal"),
        ]:
            b = QPushButton(txt); b.setFixedHeight(30)
            if est == "primary":
                b.setStyleSheet(f"background-color:{COLOR_ACCENT_BLUE}; color:white; border-radius:4px; border:none; padding:0 10px; font-size:12px; font-weight:600;")
            elif est == "success":
                b.setStyleSheet(f"background-color:#2E7D32; color:white; border-radius:4px; border:none; padding:0 10px; font-size:12px;")
            b.clicked.connect(cb); bl.addWidget(b)
        bl.addStretch()
        lay.addWidget(btn_frame)

    def cargar_datos(self):
        estado = self.combo_estado.currentText()
        tipo   = self.combo_tipo.currentText()
        planes = PlanService.listar(
            estado=None if estado=="Todos" else estado,
        )
        if tipo != "Todos los tipos":
            planes = [p for p in planes if p.tipo_mantenimiento == tipo]

        datos, ids = [], []
        for p in planes:
            try: eq_nom = p.equipo.nombre if p.equipo else "-"
            except: eq_nom = "-"
            prox = p.proxima_ejecucion.strftime("%d/%m/%Y") if p.proxima_ejecucion else "-"
            datos.append({
                "codigo":      p.codigo,
                "equipo":      eq_nom,
                "descripcion": p.descripcion or "-",
                "tipo":        p.tipo_mantenimiento,
                "frecuencia":  f"{p.frecuencia:.0f} {p.unidad_frecuencia}",
                "proxima":     prox,
                "estado":      p.estado,
            })
            ids.append(p.id)
        self.tabla.cargar(datos, ids)
        self.lbl_cnt.setText(f"{len(planes)} plan(es)")

    def _nuevo(self):
        dlg = PlanForm(parent=self)
        if dlg.exec(): self.cargar_datos()

    def _editar(self):
        pid = self.tabla.id_seleccionado()
        if not pid: QMessageBox.information(self,"Seleccionar","Seleccione un plan."); return
        dlg = PlanForm(plan_id=pid, parent=self)
        if dlg.exec(): self.cargar_datos()

    def _ver_detalle(self, pid=None):
        eid = pid or self.tabla.id_seleccionado()
        if not eid: return
        from app.core.database import get_session
        from app.models.plan import PlanMantenimiento
        session = get_session()
        try:
            p = session.query(PlanMantenimiento).get(eid)
            if not p: return
            try: eq = p.equipo.nombre if p.equipo else "-"
            except: eq = "-"
            QMessageBox.information(self, f"Plan {p.codigo}",
                f"Codigo: {p.codigo}\nEquipo: {eq}\nTipo: {p.tipo_mantenimiento}\n"
                f"Frecuencia: {p.frecuencia} {p.unidad_frecuencia}\nCriterio: {p.criterio}\n"
                f"Duracion estimada: {p.duracion_estimada} h\nPrioridad: {p.prioridad}\n"
                f"Estado: {p.estado}\nProxima ejecucion: "
                f"{p.proxima_ejecucion.strftime('%d/%m/%Y') if p.proxima_ejecucion else '-'}\n"
                f"Descripcion: {p.descripcion or '-'}")
        finally: session.close()

    def _ver_detalle_btn(self): self._ver_detalle()

    def _pausar(self):
        pid = self.tabla.id_seleccionado()
        if not pid: return
        ok, msg = PlanService.pausar(pid)
        (QMessageBox.information if ok else QMessageBox.critical)(self, "Pausar", msg)
        if ok: self.cargar_datos()

    def _reactivar(self):
        pid = self.tabla.id_seleccionado()
        if not pid: return
        ok, msg = PlanService.reactivar(pid)
        (QMessageBox.information if ok else QMessageBox.critical)(self, "Reactivar", msg)
        if ok: self.cargar_datos()

    def _duplicar(self):
        pid = self.tabla.id_seleccionado()
        if not pid: QMessageBox.information(self,"Seleccionar","Seleccione un plan."); return
        from PySide6.QtWidgets import QInputDialog
        cod, ok = QInputDialog.getText(self,"Duplicar plan","Nuevo codigo para la copia:")
        if ok and cod.strip():
            ok2, msg, _ = PlanService.duplicar(pid, cod.strip())
            (QMessageBox.information if ok2 else QMessageBox.critical)(self,"Duplicar",msg)
            if ok2: self.cargar_datos()

    def _gen_ots(self):
        resp = QMessageBox.question(self,"Generar OTs",
            "Se generaran OTs para todos los planes activos con fecha vencida.\n\nContinuar?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if resp != QMessageBox.StandardButton.Yes: return
        n, msgs = PlanService.generar_ots_desde_planes()
        resumen = f"OTs generadas: {n}\n\n" + "\n".join(msgs[:10])
        QMessageBox.information(self,"Generacion completada", resumen)
        self.cargar_datos()

    def _exportar(self):
        from PySide6.QtWidgets import QFileDialog
        ruta, _ = QFileDialog.getSaveFileName(self,"Exportar Planes","planes.xlsx","Excel (*.xlsx)")
        if not ruta: return
        try:
            import pandas as pd
            planes = PlanService.listar()
            datos = [{"Codigo":p.codigo,"Tipo":p.tipo_mantenimiento,
                "Frecuencia":f"{p.frecuencia} {p.unidad_frecuencia}",
                "Estado":p.estado,"Prioridad":p.prioridad,
                "Proxima":p.proxima_ejecucion.strftime("%d/%m/%Y") if p.proxima_ejecucion else ""
            } for p in planes]
            pd.DataFrame(datos).to_excel(ruta, index=False)
            QMessageBox.information(self,"Exportado", ruta)
        except Exception as e:
            QMessageBox.critical(self,"Error",str(e))


class PlanForm(QDialog):
    def __init__(self, plan_id=None, parent=None):
        super().__init__(parent)
        self.plan_id = plan_id
        self.setWindowTitle("Editar Plan" if plan_id else "Nuevo Plan de Mantenimiento")
        self.setMinimumSize(580, 520)
        self.setModal(True)
        self._checklist = []
        self._materiales = []
        self._construir_ui()
        if plan_id: self._cargar()

    def _construir_ui(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(20,16,20,16); lay.setSpacing(10)
        lbl = QLabel(self.windowTitle())
        lbl.setStyleSheet(f"font-size:16px; font-weight:700; color:{COLOR_TEXT_PRIMARY};")
        lay.addWidget(lbl)

        tabs = QTabWidget()

        # Tab 1: Datos generales
        t1 = QWidget(); f1 = QFormLayout(t1); f1.setSpacing(9); f1.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        self.inp_codigo = QLineEdit(); self.inp_codigo.setPlaceholderText("Ej: PM-001")
        self.combo_equipo = QComboBox()
        self._cargar_equipos()
        self.inp_descripcion = QLineEdit()
        self.combo_tipo = QComboBox()
        self.combo_tipo.addItems(["Preventivo","Predictivo","Lubricacion","Inspeccion","Mejora"])
        self.inp_frecuencia = QDoubleSpinBox(); self.inp_frecuencia.setRange(0.1,9999); self.inp_frecuencia.setValue(30)
        self.combo_unidad = QComboBox()
        self.combo_unidad.addItems(["Dias","Semanas","Meses","Horas","Kilometros","Ciclos"])
        self.combo_criterio = QComboBox()
        self.combo_criterio.addItems(["Fecha","Contador","Ambos"])
        self.inp_duracion = QDoubleSpinBox(); self.inp_duracion.setRange(0.1,999); self.inp_duracion.setValue(2); self.inp_duracion.setSuffix(" horas")
        self.combo_prioridad = QComboBox()
        self.combo_prioridad.addItems(["Urgente","Alta","Normal","Baja"]); self.combo_prioridad.setCurrentText("Normal")
        self.combo_criticidad = QComboBox()
        self.combo_criticidad.addItems(["Critica","Alta","Media","Baja"]); self.combo_criticidad.setCurrentText("Media")
        self.inp_procedimiento = QTextEdit(); self.inp_procedimiento.setMaximumHeight(70)
        self.inp_procedimiento.setPlaceholderText("Procedimiento paso a paso...")

        f1.addRow("Codigo *:", self.inp_codigo)
        f1.addRow("Equipo *:", self.combo_equipo)
        f1.addRow("Descripcion:", self.inp_descripcion)
        f1.addRow("Tipo:", self.combo_tipo)
        f1.addRow("Frecuencia *:", self.inp_frecuencia)
        f1.addRow("Unidad frecuencia:", self.combo_unidad)
        f1.addRow("Criterio:", self.combo_criterio)
        f1.addRow("Duracion estimada:", self.inp_duracion)
        f1.addRow("Prioridad:", self.combo_prioridad)
        f1.addRow("Criticidad:", self.combo_criticidad)
        f1.addRow("Procedimiento:", self.inp_procedimiento)
        tabs.addTab(t1, "Datos Generales")
        lay.addWidget(tabs)

        # Botones
        btns = QHBoxLayout(); btns.addStretch()
        bc = QPushButton("Cancelar"); bc.clicked.connect(self.reject)
        bg = QPushButton("Guardar")
        bg.setStyleSheet(f"background-color:{COLOR_ACCENT_BLUE}; color:white; font-weight:600; border-radius:4px; border:none; padding:6px 20px;")
        bg.clicked.connect(self._guardar)
        btns.addWidget(bc); btns.addWidget(bg)
        lay.addLayout(btns)

    def _cargar_equipos(self):
        self.combo_equipo.clear()
        self.combo_equipo.addItem("-- Seleccione equipo --", None)
        for e in EquipoService.listar(solo_activos=True):
            self.combo_equipo.addItem(f"{e.codigo} - {e.nombre}", e.id)

    def _cargar(self):
        from app.core.database import get_session
        from app.models.plan import PlanMantenimiento
        session = get_session()
        try:
            p = session.query(PlanMantenimiento).get(self.plan_id)
            if not p: return
            self.inp_codigo.setText(p.codigo); self.inp_codigo.setReadOnly(True)
            idx = self.combo_equipo.findData(p.equipo_id)
            if idx >= 0: self.combo_equipo.setCurrentIndex(idx)
            self.inp_descripcion.setText(p.descripcion or "")
            self.combo_tipo.setCurrentText(p.tipo_mantenimiento)
            self.inp_frecuencia.setValue(p.frecuencia)
            self.combo_unidad.setCurrentText(p.unidad_frecuencia)
            self.combo_criterio.setCurrentText(p.criterio)
            self.inp_duracion.setValue(p.duracion_estimada or 1)
            self.combo_prioridad.setCurrentText(p.prioridad)
            self.combo_criticidad.setCurrentText(p.criticidad or "Media")
            self.inp_procedimiento.setPlainText(p.procedimiento or "")
        finally: session.close()

    def _guardar(self):
        datos = {
            "codigo":              self.inp_codigo.text().strip(),
            "equipo_id":           self.combo_equipo.currentData(),
            "descripcion":         self.inp_descripcion.text().strip(),
            "tipo_mantenimiento":  self.combo_tipo.currentText(),
            "frecuencia":          self.inp_frecuencia.value(),
            "unidad_frecuencia":   self.combo_unidad.currentText(),
            "criterio":            self.combo_criterio.currentText(),
            "duracion_estimada":   self.inp_duracion.value(),
            "prioridad":           self.combo_prioridad.currentText(),
            "criticidad":          self.combo_criticidad.currentText(),
            "procedimiento":       self.inp_procedimiento.toPlainText().strip(),
        }
        if self.plan_id:
            from app.core.database import get_session
            from app.models.plan import PlanMantenimiento
            session = get_session()
            try:
                p = session.query(PlanMantenimiento).get(self.plan_id)
                for k, v in datos.items():
                    if k not in ("codigo","equipo_id") and v:
                        setattr(p, k, v)
                session.commit()
                QMessageBox.information(self,"OK","Plan actualizado.")
                self.accept()
            except Exception as e:
                session.rollback()
                QMessageBox.critical(self,"Error",str(e))
            finally: session.close()
        else:
            ok, msg, _ = PlanService.crear(datos, [], [])
            if ok: QMessageBox.information(self,"OK",msg); self.accept()
            else: QMessageBox.critical(self,"Error",msg)
