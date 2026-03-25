"""Widget adjuntos — stub."""
from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel, QPushButton, QFileDialog, QListWidget, QHBoxLayout, QMessageBox
import shutil, os
from app.core.database import get_session
from app.models.adjunto import Adjunto
from app.core.session import session_usuario

class AdjuntosDialog(QDialog):
    def __init__(self, tabla_origen, registro_id, parent=None):
        super().__init__(parent)
        self.tabla_origen = tabla_origen; self.registro_id = registro_id
        self.setWindowTitle("Adjuntos"); self.setMinimumSize(500, 360); self.setModal(True)
        lay = QVBoxLayout(self); lay.setContentsMargins(16,12,16,12); lay.setSpacing(8)
        lay.addWidget(QLabel(f"Archivos adjuntos — {tabla_origen} #{registro_id}"))
        self.lista = QListWidget(); lay.addWidget(self.lista)
        btns = QHBoxLayout()
        btn_add = QPushButton("[+] Adjuntar archivo"); btn_add.clicked.connect(self._adjuntar)
        btn_abrir = QPushButton("[Dir] Abrir"); btn_abrir.clicked.connect(self._abrir)
        btn_close = QPushButton("Cerrar"); btn_close.clicked.connect(self.accept)
        btns.addWidget(btn_add); btns.addWidget(btn_abrir); btns.addStretch(); btns.addWidget(btn_close)
        lay.addLayout(btns)
        self._cargar()

    def _cargar(self):
        self.lista.clear()
        session = get_session()
        try:
            adj = session.query(Adjunto).filter_by(tabla_origen=self.tabla_origen, registro_id=self.registro_id).all()
            for a in adj: self.lista.addItem(f"{a.nombre_original}  ({a.ruta})")
        finally: session.close()

    def _adjuntar(self):
        ruta, _ = QFileDialog.getOpenFileName(self,"Seleccionar archivo")
        if not ruta: return
        dest_dir = os.path.join("assets","adjuntos",self.tabla_origen,str(self.registro_id))
        os.makedirs(dest_dir, exist_ok=True)
        nombre = os.path.basename(ruta)
        destino = os.path.join(dest_dir, nombre)
        shutil.copy2(ruta, destino)
        session = get_session()
        try:
            session.add(Adjunto(tabla_origen=self.tabla_origen, registro_id=self.registro_id,
                nombre_original=nombre, ruta=destino,
                subido_por=session_usuario.usuario_id))
            session.commit()
        finally: session.close()
        self._cargar()

    def _abrir(self):
        item = self.lista.currentItem()
        if not item: return
        ruta = item.text().split("(")[-1].rstrip(")")
        import subprocess, sys
        try:
            if sys.platform=="win32": os.startfile(ruta)
            elif sys.platform=="darwin": subprocess.Popen(["open",ruta])
            else: subprocess.Popen(["xdg-open",ruta])
        except: QMessageBox.warning(self,"Error","No se pudo abrir el archivo.")
