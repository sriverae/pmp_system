"""Diálogo de ausencias de trabajador — stub."""
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QLabel, QPushButton, QHBoxLayout,
    QTableWidget, QTableWidgetItem, QDateEdit, QComboBox, QMessageBox)
from PySide6.QtCore import QDate
from app.core.database import get_session
from app.models.trabajador import AusenciaTrabajador, Trabajador
from datetime import datetime

class AusenciasDialog(QDialog):
    def __init__(self, trabajador_id, parent=None):
        super().__init__(parent)
        self.trabajador_id = trabajador_id
        session = get_session()
        try:
            t = session.query(Trabajador).get(trabajador_id)
            nombre = t.nombre_completo if t else f"ID {trabajador_id}"
        finally: session.close()
        self.setWindowTitle(f"Ausencias — {nombre}")
        self.setMinimumSize(600, 400)
        self.setModal(True)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(16,12,16,12); lay.setSpacing(8)
        lay.addWidget(QLabel("Registrar ausencia:"))
        row = QHBoxLayout()
        self.fecha_ini = QDateEdit(); self.fecha_ini.setDate(QDate.currentDate()); self.fecha_ini.setCalendarPopup(True)
        self.fecha_fin = QDateEdit(); self.fecha_fin.setDate(QDate.currentDate()); self.fecha_fin.setCalendarPopup(True)
        self.combo_tipo = QComboBox(); self.combo_tipo.addItems(["Vacaciones","Permiso","Enfermedad","Suspensión","Otro"])
        btn_add = QPushButton("Agregar"); btn_add.clicked.connect(self._agregar)
        row.addWidget(QLabel("Desde:")); row.addWidget(self.fecha_ini)
        row.addWidget(QLabel("Hasta:")); row.addWidget(self.fecha_fin)
        row.addWidget(QLabel("Tipo:")); row.addWidget(self.combo_tipo)
        row.addWidget(btn_add)
        lay.addLayout(row)
        self.tabla = QTableWidget(0,3)
        self.tabla.setHorizontalHeaderLabels(["Desde","Hasta","Tipo"])
        self.tabla.verticalHeader().setVisible(False)
        lay.addWidget(self.tabla)
        btn_close = QPushButton("Cerrar"); btn_close.clicked.connect(self.accept)
        lay.addWidget(btn_close)
        self._cargar()

    def _cargar(self):
        session = get_session()
        try:
            ausencias = session.query(AusenciaTrabajador).filter_by(trabajador_id=self.trabajador_id).all()
            self.tabla.setRowCount(0)
            for a in ausencias:
                r = self.tabla.rowCount(); self.tabla.insertRow(r)
                self.tabla.setItem(r,0,QTableWidgetItem(a.fecha_inicio.strftime("%d/%m/%Y")))
                self.tabla.setItem(r,1,QTableWidgetItem(a.fecha_fin.strftime("%d/%m/%Y")))
                self.tabla.setItem(r,2,QTableWidgetItem(a.tipo_ausencia))
        finally: session.close()

    def _agregar(self):
        fi = self.fecha_ini.date(); ff = self.fecha_fin.date()
        d_ini = datetime(fi.year(),fi.month(),fi.day())
        d_fin = datetime(ff.year(),ff.month(),ff.day())
        if d_fin < d_ini: QMessageBox.warning(self,"Error","La fecha fin no puede ser anterior a la fecha inicio."); return
        session = get_session()
        try:
            session.add(AusenciaTrabajador(trabajador_id=self.trabajador_id, fecha_inicio=d_ini, fecha_fin=d_fin, tipo_ausencia=self.combo_tipo.currentText()))
            session.commit()
            self._cargar()
        except Exception as e: session.rollback(); QMessageBox.critical(self,"Error",str(e))
        finally: session.close()
