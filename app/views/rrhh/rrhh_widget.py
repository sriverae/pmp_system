"""
Módulo RRHH — Gestión de personal de mantenimiento.
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFrame, QMessageBox, QComboBox, QDialog,
    QFormLayout, QLineEdit, QDateEdit, QTextEdit
)
from PySide6.QtCore import Qt, QDate

from app.views.shared.tabla_base import TablaBase
from app.core.database import get_session
from app.models.trabajador import Trabajador, AusenciaTrabajador
from app.services.auditoria_service import AuditoriaService
from app.core.session import session_usuario
from app.views.shared.styles import (
    COLOR_TEXT_PRIMARY, COLOR_TEXT_SECONDARY, COLOR_ACCENT_BLUE,
    COLOR_BORDER, COLOR_BG_PANEL, COLOR_DANGER, COLOR_WARNING
)


COLS_TRAB = [
    {"header": "Código",       "key": "codigo",       "width": 90},
    {"header": "Apellidos",    "key": "apellidos",    "width": 150},
    {"header": "Nombres",      "key": "nombres",      "width": 130},
    {"header": "Especialidad", "key": "especialidad", "width": 140},
    {"header": "Turno",        "key": "turno",        "width": 80},
    {"header": "Estado",       "key": "estado",       "width": 90},
    {"header": "Horas/día",    "key": "horas_dia",    "width": 70},
]


class RRHHWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._construir_ui()
        self.cargar_datos()

    def _construir_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(10)

        enc = QHBoxLayout()
        lbl = QLabel("[RRHH]  Gestión de Personal")
        lbl.setStyleSheet(
            f"font-size: 18px; font-weight: 700; color: {COLOR_TEXT_PRIMARY};")
        self.lbl_conteo = QLabel()
        self.lbl_conteo.setStyleSheet(
            f"color: {COLOR_TEXT_SECONDARY}; font-size: 12px;")
        enc.addWidget(lbl)
        enc.addWidget(self.lbl_conteo)
        enc.addStretch()
        layout.addLayout(enc)

        fil = QHBoxLayout()
        self.combo_estado = QComboBox()
        self.combo_estado.addItems(
            ["Todos", "Activo", "Inactivo", "Vacaciones",
             "Permiso", "Suspendido"])
        self.combo_estado.setFixedWidth(120)
        self.combo_estado.currentIndexChanged.connect(self.cargar_datos)

        self.combo_turno = QComboBox()
        self.combo_turno.addItems(
            ["Todos los turnos", "Mañana", "Tarde", "Noche", "Rotativo"])
        self.combo_turno.setFixedWidth(140)
        self.combo_turno.currentIndexChanged.connect(self.cargar_datos)

        fil.addWidget(QLabel("Estado:"))
        fil.addWidget(self.combo_estado)
        fil.addWidget(QLabel("Turno:"))
        fil.addWidget(self.combo_turno)
        fil.addStretch()
        layout.addLayout(fil)

        self.tabla = TablaBase(columnas=COLS_TRAB, columna_estado="estado")
        layout.addWidget(self.tabla)

        btn_frame = QFrame()
        btn_frame.setStyleSheet(
            f"background-color: {COLOR_BG_PANEL}; border-radius: 6px; "
            f"border: 1px solid {COLOR_BORDER}; padding: 6px;")
        bl = QHBoxLayout(btn_frame)
        bl.setSpacing(6)
        for texto, cb, est in [
            ("[+] Nuevo",          self._nuevo,          "normal"),
            ("[Edit] Editar",          self._editar,         "normal"),
            ("[Cal] Ausencias",      self._ausencias,      "normal"),
            ("[X] Inactivar",      self._inactivar,      "danger"),
            ("[OK] Activar",        self._activar,        "success"),
            ("[Exp] Exportar",       self._exportar,       "normal"),
        ]:
            b = QPushButton(texto)
            b.setFixedHeight(30)
            if est == "danger":
                b.setStyleSheet(
                    "background-color: #C62828; color: white; "
                    "border-radius: 4px; border: none; padding: 0 10px;")
            elif est == "success":
                b.setStyleSheet(
                    "background-color: #2E7D32; color: white; "
                    "border-radius: 4px; border: none; padding: 0 10px;")
            b.clicked.connect(cb)
            bl.addWidget(b)
        bl.addStretch()
        layout.addWidget(btn_frame)

    def cargar_datos(self):
        estado = self.combo_estado.currentText()
        turno = self.combo_turno.currentText()
        session = get_session()
        try:
            q = session.query(Trabajador)
            if estado != "Todos":
                q = q.filter_by(estado=estado)
            if turno != "Todos los turnos":
                q = q.filter_by(turno=turno)
            trabajadores = q.order_by(
                Trabajador.apellidos, Trabajador.nombres).all()

            datos, ids = [], []
            for t in trabajadores:
                datos.append({
                    "codigo": t.codigo,
                    "apellidos": t.apellidos,
                    "nombres": t.nombres,
                    "especialidad": t.especialidad or "-",
                    "turno": t.turno or "-",
                    "estado": t.estado,
                    "horas_dia": str(t.horas_max_dia or 8),
                })
                ids.append(t.id)
            self.tabla.cargar(datos, ids)
            self.lbl_conteo.setText(f"{len(trabajadores)} trabajador(es)")
        finally:
            session.close()

    def _nuevo(self):
        from app.views.rrhh.trabajador_form import TrabajadorForm
        dlg = TrabajadorForm(parent=self)
        if dlg.exec():
            self.cargar_datos()

    def _editar(self):
        tid = self.tabla.id_seleccionado()
        if not tid:
            QMessageBox.information(self, "Seleccionar",
                                     "Seleccione un trabajador.")
            return
        from app.views.rrhh.trabajador_form import TrabajadorForm
        dlg = TrabajadorForm(trabajador_id=tid, parent=self)
        if dlg.exec():
            self.cargar_datos()

    def _ausencias(self):
        tid = self.tabla.id_seleccionado()
        if not tid:
            QMessageBox.information(self, "Seleccionar",
                                     "Seleccione un trabajador.")
            return
        from app.views.rrhh.ausencias_dialog import AusenciasDialog
        dlg = AusenciasDialog(trabajador_id=tid, parent=self)
        dlg.exec()
        self.cargar_datos()

    def _inactivar(self):
        tid = self.tabla.id_seleccionado()
        if not tid:
            return
        session = get_session()
        try:
            t = session.query(Trabajador).get(tid)
            t.estado = "Inactivo"
            session.commit()
            AuditoriaService.registrar(
                "RRHH", "Inactivar trabajador",
                tabla="trabajadores", registro_id=tid)
        finally:
            session.close()
        self.cargar_datos()

    def _activar(self):
        tid = self.tabla.id_seleccionado()
        if not tid:
            return
        session = get_session()
        try:
            t = session.query(Trabajador).get(tid)
            t.estado = "Activo"
            session.commit()
        finally:
            session.close()
        self.cargar_datos()

    def _exportar(self):
        from PySide6.QtWidgets import QFileDialog
        ruta, _ = QFileDialog.getSaveFileName(
            self, "Exportar personal", "personal.xlsx",
            "Excel (*.xlsx)")
        if not ruta:
            return
        try:
            import pandas as pd
            session = get_session()
            trabajadores = session.query(Trabajador).all()
            session.close()
            datos = [{
                "Código": t.codigo,
                "Apellidos": t.apellidos,
                "Nombres": t.nombres,
                "Especialidad": t.especialidad,
                "Turno": t.turno,
                "Estado": t.estado,
                "Horas/día": t.horas_max_dia,
            } for t in trabajadores]
            pd.DataFrame(datos).to_excel(ruta, index=False)
            QMessageBox.information(self, "Exportado", ruta)
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))
