"""Módulo Configuración — parámetros generales del sistema."""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLabel, QPushButton, QLineEdit, QSpinBox,
    QGroupBox, QMessageBox, QTabWidget
)
from PySide6.QtCore import Qt

from app.core.config_manager import ConfigManager
from app.core.database import get_session
from app.models.base import ConfiguracionSistema
from app.views.shared.styles import (
    COLOR_TEXT_PRIMARY, COLOR_TEXT_SECONDARY, COLOR_ACCENT_BLUE
)


class ConfigWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._config = ConfigManager()
        self._construir_ui()
        self._cargar_valores()

    def _construir_ui(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(24, 16, 24, 16)
        lay.setSpacing(16)

        lbl = QLabel("[CFG]  Configuración del Sistema")
        lbl.setStyleSheet(
            f"font-size: 18px; font-weight: 700; color: {COLOR_TEXT_PRIMARY};")
        lay.addWidget(lbl)

        tabs = QTabWidget()

        # -- Tab 1: Empresa ---------------------------------------------
        tab1 = QWidget()
        form1 = QFormLayout(tab1)
        form1.setSpacing(10)
        form1.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        form1.setContentsMargins(16, 16, 16, 16)

        self.inp_empresa = QLineEdit()
        self.inp_ruc = QLineEdit()
        self.inp_moneda = QLineEdit()
        self.inp_moneda.setPlaceholderText("S/. / USD / EUR")
        self.inp_dir_backup = QLineEdit()
        self.inp_dir_backup.setPlaceholderText("Ruta de carpeta para backups...")

        form1.addRow("Nombre de la empresa:", self.inp_empresa)
        form1.addRow("RUC / ID fiscal:", self.inp_ruc)
        form1.addRow("Moneda:", self.inp_moneda)
        form1.addRow("Directorio de backups:", self.inp_dir_backup)
        tabs.addTab(tab1, "Empresa")

        # -- Tab 2: OTs -------------------------------------------------
        tab2 = QWidget()
        form2 = QFormLayout(tab2)
        form2.setSpacing(10)
        form2.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        form2.setContentsMargins(16, 16, 16, 16)

        self.inp_prefijo_ot = QLineEdit()
        self.inp_prefijo_ot.setPlaceholderText("Ej: OT")
        self.inp_prefijo_ot.setMaximumWidth(100)

        self.inp_digitos_ot = QSpinBox()
        self.inp_digitos_ot.setRange(4, 10)
        self.inp_digitos_ot.setValue(6)
        self.inp_digitos_ot.setMaximumWidth(80)

        self.inp_max_horas_dia = QSpinBox()
        self.inp_max_horas_dia.setRange(1, 24)
        self.inp_max_horas_dia.setValue(10)
        self.inp_max_horas_dia.setSuffix(" horas")
        self.inp_max_horas_dia.setMaximumWidth(120)

        form2.addRow("Prefijo número OT:", self.inp_prefijo_ot)
        form2.addRow("Dígitos número OT:", self.inp_digitos_ot)
        form2.addRow("Máximo horas/día técnico:", self.inp_max_horas_dia)
        tabs.addTab(tab2, "Órdenes de Trabajo")

        # -- Tab 3: Seguridad -------------------------------------------
        tab3 = QWidget()
        form3 = QFormLayout(tab3)
        form3.setSpacing(10)
        form3.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        form3.setContentsMargins(16, 16, 16, 16)

        self.inp_max_intentos = QSpinBox()
        self.inp_max_intentos.setRange(3, 10)
        self.inp_max_intentos.setValue(5)
        self.inp_max_intentos.setMaximumWidth(80)

        self.inp_bloqueo_min = QSpinBox()
        self.inp_bloqueo_min.setRange(1, 60)
        self.inp_bloqueo_min.setValue(15)
        self.inp_bloqueo_min.setSuffix(" min")
        self.inp_bloqueo_min.setMaximumWidth(100)

        form3.addRow("Máx. intentos de login:", self.inp_max_intentos)
        form3.addRow("Tiempo de bloqueo:", self.inp_bloqueo_min)
        tabs.addTab(tab3, "Seguridad")

        lay.addWidget(tabs)

        # Botones
        btns = QHBoxLayout()
        btns.addStretch()
        btn_cancel = QPushButton("Descartar cambios")
        btn_cancel.clicked.connect(self._cargar_valores)
        btn_save = QPushButton("  Guardar configuración  ")
        btn_save.setStyleSheet(
            f"background-color: {COLOR_ACCENT_BLUE}; color: white; "
            f"font-weight: 600; border-radius: 4px; border: none;")
        btn_save.setFixedHeight(34)
        btn_save.clicked.connect(self._guardar)
        btns.addWidget(btn_cancel)
        btns.addWidget(btn_save)
        lay.addLayout(btns)
        lay.addStretch()

    def _cargar_valores(self):
        session = get_session()
        try:
            def get_cfg(clave, defecto=""):
                c = session.query(ConfiguracionSistema).filter_by(
                    clave=clave).first()
                return c.valor if c else defecto

            self.inp_empresa.setText(get_cfg("empresa_nombre", "Mi Empresa"))
            self.inp_ruc.setText(get_cfg("empresa_ruc", ""))
            self.inp_moneda.setText(get_cfg("moneda", "S/."))
            self.inp_dir_backup.setText(
                self._config.get("backup", "directory", "backups"))
            self.inp_prefijo_ot.setText(get_cfg("ot_prefijo", "OT"))
            self.inp_digitos_ot.setValue(
                int(get_cfg("ot_digitos", "6")))
            self.inp_max_horas_dia.setValue(
                int(get_cfg("max_horas_tecnico_dia", "10")))
            self.inp_max_intentos.setValue(
                int(get_cfg("max_intentos_login", "5")))
            self.inp_bloqueo_min.setValue(
                int(get_cfg("bloqueo_minutos", "15")))
        finally:
            session.close()

    def _guardar(self):
        session = get_session()
        try:
            def set_cfg(clave, valor):
                c = session.query(ConfiguracionSistema).filter_by(
                    clave=clave).first()
                if c:
                    c.valor = valor
                else:
                    session.add(ConfiguracionSistema(
                        clave=clave, valor=valor))

            set_cfg("empresa_nombre", self.inp_empresa.text().strip())
            set_cfg("empresa_ruc", self.inp_ruc.text().strip())
            set_cfg("moneda", self.inp_moneda.text().strip() or "S/.")
            set_cfg("ot_prefijo", self.inp_prefijo_ot.text().strip() or "OT")
            set_cfg("ot_digitos", str(self.inp_digitos_ot.value()))
            set_cfg("max_horas_tecnico_dia",
                    str(self.inp_max_horas_dia.value()))
            set_cfg("max_intentos_login", str(self.inp_max_intentos.value()))
            set_cfg("bloqueo_minutos", str(self.inp_bloqueo_min.value()))

            session.commit()

            self._config.set("backup", "directory",
                             self.inp_dir_backup.text().strip() or "backups")
            QMessageBox.information(
                self, "Configuración",
                "Configuración guardada exitosamente.")
        except Exception as e:
            session.rollback()
            QMessageBox.critical(self, "Error", str(e))
        finally:
            session.close()
