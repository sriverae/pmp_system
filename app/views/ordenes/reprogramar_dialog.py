"""Diálogo reprogramar OT — stub."""
from PySide6.QtWidgets import QDialog, QVBoxLayout, QFormLayout, QLabel, QDateEdit, QLineEdit, QPushButton, QHBoxLayout, QMessageBox
from PySide6.QtCore import QDate, Qt
from app.services.ot_service import OTService

class ReprogramarDialog(QDialog):
    def __init__(self, ot_id, parent=None):
        super().__init__(parent)
        self.ot_id = ot_id
        self.setWindowTitle("Reprogramar OT")
        self.setFixedSize(400, 220)
        self.setModal(True)
        lay = QVBoxLayout(self); lay.setContentsMargins(20,16,20,16); lay.setSpacing(10)
        form = QFormLayout(); form.setSpacing(9); form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        self.fecha = QDateEdit(); self.fecha.setDate(QDate.currentDate().addDays(7)); self.fecha.setCalendarPopup(True)
        self.inp_motivo = QLineEdit(); self.inp_motivo.setPlaceholderText("Motivo de reprogramación (obligatorio)")
        form.addRow("Nueva fecha *:", self.fecha)
        form.addRow("Motivo *:", self.inp_motivo)
        lay.addLayout(form)
        btns = QHBoxLayout()
        btn_c = QPushButton("Cancelar"); btn_c.clicked.connect(self.reject)
        btn_g = QPushButton("Reprogramar"); btn_g.clicked.connect(self._reprogramar)
        btns.addStretch(); btns.addWidget(btn_c); btns.addWidget(btn_g)
        lay.addLayout(btns)

    def _reprogramar(self):
        if not self.inp_motivo.text().strip():
            QMessageBox.warning(self,"Requerido","El motivo es obligatorio."); return
        fd = self.fecha.date()
        from datetime import datetime
        nueva = datetime(fd.year(),fd.month(),fd.day())
        ok, msg = OTService.reprogramar_ot(self.ot_id, nueva, self.inp_motivo.text().strip())
        if ok: QMessageBox.information(self,"OK",msg); self.accept()
        else: QMessageBox.critical(self,"Error",msg)
