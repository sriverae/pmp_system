"""Contador equipo — stub."""
from PySide6.QtWidgets import QDialog, QVBoxLayout, QFormLayout, QLabel, QDoubleSpinBox, QLineEdit, QPushButton, QHBoxLayout, QMessageBox
from PySide6.QtCore import Qt
from app.services.equipo_service import EquipoService

class ContadorDialog(QDialog):
    def __init__(self, equipo_id, parent=None):
        super().__init__(parent)
        self.equipo_id = equipo_id
        eq = EquipoService.obtener(equipo_id)
        self.setWindowTitle(f"Lectura contador — {eq.nombre if eq else ''}")
        self.setFixedSize(380, 200); self.setModal(True)
        lay = QVBoxLayout(self); lay.setContentsMargins(20,16,20,16); lay.setSpacing(10)
        form = QFormLayout(); form.setSpacing(9); form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        lbl_act = QLabel(f"Lectura actual: {eq.lectura_actual:.1f} {eq.tipo_contador or ''}") if eq else QLabel("-")
        self.inp_nueva = QDoubleSpinBox(); self.inp_nueva.setRange(0,99999999); self.inp_nueva.setDecimals(1)
        if eq: self.inp_nueva.setValue(eq.lectura_actual)
        self.inp_obs = QLineEdit(); self.inp_obs.setPlaceholderText("Observaciones...")
        form.addRow("Lectura actual:", lbl_act)
        form.addRow("Nueva lectura *:", self.inp_nueva)
        form.addRow("Observaciones:", self.inp_obs)
        lay.addLayout(form)
        btns = QHBoxLayout()
        btn_c = QPushButton("Cancelar"); btn_c.clicked.connect(self.reject)
        btn_g = QPushButton("Registrar"); btn_g.clicked.connect(self._registrar)
        btns.addStretch(); btns.addWidget(btn_c); btns.addWidget(btn_g)
        lay.addLayout(btns)

    def _registrar(self):
        ok, msg = EquipoService.registrar_lectura_contador(self.equipo_id, self.inp_nueva.value(), self.inp_obs.text().strip())
        if ok: QMessageBox.information(self,"OK",msg); self.accept()
        else: QMessageBox.critical(self,"Error",msg)
