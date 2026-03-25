"""
Ventana Principal — Software PMP v5.0
Contiene: menú superior, toolbar de accesos rápidos,
panel central dinámico y barra de estado.
"""
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QStackedWidget, QToolBar,
    QStatusBar, QLabel, QSizePolicy, QMessageBox, QVBoxLayout,
    QFileDialog, QApplication, QInputDialog
)
from PySide6.QtCore import Qt, QTimer, QSize
from PySide6.QtGui import QAction, QIcon, QFont

from app.core.session import session_usuario
from app.services.auth_service import AuthService
from app.views.shared.styles import (
    COLOR_BG_DARK, COLOR_TEXT_SECONDARY, COLOR_ACCENT_BLUE,
    COLOR_SUCCESS, COLOR_DANGER, COLOR_WARNING
)
from datetime import datetime


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(
            "Software PMP — Versión 5.0  |  Programa de Mantenimiento Planificado")
        self.resize(1400, 860)
        self.setMinimumSize(1100, 700)

        self._panel_central = QStackedWidget()
        self.setCentralWidget(self._panel_central)
        self._widgets_cache = {}

        self._construir_menu()
        self._construir_toolbar()
        self._construir_barra_estado()
        self._iniciar_timer_reloj()

        # Mostrar dashboard al inicio
        self._mostrar_modulo("dashboard")

    # ---------------------------------------------------------------------
    # MENÚ SUPERIOR
    # ---------------------------------------------------------------------

    def _construir_menu(self):
        barra = self.menuBar()

        # -- Archivo -------------------------------------------------------
        m_archivo = barra.addMenu("Archivo")
        self._agregar_accion(m_archivo, "Nuevo proyecto...",
                              self._nuevo_proyecto, "Ctrl+N")
        self._agregar_accion(m_archivo, "Abrir base de datos...",
                              self._abrir_base)
        m_archivo.addSeparator()
        self._agregar_accion(m_archivo, "Guardar respaldo",
                              self._guardar_respaldo, "Ctrl+B")
        self._agregar_accion(m_archivo, "Restaurar respaldo...",
                              self._restaurar_respaldo)
        m_archivo.addSeparator()
        self._agregar_accion(m_archivo, "Importar desde Excel...",
                              self._importar_excel)
        self._agregar_accion(m_archivo, "Cargar datos demo",
                              self._cargar_datos_demo)
        self._agregar_accion(m_archivo, "Exportar datos...",
                              self._exportar_datos)
        m_archivo.addSeparator()
        self._agregar_accion(m_archivo, "Configuración general",
                              lambda: self._mostrar_modulo("configuracion"))
        m_archivo.addSeparator()
        self._agregar_accion(m_archivo, "Cerrar sesión",
                              self._cerrar_sesion, "Ctrl+L")
        self._agregar_accion(m_archivo, "Salir",
                              self._salir, "Ctrl+Q")

        # -- PMP -----------------------------------------------------------
        m_pmp = barra.addMenu("PMP")
        self._agregar_accion(m_pmp, "Dashboard",
                              lambda: self._mostrar_modulo("dashboard"))
        m_pmp.addSeparator()
        self._agregar_accion(m_pmp, "Planes de mantenimiento",
                              lambda: self._mostrar_modulo("planes"))
        self._agregar_accion(m_pmp, "Órdenes de trabajo",
                              lambda: self._mostrar_modulo("ordenes"))
        self._agregar_accion(m_pmp, "Calendario",
                              lambda: self._mostrar_modulo("calendario"))
        m_pmp.addSeparator()
        self._agregar_accion(m_pmp, "Historial",
                              lambda: self._mostrar_modulo("historial"))
        self._agregar_accion(m_pmp, "Costos",
                              lambda: self._mostrar_modulo("costos"))
        m_pmp.addSeparator()
        self._agregar_accion(m_pmp, "KPIs e Indicadores",
                              lambda: self._mostrar_modulo("kpis"))
        self._agregar_accion(m_pmp, "Análisis RAM",
                              lambda: self._mostrar_modulo("ram"))
        self._agregar_accion(m_pmp, "Reportes",
                              lambda: self._mostrar_modulo("reportes"))
        m_pmp.addSeparator()
        self._agregar_accion(m_pmp, "Auditoría",
                              lambda: self._mostrar_modulo("auditoria"))
        self._agregar_accion(m_pmp, "Backup / Restauración",
                              lambda: self._mostrar_modulo("backup"))

        # -- Equipos -------------------------------------------------------
        m_equipos = barra.addMenu("Equipos")
        self._agregar_accion(m_equipos, "Gestión de equipos",
                              lambda: self._mostrar_modulo("equipos"))

        # -- Materiales ----------------------------------------------------
        m_mats = barra.addMenu("Materiales")
        self._agregar_accion(m_mats, "Gestión de materiales",
                              lambda: self._mostrar_modulo("materiales"))
        self._agregar_accion(m_mats, "Alertas de stock",
                              lambda: self._mostrar_modulo("materiales"))

        # -- RRHH ----------------------------------------------------------
        m_rrhh = barra.addMenu("RRHH")
        self._agregar_accion(m_rrhh, "Gestión de personal",
                              lambda: self._mostrar_modulo("rrhh"))

    def _agregar_accion(self, menu, texto, callback,
                         shortcut: str = None) -> QAction:
        accion = QAction(texto, self)
        if shortcut:
            accion.setShortcut(shortcut)
        accion.triggered.connect(callback)
        menu.addAction(accion)
        return accion

    # ---------------------------------------------------------------------
    # TOOLBAR
    # ---------------------------------------------------------------------

    def _construir_toolbar(self):
        toolbar = QToolBar("Accesos rápidos")
        toolbar.setMovable(False)
        toolbar.setIconSize(QSize(18, 18))
        toolbar.setToolButtonStyle(
            Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.addToolBar(toolbar)

        botones = [
            ("[Nuevo] Nueva OT",      lambda: self._nueva_ot_rapida()),
            ("[Plan] Planes",         lambda: self._mostrar_modulo("planes")),
            ("[Eq] Equipos",          lambda: self._mostrar_modulo("equipos")),
            ("[Mat] Materiales",     lambda: self._mostrar_modulo("materiales")),
            ("[RRHH] RRHH",           lambda: self._mostrar_modulo("rrhh")),
            ("[Cal] Calendario",     lambda: self._mostrar_modulo("calendario")),
            ("[KPI] KPIs",           lambda: self._mostrar_modulo("kpis")),
            ("[Rep] Reportes",       lambda: self._mostrar_modulo("reportes")),
            ("[CFG] Configuración",  lambda: self._mostrar_modulo("configuracion")),
        ]
        for texto, cb in botones:
            btn = QAction(texto, self)
            btn.triggered.connect(cb)
            toolbar.addAction(btn)
            if texto in ("[Plan] Planes", "[Cal] Calendario", "[CFG] Configuración"):
                toolbar.addSeparator()

    # ---------------------------------------------------------------------
    # BARRA DE ESTADO
    # ---------------------------------------------------------------------

    def _construir_barra_estado(self):
        status = QStatusBar()
        self.setStatusBar(status)

        # Usuario logueado
        self.lbl_status_usuario = QLabel(
            f"  [User] {session_usuario.nombre_completo}  |  "
            f"Rol: {session_usuario.rol}  ")
        self.lbl_status_usuario.setStyleSheet(
            f"color: {COLOR_ACCENT_BLUE}; font-size: 12px;")

        # Separador
        sep = QLabel("  |  ")
        sep.setStyleSheet(f"color: {COLOR_TEXT_SECONDARY};")

        # Reloj
        self.lbl_reloj = QLabel()
        self.lbl_reloj.setStyleSheet(
            f"color: {COLOR_TEXT_SECONDARY}; font-size: 12px; padding-right: 8px;")

        status.addPermanentWidget(self.lbl_status_usuario)
        status.addPermanentWidget(sep)
        status.addPermanentWidget(self.lbl_reloj)

    def _iniciar_timer_reloj(self):
        self._timer_reloj = QTimer(self)
        self._timer_reloj.timeout.connect(self._actualizar_reloj)
        self._timer_reloj.start(1000)
        self._actualizar_reloj()

    def _actualizar_reloj(self):
        try:
            ahora = datetime.now().strftime("  %d/%m/%Y   %H:%M:%S")
            self.lbl_reloj.setText(ahora)
        except Exception:
            pass

    # ---------------------------------------------------------------------
    # NAVEGACIÓN DE MÓDULOS
    # ---------------------------------------------------------------------

    def _mostrar_modulo(self, nombre: str):
        """
        Carga (o recupera del caché) el widget del módulo y lo muestra
        en el panel central.
        """
        if nombre not in self._widgets_cache:
            widget = self._crear_widget_modulo(nombre)
            if widget is None:
                return
            self._panel_central.addWidget(widget)
            self._widgets_cache[nombre] = widget

        self._panel_central.setCurrentWidget(self._widgets_cache[nombre])
        self.statusBar().showMessage(
            f"  Módulo: {nombre.upper()}", 3000)

    def _crear_widget_modulo(self, nombre: str) -> QWidget:
        """Instancia el widget correspondiente al nombre del módulo."""
        try:
            if nombre == "dashboard":
                from app.views.dashboard.dashboard_widget import DashboardWidget
                w = DashboardWidget()
                # Conectar señales del dashboard
                w.ir_a_ots.connect(lambda: self._mostrar_modulo("ordenes"))
                w.ir_a_planes.connect(lambda: self._mostrar_modulo("planes"))
                w.ir_a_equipos.connect(lambda: self._mostrar_modulo("equipos"))
                w.ir_a_costos.connect(lambda: self._mostrar_modulo("costos"))
                return w

            elif nombre == "equipos":
                from app.views.equipos.equipos_widget import EquiposWidget
                return EquiposWidget()

            elif nombre == "materiales":
                from app.views.materiales.materiales_widget import MaterialesWidget
                return MaterialesWidget()

            elif nombre == "rrhh":
                from app.views.rrhh.rrhh_widget import RRHHWidget
                return RRHHWidget()

            elif nombre == "planes":
                from app.views.planes.planes_widget import PlanesWidget
                return PlanesWidget()

            elif nombre == "ordenes":
                from app.views.ordenes.ordenes_widget import OrdenesWidget
                return OrdenesWidget()

            elif nombre == "calendario":
                from app.views.calendario.calendario_widget import CalendarioWidget
                return CalendarioWidget()

            elif nombre == "costos":
                from app.views.costos.costos_widget import CostosWidget
                return CostosWidget()

            elif nombre == "kpis":
                from app.views.kpis.kpis_widget import KpisWidget
                return KpisWidget()

            elif nombre == "ram":
                from app.views.ram.ram_widget import RamWidget
                return RamWidget()

            elif nombre == "reportes":
                from app.views.reportes.reportes_widget import ReportesWidget
                return ReportesWidget()

            elif nombre == "auditoria":
                from app.views.auditoria.auditoria_widget import AuditoriaWidget
                return AuditoriaWidget()

            elif nombre == "configuracion":
                from app.views.configuracion.config_widget import ConfigWidget
                return ConfigWidget()

            elif nombre == "backup":
                from app.views.backup.backup_widget import BackupWidget
                return BackupWidget()

            elif nombre == "historial":
                from app.views.ordenes.ordenes_widget import OrdenesWidget
                # El historial comparte módulo de OTs con filtro especial
                return OrdenesWidget(modo_historial=True)

            else:
                # Placeholder para módulos no implementados aún
                return self._placeholder(nombre)

        except ImportError as e:
            print(f"[MainWindow] Error importando módulo '{nombre}': {e}")
            return self._placeholder(nombre)

    def _placeholder(self, nombre: str) -> QWidget:
        """Widget temporal para módulos en desarrollo."""
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl = QLabel(f"Módulo: {nombre.upper()}\n\n(En construcción)")
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl.setStyleSheet(
            f"font-size: 20px; color: {COLOR_TEXT_SECONDARY};")
        lay.addWidget(lbl)
        return w

    # ---------------------------------------------------------------------
    # ACCIONES ARCHIVO
    # ---------------------------------------------------------------------

    def _nueva_ot_rapida(self):
        """Navega a Órdenes y abre el formulario de nueva OT."""
        self._mostrar_modulo("ordenes")
        widget = self._widgets_cache.get("ordenes")
        if widget and hasattr(widget, "abrir_nueva_ot"):
            widget.abrir_nueva_ot()

    def _nuevo_proyecto(self):
        from app.views.configuracion.config_widget import ConfigWidget
        self._mostrar_modulo("configuracion")

    def _abrir_base(self):
        ruta, _ = QFileDialog.getOpenFileName(
            self, "Abrir base de datos", "",
            "SQLite (*.db *.sqlite)")
        if ruta:
            from app.core.database import inicializar_base_datos
            from app.core.config_manager import ConfigManager
            try:
                inicializar_base_datos(ruta)
                ConfigManager().set("database", "path", ruta)
                # Limpiar caché de widgets
                self._widgets_cache.clear()
                while self._panel_central.count():
                    self._panel_central.removeWidget(
                        self._panel_central.widget(0))
                self._mostrar_modulo("dashboard")
                QMessageBox.information(
                    self, "Base de datos",
                    f"Base cargada exitosamente:\n{ruta}")
            except Exception as e:
                QMessageBox.critical(
                    self, "Error", f"No se pudo abrir la base:\n{str(e)}")

    def _guardar_respaldo(self):
        self._mostrar_modulo("backup")
        widget = self._widgets_cache.get("backup")
        if widget and hasattr(widget, "crear_backup"):
            widget.crear_backup()

    def _restaurar_respaldo(self):
        if not session_usuario.is_admin():
            QMessageBox.warning(
                self, "Acceso denegado",
                "Solo el Administrador puede restaurar respaldos.")
            return
        self._mostrar_modulo("backup")
        widget = self._widgets_cache.get("backup")
        if widget and hasattr(widget, "restaurar_backup"):
            widget.restaurar_backup()

    def _importar_excel(self):
        from app.services.bulk_import_service import BulkImportService

        modulos = [
            ("Equipos", "equipos"),
            ("RRHH", "rrhh"),
            ("Materiales", "materiales"),
            ("Planes", "planes"),
            ("Órdenes de trabajo", "ots"),
        ]
        etiqueta, ok = QInputDialog.getItem(
            self,
            "Importación masiva",
            "Seleccione el módulo a importar:",
            [m[0] for m in modulos],
            0,
            False
        )
        if not ok:
            return
        modulo = dict(modulos)[etiqueta]

        accion, ok = QInputDialog.getItem(
            self,
            "Importación masiva",
            "Acción:",
            ["Importar desde Excel", "Descargar plantilla"],
            0,
            False
        )
        if not ok:
            return

        if accion == "Descargar plantilla":
            ruta, _ = QFileDialog.getSaveFileName(
                self, "Guardar plantilla", f"plantilla_{modulo}.xlsx", "Excel (*.xlsx)")
            if not ruta:
                return
            ok_t, msg = BulkImportService.exportar_plantilla(modulo, ruta)
            (QMessageBox.information if ok_t else QMessageBox.critical)(
                self, "Plantilla", msg
            )
            return

        ruta, _ = QFileDialog.getOpenFileName(
            self, "Seleccionar archivo Excel", "", "Excel (*.xlsx *.xls)")
        if not ruta:
            return
        ok_i, resultado = BulkImportService.importar_excel(modulo, ruta)
        resumen = (
            f"Insertados: {resultado.insertados}\n"
            f"Actualizados: {resultado.actualizados}\n"
            f"Omitidos: {resultado.omitidos}\n"
            f"Errores: {resultado.errores}"
        )
        if resultado.detalle_errores:
            resumen += "\n\nDetalle (primeros 8):\n" + "\n".join(resultado.detalle_errores[:8])
        (QMessageBox.information if ok_i else QMessageBox.warning)(
            self, "Importación masiva", resumen
        )

    def _exportar_datos(self):
        self._mostrar_modulo("reportes")

    def _cargar_datos_demo(self):
        resp = QMessageBox.question(
            self,
            "Datos demo",
            "Se cargarán registros demo de Equipos, RRHH, Materiales, Planes y OTs.\n\n¿Continuar?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if resp != QMessageBox.StandardButton.Yes:
            return
        from app.services.demo_data_service import DemoDataService
        ok, msg = DemoDataService.cargar_datos_demo()
        (QMessageBox.information if ok else QMessageBox.critical)(self, "Datos demo", msg)
        if ok and "ordenes" in self._widgets_cache:
            try:
                self._widgets_cache["ordenes"].cargar_datos()
            except Exception:
                pass

    def _cerrar_sesion(self):
        resp = QMessageBox.question(
            self, "Cerrar sesión",
            "¿Desea cerrar la sesión actual?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if resp == QMessageBox.StandardButton.Yes:
            AuthService.logout()
            from app.views.login.login_window import LoginWindow
            self._login = LoginWindow()
            self._login.show()
            self.close()

    def _salir(self):
        resp = QMessageBox.question(
            self, "Salir",
            "¿Desea cerrar la aplicación?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if resp == QMessageBox.StandardButton.Yes:
            AuthService.logout()
            QApplication.quit()

    def closeEvent(self, event):
        AuthService.logout()
        event.accept()
