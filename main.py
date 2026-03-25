"""
Software PMP - Versión 5.0
Programa de Mantenimiento Planificado
Punto de entrada principal.
"""
import sys
import os

# Asegurar que el directorio raíz esté en el path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon

from app.core.database import inicializar_base_datos
from app.core.config_manager import ConfigManager
from app.views.login.login_window import LoginWindow
from app.views.shared.styles import STYLESHEET_GLOBAL


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Software PMP")
    app.setApplicationVersion("5.0")
    app.setOrganizationName("PMP Industrial")
    app.setStyleSheet(STYLESHEET_GLOBAL)

    # Inicializar configuración
    config = ConfigManager()
    db_path = config.get("database", "path", fallback="pmp_data.db")

    # Inicializar base de datos
    inicializar_base_datos(db_path)

    # Mostrar login
    login = LoginWindow()
    login.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
