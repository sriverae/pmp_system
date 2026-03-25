"""Módulo Backup — Respaldo y restauración de la base de datos."""
import shutil
import os
from datetime import datetime
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFrame, QMessageBox, QFileDialog,
    QTableWidget, QTableWidgetItem, QHeaderView
)
from PySide6.QtCore import Qt

from app.core.config_manager import ConfigManager
from app.core.session import session_usuario
from app.views.shared.styles import (
    COLOR_TEXT_PRIMARY, COLOR_TEXT_SECONDARY, COLOR_ACCENT_BLUE,
    COLOR_SUCCESS, COLOR_DANGER, COLOR_BORDER, COLOR_BG_PANEL
)


class BackupWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._config = ConfigManager()
        self._construir_ui()
        self._cargar_historial()

    def _construir_ui(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(16, 12, 16, 12)
        lay.setSpacing(16)

        lbl = QLabel("[Bkp]  Backup y Restauración")
        lbl.setStyleSheet(
            f"font-size: 18px; font-weight: 700; color: {COLOR_TEXT_PRIMARY};")
        lay.addWidget(lbl)

        # Acciones principales
        btn_row = QHBoxLayout()
        for texto, cb, color in [
            ("[Bkp]  Crear Backup Ahora",     self.crear_backup,    COLOR_ACCENT_BLUE),
            ("[Dir]  Restaurar desde Backup", self.restaurar_backup, COLOR_DANGER),
            ("[Dir]  Abrir carpeta backups",  self._abrir_carpeta,  "#37474F"),
        ]:
            btn = QPushButton(texto)
            btn.setFixedHeight(40)
            btn.setStyleSheet(
                f"background-color: {color}; color: white; font-weight: 600; "
                f"border-radius: 6px; border: none; padding: 0 20px; font-size: 13px;")
            btn.clicked.connect(cb)
            btn_row.addWidget(btn)
        btn_row.addStretch()
        lay.addLayout(btn_row)

        # Descripción
        lbl_info = QLabel(
            "[i]  Los backups son copias de la base de datos SQLite. "
            "Se guardan en la carpeta 'backups/' con marca de tiempo. "
            "La restauración reemplaza la base actual — haga un backup previo.")
        lbl_info.setStyleSheet(
            f"color: {COLOR_TEXT_SECONDARY}; font-size: 11px; "
            f"background-color: {COLOR_BG_PANEL}; padding: 8px 12px; "
            f"border-radius: 4px;")
        lbl_info.setWordWrap(True)
        lay.addWidget(lbl_info)

        # Historial de backups
        lbl_hist = QLabel("Historial de backups:")
        lbl_hist.setStyleSheet(
            f"font-weight: 600; color: {COLOR_TEXT_PRIMARY}; font-size: 13px;")
        lay.addWidget(lbl_hist)

        self.tabla_hist = QTableWidget(0, 4)
        self.tabla_hist.setHorizontalHeaderLabels(
            ["Archivo", "Fecha/Hora", "Tamaño", "Estado"])
        self.tabla_hist.horizontalHeader().setStretchLastSection(True)
        self.tabla_hist.setEditTriggers(
            QTableWidget.EditTrigger.NoEditTriggers)
        self.tabla_hist.verticalHeader().setVisible(False)
        self.tabla_hist.setAlternatingRowColors(True)
        lay.addWidget(self.tabla_hist)

        self.lbl_status = QLabel("")
        self.lbl_status.setStyleSheet(
            f"font-size: 12px; font-weight: 600;")
        lay.addWidget(self.lbl_status)

    def crear_backup(self):
        """Crea copia del archivo SQLite con marca de tiempo."""
        db_path = self._config.get("database", "path", "pmp_data.db")
        if not os.path.exists(db_path):
            QMessageBox.warning(
                self, "Base no encontrada",
                f"No se encontró la base de datos en:\n{db_path}")
            return

        backup_dir = self._config.get("backup", "directory", "backups")
        os.makedirs(backup_dir, exist_ok=True)

        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        nombre = f"pmp_backup_{ts}.db"
        destino = os.path.join(backup_dir, nombre)

        try:
            shutil.copy2(db_path, destino)
            tam = os.path.getsize(destino)
            self.lbl_status.setText(
                f"[OK] Backup creado: {nombre} ({tam // 1024} KB)")
            self.lbl_status.setStyleSheet(
                f"color: {COLOR_SUCCESS}; font-weight: 600;")

            # Registrar en BD
            from app.core.database import get_session
            from app.models.base import BackupRegistrado
            session = get_session()
            try:
                session.add(BackupRegistrado(
                    nombre_archivo=nombre,
                    ruta=destino,
                    tamanio_bytes=tam,
                    creado_por=session_usuario.usuario_id
                ))
                session.commit()
            finally:
                session.close()

            self._cargar_historial()
            QMessageBox.information(
                self, "Backup creado",
                f"Backup guardado exitosamente:\n{destino}")
        except Exception as e:
            QMessageBox.critical(self, "Error al crear backup", str(e))

    def restaurar_backup(self):
        """Restaura la BD desde un archivo de backup."""
        if not session_usuario.is_admin():
            QMessageBox.warning(
                self, "Acceso denegado",
                "Solo el Administrador puede restaurar backups.")
            return

        ruta, _ = QFileDialog.getOpenFileName(
            self, "Seleccionar backup a restaurar",
            self._config.get("backup", "directory", "backups"),
            "SQLite (*.db)")
        if not ruta:
            return

        resp = QMessageBox.critical(
            self,
            "[!] ADVERTENCIA — Restaurar Backup",
            f"¿Desea REEMPLAZAR la base de datos actual con:\n\n"
            f"{ruta}\n\n"
            "ESTA ACCIÓN NO SE PUEDE DESHACER.\n"
            "Se recomienda crear un backup previo.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if resp != QMessageBox.StandardButton.Yes:
            return

        db_path = self._config.get("database", "path", "pmp_data.db")
        try:
            # Crear backup de seguridad antes de restaurar
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_dir = self._config.get("backup", "directory", "backups")
            os.makedirs(backup_dir, exist_ok=True)
            shutil.copy2(db_path,
                         os.path.join(backup_dir,
                                      f"pre_restauracion_{ts}.db"))

            shutil.copy2(ruta, db_path)
            QMessageBox.information(
                self, "Restauración exitosa",
                "Base de datos restaurada. "
                "Reinicie la aplicación para aplicar los cambios.")
        except Exception as e:
            QMessageBox.critical(
                self, "Error al restaurar", str(e))

    def _abrir_carpeta(self):
        import subprocess
        import sys
        backup_dir = self._config.get("backup", "directory", "backups")
        os.makedirs(backup_dir, exist_ok=True)
        ruta_abs = os.path.abspath(backup_dir)
        if sys.platform == "win32":
            os.startfile(ruta_abs)
        elif sys.platform == "darwin":
            subprocess.Popen(["open", ruta_abs])
        else:
            subprocess.Popen(["xdg-open", ruta_abs])

    def _cargar_historial(self):
        """Lista archivos .db en la carpeta de backups."""
        backup_dir = self._config.get("backup", "directory", "backups")
        self.tabla_hist.setRowCount(0)
        if not os.path.exists(backup_dir):
            return
        archivos = sorted(
            [f for f in os.listdir(backup_dir) if f.endswith(".db")],
            reverse=True
        )
        for archivo in archivos[:20]:
            ruta = os.path.join(backup_dir, archivo)
            tam = os.path.getsize(ruta)
            mtime = datetime.fromtimestamp(
                os.path.getmtime(ruta)).strftime("%d/%m/%Y %H:%M")

            r = self.tabla_hist.rowCount()
            self.tabla_hist.insertRow(r)
            for c, v in enumerate([
                archivo, mtime,
                f"{tam // 1024} KB", "OK"
            ]):
                self.tabla_hist.setItem(r, c, QTableWidgetItem(v))
