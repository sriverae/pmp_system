"""
Ventana de Login — Software PMP v5.0
Valida usuario, contraseña, bloqueo temporal y registra auditoría.
"""
from PySide6.QtWidgets import (
    QDialog, QWidget, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLabel, QLineEdit, QPushButton, QMessageBox, QFrame,
    QApplication, QFileDialog
)
from PySide6.QtCore import Qt, QTimer, QSize
from PySide6.QtGui import QFont, QIcon, QPixmap, QColor

from app.services.auth_service import AuthService
from app.core.config_manager import ConfigManager
from app.core.database import inicializar_base_datos
from app.views.shared.styles import (
    COLOR_ACCENT_BLUE, COLOR_BG_DARK, COLOR_BG_MEDIUM,
    COLOR_BG_PANEL, COLOR_BORDER, COLOR_TEXT_PRIMARY,
    COLOR_TEXT_SECONDARY, COLOR_DANGER, COLOR_SUCCESS
)


class LoginWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Software PMP — Inicio de Sesión")
        self.setFixedSize(460, 560)
        self.setWindowFlags(Qt.WindowType.Window |
                            Qt.WindowType.WindowCloseButtonHint)
        self._timer_bloqueo = QTimer(self)
        self._timer_bloqueo.timeout.connect(self._actualizar_cuenta_regresiva)
        self._segundos_restantes = 0
        self._main_window = None
        self._construir_ui()
        self._centrar()

    def _centrar(self):
        screen = QApplication.primaryScreen().availableGeometry()
        self.move(
            (screen.width() - self.width()) // 2,
            (screen.height() - self.height()) // 2
        )

    def _construir_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(0)

        # -- Encabezado ----------------------------------------------------
        encabezado = QVBoxLayout()
        encabezado.setSpacing(6)

        icono = QLabel("[CFG]")
        icono.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icono.setStyleSheet(
            f"font-size: 48px; color: {COLOR_ACCENT_BLUE}; margin-bottom: 8px;")

        lbl_titulo = QLabel("Software PMP")
        lbl_titulo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_titulo.setStyleSheet(
            f"font-size: 24px; font-weight: 700; color: {COLOR_TEXT_PRIMARY}; "
            f"letter-spacing: 2px;")

        lbl_version = QLabel("Versión 5.0 — Programa de Mantenimiento Planificado")
        lbl_version.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_version.setStyleSheet(
            f"font-size: 11px; color: {COLOR_TEXT_SECONDARY}; letter-spacing: 0.5px;")

        separador = QFrame()
        separador.setFrameShape(QFrame.Shape.HLine)
        separador.setStyleSheet(
            f"border: none; border-top: 1px solid {COLOR_BORDER}; margin: 16px 0;")

        encabezado.addWidget(icono)
        encabezado.addWidget(lbl_titulo)
        encabezado.addWidget(lbl_version)
        encabezado.addWidget(separador)
        layout.addLayout(encabezado)

        # -- Formulario ----------------------------------------------------
        form_frame = QFrame()
        form_frame.setStyleSheet(
            f"background-color: {COLOR_BG_PANEL}; border-radius: 8px; "
            f"border: 1px solid {COLOR_BORDER};")
        form_layout = QVBoxLayout(form_frame)
        form_layout.setContentsMargins(24, 24, 24, 24)
        form_layout.setSpacing(16)

        # Usuario
        lbl_usuario = QLabel("Usuario")
        lbl_usuario.setStyleSheet(
            f"font-weight: 600; font-size: 12px; color: {COLOR_TEXT_SECONDARY}; "
            f"text-transform: uppercase; letter-spacing: 0.5px;")
        self.input_usuario = QLineEdit()
        self.input_usuario.setPlaceholderText("Ingrese su usuario")
        self.input_usuario.setMinimumHeight(38)
        self.input_usuario.returnPressed.connect(self._intentar_login)

        # Contraseña
        lbl_clave = QLabel("Contraseña")
        lbl_clave.setStyleSheet(lbl_usuario.styleSheet())
        self.input_clave = QLineEdit()
        self.input_clave.setPlaceholderText("Ingrese su contraseña")
        self.input_clave.setEchoMode(QLineEdit.EchoMode.Password)
        self.input_clave.setMinimumHeight(38)
        self.input_clave.returnPressed.connect(self._intentar_login)

        form_layout.addWidget(lbl_usuario)
        form_layout.addWidget(self.input_usuario)
        form_layout.addWidget(lbl_clave)
        form_layout.addWidget(self.input_clave)
        layout.addWidget(form_frame)

        layout.addSpacing(16)

        # -- Mensaje de estado ---------------------------------------------
        self.lbl_mensaje = QLabel("")
        self.lbl_mensaje.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_mensaje.setWordWrap(True)
        self.lbl_mensaje.setStyleSheet(
            "font-size: 12px; min-height: 36px; padding: 4px;")
        self.lbl_mensaje.hide()
        layout.addWidget(self.lbl_mensaje)

        layout.addSpacing(8)

        # -- Botones principales -------------------------------------------
        self.btn_ingresar = QPushButton("  Ingresar")
        self.btn_ingresar.setObjectName("btn_primary")
        self.btn_ingresar.setMinimumHeight(42)
        self.btn_ingresar.setStyleSheet(
            f"font-size: 14px; font-weight: 600; "
            f"background-color: {COLOR_ACCENT_BLUE}; color: white; "
            f"border-radius: 6px; border: none;")
        self.btn_ingresar.clicked.connect(self._intentar_login)

        btn_cancelar = QPushButton("Cancelar")
        btn_cancelar.setMinimumHeight(42)
        btn_cancelar.setStyleSheet(
            f"font-size: 13px; background-color: {COLOR_BG_MEDIUM}; "
            f"color: {COLOR_TEXT_SECONDARY}; border-radius: 6px; "
            f"border: 1px solid {COLOR_BORDER};")
        btn_cancelar.clicked.connect(QApplication.quit)

        btn_row = QHBoxLayout()
        btn_row.addWidget(btn_cancelar)
        btn_row.addWidget(self.btn_ingresar)
        layout.addLayout(btn_row)

        layout.addSpacing(12)

        # -- Botón configurar BD -------------------------------------------
        btn_config_bd = QPushButton("Configurar base de datos...")
        btn_config_bd.setFlat(True)
        btn_config_bd.setStyleSheet(
            f"color: {COLOR_TEXT_SECONDARY}; font-size: 11px; "
            f"background: transparent; border: none; text-decoration: underline;")
        btn_config_bd.clicked.connect(self._configurar_bd)
        layout.addWidget(btn_config_bd, alignment=Qt.AlignmentFlag.AlignCenter)

        layout.addStretch()

        # -- Footer --------------------------------------------------------
        lbl_footer = QLabel("© 2024 Software PMP — Todos los derechos reservados")
        lbl_footer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_footer.setStyleSheet(
            f"font-size: 10px; color: {COLOR_BORDER}; margin-top: 8px;")
        layout.addWidget(lbl_footer)

        # Foco inicial
        self.input_usuario.setFocus()

    def _intentar_login(self):
        """Intenta autenticar. Maneja bloqueo temporal."""
        if self._segundos_restantes > 0:
            return

        username = self.input_usuario.text().strip()
        password = self.input_clave.text()

        resultado = AuthService.login(username, password)

        if resultado.exitoso:
            self._mostrar_mensaje(resultado.mensaje, "success")
            self.btn_ingresar.setEnabled(False)
            # Pequeño delay para mostrar mensaje antes de abrir ventana principal
            QTimer.singleShot(600, self._abrir_ventana_principal)
        else:
            self._mostrar_mensaje(resultado.mensaje, "error")
            self.input_clave.clear()
            self.input_clave.setFocus()

            if resultado.bloqueado and resultado.segundos_restantes > 0:
                self._segundos_restantes = resultado.segundos_restantes
                self.btn_ingresar.setEnabled(False)
                self._timer_bloqueo.start(1000)

    def _actualizar_cuenta_regresiva(self):
        self._segundos_restantes -= 1
        if self._segundos_restantes <= 0:
            self._timer_bloqueo.stop()
            self.btn_ingresar.setEnabled(True)
            self._mostrar_mensaje("Puede intentar nuevamente.", "info")
        else:
            m = self._segundos_restantes // 60
            s = self._segundos_restantes % 60
            self._mostrar_mensaje(
                f"Cuenta bloqueada. Espere {m:02d}:{s:02d}", "error")

    def _mostrar_mensaje(self, texto: str, tipo: str):
        colores = {
            "success": (COLOR_SUCCESS, "#1B5E20"),
            "error":   (COLOR_DANGER, "#B71C1C"),
            "info":    (COLOR_ACCENT_BLUE, "#0D47A1"),
        }
        color_texto, color_fondo = colores.get(tipo, ("#FFFFFF", "#263238"))
        self.lbl_mensaje.setText(texto)
        self.lbl_mensaje.setStyleSheet(
            f"font-size: 12px; color: {color_texto}; "
            f"background-color: {color_fondo}40; "
            f"border: 1px solid {color_texto}60; border-radius: 4px; "
            f"padding: 6px 12px; min-height: 30px;"
        )
        self.lbl_mensaje.show()

    def _abrir_ventana_principal(self):
        from app.views.main_window import MainWindow
        self._main_window = MainWindow()
        self._main_window.show()
        self.close()

    def _configurar_bd(self):
        """Permite seleccionar o crear una base de datos SQLite."""
        ruta, _ = QFileDialog.getSaveFileName(
            self,
            "Seleccionar o crear base de datos",
            "pmp_data.db",
            "Base de datos SQLite (*.db)"
        )
        if ruta:
            config = ConfigManager()
            config.set("database", "path", ruta)
            inicializar_base_datos(ruta)
            self._mostrar_mensaje(
                f"Base de datos configurada: {ruta}", "success")
