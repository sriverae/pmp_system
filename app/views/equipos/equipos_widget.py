"""
Módulo Equipos — Gestión completa de equipos industriales.
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFrame, QMessageBox, QComboBox,
    QSplitter, QGroupBox, QFormLayout, QTextEdit
)
from PySide6.QtCore import Qt

from app.views.shared.tabla_base import TablaBase
from app.services.equipo_service import EquipoService
from app.core.session import session_usuario
from app.views.shared.styles import (
    COLOR_TEXT_PRIMARY, COLOR_TEXT_SECONDARY, COLOR_ACCENT_BLUE,
    COLOR_BORDER, COLOR_BG_PANEL, COLOR_SUCCESS, COLOR_DANGER,
    COLOR_WARNING
)


COLUMNAS_EQUIPOS = [
    {"header": "Código",    "key": "codigo",       "width": 90},
    {"header": "Nombre",    "key": "nombre",       "width": 200},
    {"header": "Área",      "key": "area",         "width": 120},
    {"header": "Ubicación", "key": "ubicacion",    "width": 140},
    {"header": "Criticidad","key": "criticidad",   "width": 90},
    {"header": "Estado",    "key": "estado",       "width": 100},
    {"header": "Lect. Act.","key": "lectura_actual","width": 90},
    {"header": "Prox. Interv.","key": "proxima",   "width": 110},
]


class EquiposWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._construir_ui()
        self.cargar_datos()

    def _construir_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(10)

        # -- Encabezado ----------------------------------------------------
        enc = QHBoxLayout()
        lbl = QLabel("[CFG]  Gestión de Equipos")
        lbl.setStyleSheet(
            f"font-size: 18px; font-weight: 700; color: {COLOR_TEXT_PRIMARY};")
        self.lbl_conteo = QLabel("0 equipos")
        self.lbl_conteo.setStyleSheet(
            f"color: {COLOR_TEXT_SECONDARY}; font-size: 12px;")
        enc.addWidget(lbl)
        enc.addWidget(self.lbl_conteo)
        enc.addStretch()
        layout.addLayout(enc)

        # -- Barra de filtros ----------------------------------------------
        filtros_row = QHBoxLayout()
        filtros_row.setSpacing(8)

        self.combo_estado = QComboBox()
        self.combo_estado.addItems(
            ["Todos los estados", "Activo", "Inactivo",
             "Dado de baja", "En mantenimiento"])
        self.combo_estado.setFixedWidth(160)
        self.combo_estado.currentIndexChanged.connect(self.cargar_datos)

        self.combo_criticidad = QComboBox()
        self.combo_criticidad.addItems(
            ["Toda criticidad", "Crítica", "Alta", "Media", "Baja"])
        self.combo_criticidad.setFixedWidth(140)
        self.combo_criticidad.currentIndexChanged.connect(self.cargar_datos)

        filtros_row.addWidget(QLabel("Estado:"))
        filtros_row.addWidget(self.combo_estado)
        filtros_row.addWidget(QLabel("Criticidad:"))
        filtros_row.addWidget(self.combo_criticidad)
        filtros_row.addStretch()
        layout.addLayout(filtros_row)

        # -- Splitter: tabla + detalle -------------------------------------
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Tabla
        frame_tabla = QFrame()
        lay_tabla = QVBoxLayout(frame_tabla)
        lay_tabla.setContentsMargins(0, 0, 0, 0)

        self.tabla = TablaBase(
            columnas=COLUMNAS_EQUIPOS,
            columna_estado="estado"
        )
        self.tabla.fila_seleccionada.connect(self._on_seleccion)
        self.tabla.doble_click.connect(self._ver_detalle)
        lay_tabla.addWidget(self.tabla)

        # Botones de acción
        btn_frame = QFrame()
        btn_frame.setStyleSheet(
            f"background-color: {COLOR_BG_PANEL}; border-radius: 6px; "
            f"border: 1px solid {COLOR_BORDER}; padding: 6px;")
        btn_lay = QHBoxLayout(btn_frame)
        btn_lay.setSpacing(6)

        self.btn_nuevo = self._btn("[+] Nuevo", self._nuevo)
        self.btn_editar = self._btn("[Edit] Editar", self._editar)
        self.btn_detalle = self._btn("[Aud] Detalle", self._ver_detalle)
        self.btn_historial = self._btn("[Hist] Historial", self._ver_historial)
        self.btn_contadores = self._btn("[Cnt] Contadores", self._contadores)
        self.btn_adjuntos = self._btn("[Adj] Adjuntos", self._adjuntos)

        separador = QFrame()
        separador.setFrameShape(QFrame.Shape.VLine)
        separador.setStyleSheet(f"border: none; border-left: 1px solid {COLOR_BORDER};")

        self.btn_baja = self._btn("[X] Dar de baja", self._dar_baja,
                                   estilo="danger")
        self.btn_reactivar = self._btn("[OK] Reactivar", self._reactivar,
                                        estilo="success")
        self.btn_importar = self._btn("[Imp] Importar", self._importar)
        self.btn_exportar = self._btn("[Exp] Exportar", self._exportar)

        for b in [self.btn_nuevo, self.btn_editar, self.btn_detalle,
                   self.btn_historial, self.btn_contadores, self.btn_adjuntos,
                   separador,
                   self.btn_baja, self.btn_reactivar, self.btn_importar,
                   self.btn_exportar]:
            btn_lay.addWidget(b)
        btn_lay.addStretch()
        lay_tabla.addWidget(btn_frame)

        # Panel de detalle lateral
        self._panel_detalle = self._crear_panel_detalle()

        splitter.addWidget(frame_tabla)
        splitter.addWidget(self._panel_detalle)
        splitter.setSizes([900, 320])
        layout.addWidget(splitter)

    def _btn(self, texto, callback, estilo="normal") -> QPushButton:
        b = QPushButton(texto)
        b.setFixedHeight(30)
        b.setObjectName(f"btn_{estilo}" if estilo != "normal" else "")
        if estilo == "danger":
            b.setStyleSheet(
                f"background-color: #C62828; color: white; border-radius: 4px; "
                f"border: none; padding: 0 10px; font-size: 12px;")
        elif estilo == "success":
            b.setStyleSheet(
                f"background-color: #2E7D32; color: white; border-radius: 4px; "
                f"border: none; padding: 0 10px; font-size: 12px;")
        b.clicked.connect(callback)
        return b

    def _crear_panel_detalle(self) -> QFrame:
        frame = QFrame()
        frame.setMinimumWidth(280)
        frame.setStyleSheet(
            f"background-color: {COLOR_BG_PANEL}; border-radius: 8px; "
            f"border: 1px solid {COLOR_BORDER};")
        lay = QVBoxLayout(frame)
        lay.setContentsMargins(16, 14, 16, 14)
        lay.setSpacing(8)

        lbl = QLabel("Detalle del Equipo")
        lbl.setStyleSheet(
            f"font-weight: 700; font-size: 13px; color: {COLOR_TEXT_PRIMARY}; "
            f"border: none;")
        lay.addWidget(lbl)

        self.detalle_form = QFormLayout()
        self.detalle_form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        self.detalle_form.setSpacing(6)

        self._lbl_det = {}
        campos = ["Código", "Nombre", "Marca/Modelo", "Serie", "Área",
                  "Ubicación", "Criticidad", "Estado", "Tipo contador",
                  "Lectura actual", "Costo reposición"]
        for c in campos:
            lbl_val = QLabel("-")
            lbl_val.setStyleSheet(
                f"color: {COLOR_TEXT_PRIMARY}; font-size: 12px; border: none;")
            lbl_val.setWordWrap(True)
            lbl_key = QLabel(f"{c}:")
            lbl_key.setStyleSheet(
                f"color: {COLOR_TEXT_SECONDARY}; font-size: 11px; border: none;")
            self.detalle_form.addRow(lbl_key, lbl_val)
            self._lbl_det[c] = lbl_val

        lay.addLayout(self.detalle_form)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet(f"border: none; border-top: 1px solid {COLOR_BORDER};")
        lay.addWidget(sep)

        lbl_obs = QLabel("Observaciones:")
        lbl_obs.setStyleSheet(
            f"color: {COLOR_TEXT_SECONDARY}; font-size: 11px; border: none;")
        lay.addWidget(lbl_obs)

        self.txt_obs_detalle = QTextEdit()
        self.txt_obs_detalle.setReadOnly(True)
        self.txt_obs_detalle.setMaximumHeight(80)
        self.txt_obs_detalle.setStyleSheet(
            f"background-color: transparent; border: none; "
            f"color: {COLOR_TEXT_PRIMARY}; font-size: 12px;")
        lay.addWidget(self.txt_obs_detalle)
        lay.addStretch()

        return frame

    # ---------------------------------------------------------------------
    # DATOS
    # ---------------------------------------------------------------------

    def cargar_datos(self):
        estado_sel = self.combo_estado.currentText()
        crit_sel = self.combo_criticidad.currentText()

        filtro_estado = (None if estado_sel == "Todos los estados"
                         else estado_sel)
        filtro_crit = (None if crit_sel == "Toda criticidad" else crit_sel)

        equipos = EquipoService.listar(
            solo_activos=False,
            criticidad=filtro_crit
        )
        if filtro_estado:
            equipos = [e for e in equipos if e.estado == filtro_estado]

        datos = []
        ids = []
        for e in equipos:
            datos.append({
                "codigo": e.codigo,
                "nombre": e.nombre,
                "area": e.area or "-",
                "ubicacion": e.ubicacion or "-",
                "criticidad": e.criticidad,
                "estado": e.estado,
                "lectura_actual": f"{e.lectura_actual:.0f} {e.tipo_contador or ''}".strip(),
                "proxima": "-",  # Se puede calcular desde planes
            })
            ids.append(e.id)

        self.tabla.cargar(datos, ids)
        self.lbl_conteo.setText(f"{len(equipos)} equipo(s)")

    def _on_seleccion(self, equipo_id: int):
        equipo = EquipoService.obtener(equipo_id)
        if not equipo:
            return
        d = self._lbl_det
        d["Código"].setText(equipo.codigo)
        d["Nombre"].setText(equipo.nombre)
        d["Marca/Modelo"].setText(
            f"{equipo.marca or '-'} / {equipo.modelo or '-'}")
        d["Serie"].setText(equipo.serie or "-")
        d["Área"].setText(equipo.area or "-")
        d["Ubicación"].setText(equipo.ubicacion or "-")
        d["Criticidad"].setText(equipo.criticidad)

        # Color criticidad
        colores_crit = {
            "Crítica": COLOR_DANGER, "Alta": COLOR_WARNING,
            "Media": COLOR_ACCENT_BLUE, "Baja": COLOR_SUCCESS
        }
        d["Criticidad"].setStyleSheet(
            f"color: {colores_crit.get(equipo.criticidad, COLOR_TEXT_PRIMARY)}; "
            f"font-weight: 600; font-size: 12px; border: none;")

        d["Estado"].setText(equipo.estado)
        d["Tipo contador"].setText(equipo.tipo_contador or "-")
        d["Lectura actual"].setText(
            f"{equipo.lectura_actual:.1f} {equipo.tipo_contador or ''}")
        d["Costo reposición"].setText(f"{equipo.costo_reposicion:,.2f}")
        self.txt_obs_detalle.setPlainText(equipo.observaciones or "")

    # ---------------------------------------------------------------------
    # ACCIONES
    # ---------------------------------------------------------------------

    def _nuevo(self):
        from app.views.equipos.equipo_form import EquipoForm
        dlg = EquipoForm(parent=self)
        if dlg.exec():
            self.cargar_datos()

    def _editar(self):
        eid = self.tabla.id_seleccionado()
        if not eid:
            QMessageBox.information(self, "Seleccionar",
                                     "Seleccione un equipo para editar.")
            return
        from app.views.equipos.equipo_form import EquipoForm
        dlg = EquipoForm(equipo_id=eid, parent=self)
        if dlg.exec():
            self.cargar_datos()

    def _ver_detalle(self, equipo_id: int = None):
        eid = equipo_id or self.tabla.id_seleccionado()
        if not eid:
            return
        equipo = EquipoService.obtener(eid)
        if equipo:
            QMessageBox.information(
                self, f"Equipo — {equipo.codigo}",
                f"Código: {equipo.codigo}\n"
                f"Nombre: {equipo.nombre}\n"
                f"Marca/Modelo: {equipo.marca} / {equipo.modelo}\n"
                f"Serie: {equipo.serie}\n"
                f"Criticidad: {equipo.criticidad}\n"
                f"Estado: {equipo.estado}\n"
                f"Lectura actual: {equipo.lectura_actual} {equipo.tipo_contador or ''}\n"
                f"Costo reposición: {equipo.costo_reposicion:,.2f}"
            )

    def _ver_historial(self):
        eid = self.tabla.id_seleccionado()
        if not eid:
            QMessageBox.information(self, "Seleccionar",
                                     "Seleccione un equipo.")
            return
        from app.views.equipos.historial_equipo_dialog import HistorialEquipoDialog
        dlg = HistorialEquipoDialog(equipo_id=eid, parent=self)
        dlg.exec()

    def _contadores(self):
        eid = self.tabla.id_seleccionado()
        if not eid:
            QMessageBox.information(self, "Seleccionar",
                                     "Seleccione un equipo.")
            return
        from app.views.equipos.contador_dialog import ContadorDialog
        dlg = ContadorDialog(equipo_id=eid, parent=self)
        if dlg.exec():
            self.cargar_datos()

    def _adjuntos(self):
        eid = self.tabla.id_seleccionado()
        if not eid:
            return
        from app.views.shared.adjuntos_widget import AdjuntosDialog
        dlg = AdjuntosDialog("equipos", eid, parent=self)
        dlg.exec()

    def _dar_baja(self):
        if not session_usuario.puede("editar"):
            QMessageBox.warning(self, "Acceso denegado",
                                 "No tiene permiso para dar de baja equipos.")
            return
        eid = self.tabla.id_seleccionado()
        if not eid:
            QMessageBox.information(self, "Seleccionar", "Seleccione un equipo.")
            return
        equipo = EquipoService.obtener(eid)
        resp = QMessageBox.question(
            self, "Dar de baja",
            f"¿Desea dar de baja el equipo '{equipo.nombre}'?\n"
            "Esta acción cambiará su estado a 'Dado de baja'.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if resp == QMessageBox.StandardButton.Yes:
            ok, msg = EquipoService.dar_de_baja(eid, motivo="Baja manual")
            if ok:
                QMessageBox.information(self, "Éxito", msg)
                self.cargar_datos()
            else:
                QMessageBox.critical(self, "Error", msg)

    def _reactivar(self):
        eid = self.tabla.id_seleccionado()
        if not eid:
            return
        ok, msg = EquipoService.reactivar(eid)
        if ok:
            QMessageBox.information(self, "Éxito", msg)
            self.cargar_datos()
        else:
            QMessageBox.critical(self, "Error", msg)

    def _importar(self):
        from PySide6.QtWidgets import QFileDialog
        ruta, _ = QFileDialog.getOpenFileName(
            self, "Importar equipos desde Excel", "",
            "Excel (*.xlsx *.xls)")
        if ruta:
            self._importar_excel(ruta)

    def _importar_excel(self, ruta: str):
        """Importación masiva de equipos desde Excel."""
        try:
            import pandas as pd
            df = pd.read_excel(ruta)
            # Columnas requeridas
            reqs = ["codigo", "nombre", "criticidad"]
            faltantes = [c for c in reqs if c not in df.columns]
            if faltantes:
                QMessageBox.critical(
                    self, "Error",
                    f"Faltan columnas obligatorias: {', '.join(faltantes)}")
                return

            errores = []
            creados = 0
            for i, row in df.iterrows():
                datos = {c: str(row[c]) if pd.notna(row.get(c)) else ""
                         for c in df.columns}
                ok, msg, _ = EquipoService.crear(datos)
                if ok:
                    creados += 1
                else:
                    errores.append(f"Fila {i + 2}: {msg}")

            resumen = f"Importados: {creados} equipos."
            if errores:
                resumen += f"\nErrores ({len(errores)}):\n" + "\n".join(errores[:5])
            QMessageBox.information(self, "Importación completada", resumen)
            self.cargar_datos()
        except Exception as e:
            QMessageBox.critical(self, "Error al importar", str(e))

    def _exportar(self):
        from PySide6.QtWidgets import QFileDialog
        ruta, _ = QFileDialog.getSaveFileName(
            self, "Exportar equipos", "equipos.xlsx",
            "Excel (*.xlsx)")
        if ruta:
            try:
                import pandas as pd
                equipos = EquipoService.listar()
                datos = [{
                    "Código": e.codigo, "Nombre": e.nombre,
                    "Área": e.area, "Ubicación": e.ubicacion,
                    "Criticidad": e.criticidad, "Estado": e.estado,
                    "Marca": e.marca, "Modelo": e.modelo, "Serie": e.serie,
                    "Tipo contador": e.tipo_contador,
                    "Lectura actual": e.lectura_actual,
                    "Costo reposición": e.costo_reposicion,
                } for e in equipos]
                pd.DataFrame(datos).to_excel(ruta, index=False)
                QMessageBox.information(
                    self, "Exportar", f"Exportado: {ruta}")
            except Exception as e:
                QMessageBox.critical(self, "Error", str(e))
