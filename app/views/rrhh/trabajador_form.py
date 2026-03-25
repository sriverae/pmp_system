"""Formulario de trabajador — stub."""
from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel, QPushButton, QFormLayout, QLineEdit, QComboBox, QSpinBox, QMessageBox
from PySide6.QtCore import Qt
from app.core.database import get_session
from app.models.trabajador import Trabajador
from app.core.session import session_usuario
from app.services.auditoria_service import AuditoriaService

class TrabajadorForm(QDialog):
    def __init__(self, trabajador_id=None, parent=None):
        super().__init__(parent)
        self.trabajador_id = trabajador_id
        self.setWindowTitle("Trabajador")
        self.setMinimumSize(480, 440)
        self.setModal(True)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(20,16,20,16)
        lay.setSpacing(10)
        form = QFormLayout()
        form.setSpacing(9)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        self.inp_codigo = QLineEdit()
        self.inp_nombres = QLineEdit()
        self.inp_apellidos = QLineEdit()
        self.inp_especialidad = QLineEdit()
        self.combo_turno = QComboBox()
        self.combo_turno.addItems(["Mañana","Tarde","Noche","Rotativo"])
        self.combo_estado = QComboBox()
        self.combo_estado.addItems(["Activo","Inactivo","Vacaciones","Permiso","Suspendido"])
        self.inp_horas = QSpinBox()
        self.inp_horas.setRange(1,24)
        self.inp_horas.setValue(8)
        form.addRow("Código *:", self.inp_codigo)
        form.addRow("Nombres *:", self.inp_nombres)
        form.addRow("Apellidos *:", self.inp_apellidos)
        form.addRow("Especialidad:", self.inp_especialidad)
        form.addRow("Turno:", self.combo_turno)
        form.addRow("Estado:", self.combo_estado)
        form.addRow("Horas/día:", self.inp_horas)
        lay.addLayout(form)
        btns = QHBoxLayout = __import__("PySide6.QtWidgets",fromlist=["QHBoxLayout"]).QHBoxLayout()
        btn_c = QPushButton("Cancelar"); btn_c.clicked.connect(self.reject)
        btn_g = QPushButton("Guardar"); btn_g.clicked.connect(self._guardar)
        btns.addStretch(); btns.addWidget(btn_c); btns.addWidget(btn_g)
        lay.addLayout(btns)
        if trabajador_id: self._cargar()

    def _cargar(self):
        session = get_session()
        try:
            t = session.query(Trabajador).get(self.trabajador_id)
            if t:
                self.inp_codigo.setText(t.codigo); self.inp_codigo.setReadOnly(True)
                self.inp_nombres.setText(t.nombres); self.inp_apellidos.setText(t.apellidos)
                self.inp_especialidad.setText(t.especialidad or "")
                self.combo_turno.setCurrentText(t.turno or "Mañana")
                self.combo_estado.setCurrentText(t.estado)
                self.inp_horas.setValue(t.horas_max_dia or 8)
        finally: session.close()

    def _guardar(self):
        if not self.inp_codigo.text().strip() or not self.inp_nombres.text().strip():
            QMessageBox.warning(self,"Requerido","Código y nombres son obligatorios."); return
        session = get_session()
        try:
            if self.trabajador_id:
                t = session.query(Trabajador).get(self.trabajador_id)
            else:
                t = Trabajador(codigo=self.inp_codigo.text().strip())
                session.add(t)
            t.nombres = self.inp_nombres.text().strip()
            t.apellidos = self.inp_apellidos.text().strip()
            t.especialidad = self.inp_especialidad.text().strip() or None
            t.turno = self.combo_turno.currentText()
            t.estado = self.combo_estado.currentText()
            t.horas_max_dia = self.inp_horas.value()
            session.commit()
            AuditoriaService.registrar("RRHH","Guardar trabajador",tabla="trabajadores")
            QMessageBox.information(self,"OK","Trabajador guardado.")
            self.accept()
        except Exception as e:
            session.rollback(); QMessageBox.critical(self,"Error",str(e))
        finally: session.close()
