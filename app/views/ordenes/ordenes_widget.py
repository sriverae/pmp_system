"""
Módulo Órdenes de Trabajo — Gestión completa de OTs.
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFrame, QMessageBox, QComboBox,
    QDateEdit, QInputDialog
)
from PySide6.QtCore import Qt, QDate
from PySide6.QtGui import QColor

from app.views.shared.tabla_base import TablaBase
from app.services.ot_service import OTService
from app.core.session import session_usuario
from app.views.shared.styles import (
    COLOR_TEXT_PRIMARY, COLOR_TEXT_SECONDARY, COLOR_ACCENT_BLUE,
    COLOR_BORDER, COLOR_BG_PANEL, COLOR_SUCCESS, COLOR_DANGER, COLOR_WARNING
)
from datetime import datetime


COLUMNAS_OTS = [
    {"header": "Número",       "key": "numero",         "width": 130},
    {"header": "Tipo",         "key": "tipo_ot",        "width": 100},
    {"header": "Equipo",       "key": "equipo",         "width": 180},
    {"header": "Fecha Prog.",  "key": "fecha_prog",     "width": 100},
    {"header": "Hora Ini",     "key": "hora_ini",       "width": 70},
    {"header": "Hora Fin",     "key": "hora_fin",       "width": 70},
    {"header": "Prioridad",    "key": "prioridad",      "width": 80},
    {"header": "Responsable",  "key": "responsable",    "width": 160},
    {"header": "Estado",       "key": "estado",         "width": 100},
    {"header": "Costo Total",  "key": "costo_total",    "width": 100},
]


class OrdenesWidget(QWidget):
    def __init__(self, modo_historial: bool = False, parent=None):
        super().__init__(parent)
        self.modo_historial = modo_historial
        self._construir_ui()
        self.cargar_datos()

    def _construir_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(10)

        # Título
        titulo = "[Hist] Historial de OTs" if self.modo_historial else "[OT] Órdenes de Trabajo"
        lbl = QLabel(titulo)
        lbl.setStyleSheet(
            f"font-size: 18px; font-weight: 700; color: {COLOR_TEXT_PRIMARY};")
        layout.addWidget(lbl)

        # -- Barra de filtros ----------------------------------------------
        filtros = QHBoxLayout()
        filtros.setSpacing(8)

        self.combo_estado = QComboBox()
        self.combo_estado.addItems(
            ["Todos", "Borrador", "Programada", "Liberada",
             "En proceso", "Cerrada", "Anulada"])
        self.combo_estado.setFixedWidth(120)
        self.combo_estado.currentIndexChanged.connect(self.cargar_datos)

        self.combo_tipo = QComboBox()
        self.combo_tipo.addItems(
            ["Todos los tipos", "Preventivo", "Correctivo",
             "Inspección", "Predictivo", "Emergencia", "Mejora"])
        self.combo_tipo.setFixedWidth(140)
        self.combo_tipo.currentIndexChanged.connect(self.cargar_datos)

        self.combo_prioridad = QComboBox()
        self.combo_prioridad.addItems(
            ["Toda prioridad", "Urgente", "Alta", "Normal", "Baja"])
        self.combo_prioridad.setFixedWidth(130)
        self.combo_prioridad.currentIndexChanged.connect(self.cargar_datos)

        lbl_desde = QLabel("Desde:")
        lbl_desde.setStyleSheet(
            f"color: {COLOR_TEXT_SECONDARY}; font-size: 12px;")
        self.fecha_desde = QDateEdit()
        self.fecha_desde.setDate(QDate.currentDate().addDays(-30))
        self.fecha_desde.setCalendarPopup(True)
        self.fecha_desde.setFixedWidth(110)
        self.fecha_desde.dateChanged.connect(self.cargar_datos)

        lbl_hasta = QLabel("Hasta:")
        lbl_hasta.setStyleSheet(lbl_desde.styleSheet())
        self.fecha_hasta = QDateEdit()
        self.fecha_hasta.setDate(QDate.currentDate().addDays(60))
        self.fecha_hasta.setCalendarPopup(True)
        self.fecha_hasta.setFixedWidth(110)
        self.fecha_hasta.dateChanged.connect(self.cargar_datos)

        self.lbl_conteo = QLabel("0 OTs")
        self.lbl_conteo.setStyleSheet(
            f"color: {COLOR_TEXT_SECONDARY}; font-size: 12px;")

        filtros.addWidget(QLabel("Estado:"))
        filtros.addWidget(self.combo_estado)
        filtros.addWidget(QLabel("Tipo:"))
        filtros.addWidget(self.combo_tipo)
        filtros.addWidget(QLabel("Prioridad:"))
        filtros.addWidget(self.combo_prioridad)
        filtros.addWidget(lbl_desde)
        filtros.addWidget(self.fecha_desde)
        filtros.addWidget(lbl_hasta)
        filtros.addWidget(self.fecha_hasta)
        filtros.addStretch()
        filtros.addWidget(self.lbl_conteo)
        layout.addLayout(filtros)

        # -- Tabla ---------------------------------------------------------
        self.tabla = TablaBase(
            columnas=COLUMNAS_OTS,
            columna_estado="estado"
        )
        self.tabla.fila_seleccionada.connect(self._on_seleccion)
        self.tabla.doble_click.connect(self._ver_detalle)
        layout.addWidget(self.tabla)

        # -- Barra de botones ----------------------------------------------
        btn_frame = QFrame()
        btn_frame.setStyleSheet(
            f"background-color: {COLOR_BG_PANEL}; border-radius: 6px; "
            f"border: 1px solid {COLOR_BORDER}; padding: 6px;")
        btn_lay = QHBoxLayout(btn_frame)
        btn_lay.setSpacing(6)

        botones_izq = [
            ("[+] Nueva OT",     self.abrir_nueva_ot,   "primary"),
            ("[Edit] Editar",        self._editar,          "normal"),
            ("[Aud] Ver detalle",  self._ver_detalle_btn, "normal"),
        ]
        botones_estado = [
            ("[OK] Liberar",       self._liberar,  "success"),
            ("[Ini] Iniciar",        self._iniciar,  "normal"),
            ("[Act] Reprogramar",   self._reprogramar, "normal"),
            ("[Cerr] Cerrar OT",    self._cerrar,   "success"),
            ("[X] Anular",        self._anular,   "danger"),
        ]
        botones_der = [
            ("[Adj] Adjuntos",  self._adjuntos, "normal"),
            ("[Hist] Historial", self._historial_ot, "normal"),
            ("[Rep] Imprimir",  self._imprimir, "normal"),
            ("[Exp] Exportar",  self._exportar, "normal"),
        ]

        for texto, cb, est in botones_izq:
            btn_lay.addWidget(self._btn(texto, cb, est))

        sep1 = self._separador()
        btn_lay.addWidget(sep1)

        for texto, cb, est in botones_estado:
            btn_lay.addWidget(self._btn(texto, cb, est))

        sep2 = self._separador()
        btn_lay.addWidget(sep2)

        for texto, cb, est in botones_der:
            btn_lay.addWidget(self._btn(texto, cb, est))

        btn_lay.addStretch()
        layout.addWidget(btn_frame)

        # Ocultar botones de edición en modo historial
        if self.modo_historial:
            for w in []:  # se puede ajustar
                pass

    def _btn(self, texto, callback, estilo="normal") -> QPushButton:
        b = QPushButton(texto)
        b.setFixedHeight(30)
        estilos = {
            "primary": f"background-color: {COLOR_ACCENT_BLUE}; color: white; "
                       f"border-radius: 4px; border: none; padding: 0 10px; font-size: 12px;",
            "success": f"background-color: #2E7D32; color: white; "
                       f"border-radius: 4px; border: none; padding: 0 10px; font-size: 12px;",
            "danger":  f"background-color: #C62828; color: white; "
                       f"border-radius: 4px; border: none; padding: 0 10px; font-size: 12px;",
            "normal":  ""
        }
        if estilo in estilos:
            b.setStyleSheet(estilos[estilo])
        b.clicked.connect(callback)
        return b

    def _separador(self) -> QFrame:
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.VLine)
        sep.setStyleSheet(
            f"border: none; border-left: 1px solid {COLOR_BORDER}; "
            f"margin: 4px 2px;")
        return sep

    # ---------------------------------------------------------------------
    # DATOS
    # ---------------------------------------------------------------------

    def cargar_datos(self):
        filtros = {}
        estado = self.combo_estado.currentText()
        if estado != "Todos":
            filtros["estado"] = estado
        tipo = self.combo_tipo.currentText()
        if tipo != "Todos los tipos":
            filtros["tipo_ot"] = tipo
        prioridad = self.combo_prioridad.currentText()
        if prioridad != "Toda prioridad":
            filtros["prioridad"] = prioridad

        # Fechas
        fd = self.fecha_desde.date()
        fh = self.fecha_hasta.date()
        filtros["fecha_desde"] = datetime(fd.year(), fd.month(), fd.day())
        filtros["fecha_hasta"] = datetime(fh.year(), fh.month(), fh.day(), 23, 59, 59)

        if self.modo_historial:
            filtros["estado"] = "Cerrada"

        ots = OTService.listar_ots(filtros)

        datos = []
        ids = []
        for ot in ots:
            eq = ot.equipo.nombre if ot.equipo else "-"
            resp = (ot.responsable.nombre_completo
                    if ot.responsable else "-")
            datos.append({
                "numero": ot.numero,
                "tipo_ot": ot.tipo_ot,
                "equipo": eq,
                "fecha_prog": (ot.fecha_programada.strftime("%d/%m/%Y")
                               if ot.fecha_programada else "-"),
                "hora_ini": ot.hora_inicio_prog or "-",
                "hora_fin": ot.hora_fin_prog or "-",
                "prioridad": ot.prioridad,
                "responsable": resp,
                "estado": ot.estado,
                "costo_total": f"{ot.costo_total:,.2f}" if ot.costo_total else "-",
            })
            ids.append(ot.id)

        self.tabla.cargar(datos, ids)
        self.lbl_conteo.setText(f"{len(ots)} OT(s)")

    def _on_seleccion(self, ot_id: int):
        pass  # Se puede mostrar un panel de detalle lateral

    # ---------------------------------------------------------------------
    # ACCIONES
    # ---------------------------------------------------------------------

    def abrir_nueva_ot(self):
        if not session_usuario.puede("crear"):
            QMessageBox.warning(self, "Acceso denegado",
                                 "No tiene permiso para crear OTs.")
            return
        from app.views.ordenes.ot_form import OTForm
        dlg = OTForm(parent=self)
        if dlg.exec():
            self.cargar_datos()

    def _editar(self):
        ot_id = self.tabla.id_seleccionado()
        if not ot_id:
            QMessageBox.information(self, "Seleccionar", "Seleccione una OT.")
            return
        from app.views.ordenes.ot_form import OTForm
        dlg = OTForm(ot_id=ot_id, parent=self)
        if dlg.exec():
            self.cargar_datos()

    def _ver_detalle(self, ot_id: int = None):
        oid = ot_id or self.tabla.id_seleccionado()
        if not oid:
            return
        from app.core.database import get_session
        from app.models.orden_trabajo import OrdenTrabajo
        session = get_session()
        try:
            ot = session.query(OrdenTrabajo).get(oid)
            if not ot:
                return
            tecns = ", ".join(
                t.trabajador.nombre_completo for t in ot.tecnicos) or "-"
            QMessageBox.information(
                self, f"OT {ot.numero}",
                f"Número: {ot.numero}\n"
                f"Tipo: {ot.tipo_ot}\n"
                f"Equipo: {ot.equipo.nombre if ot.equipo else '-'}\n"
                f"Estado: {ot.estado}\n"
                f"Prioridad: {ot.prioridad}\n"
                f"Fecha programada: "
                f"{ot.fecha_programada.strftime('%d/%m/%Y') if ot.fecha_programada else '-'}\n"
                f"Horario: {ot.hora_inicio_prog or '-'} — {ot.hora_fin_prog or '-'}\n"
                f"Técnicos: {tecns}\n"
                f"Descripción: {ot.descripcion_trabajo or '-'}\n"
                f"Costo total: {ot.costo_total:,.2f}"
            )
        finally:
            session.close()

    def _ver_detalle_btn(self):
        self._ver_detalle()

    def _liberar(self):
        ot_id = self.tabla.id_seleccionado()
        if not ot_id:
            QMessageBox.information(self, "Seleccionar", "Seleccione una OT.")
            return
        if not session_usuario.puede("liberar_ot"):
            QMessageBox.warning(self, "Acceso denegado",
                                 "No tiene permiso para liberar OTs.")
            return
        ok, msg = OTService.liberar_ot(ot_id)
        if ok:
            QMessageBox.information(self, "Liberada", msg)
            self.cargar_datos()
        else:
            QMessageBox.critical(self, "No se puede liberar", msg)

    def _iniciar(self):
        ot_id = self.tabla.id_seleccionado()
        if not ot_id:
            return
        ok, msg = OTService.iniciar_ot(ot_id)
        if ok:
            QMessageBox.information(self, "Iniciada", msg)
            self.cargar_datos()
        else:
            QMessageBox.critical(self, "Error", msg)

    def _reprogramar(self):
        ot_id = self.tabla.id_seleccionado()
        if not ot_id:
            return
        from app.views.ordenes.reprogramar_dialog import ReprogramarDialog
        dlg = ReprogramarDialog(ot_id=ot_id, parent=self)
        if dlg.exec():
            self.cargar_datos()

    def _cerrar(self):
        ot_id = self.tabla.id_seleccionado()
        if not ot_id:
            QMessageBox.information(self, "Seleccionar", "Seleccione una OT.")
            return
        if not session_usuario.puede("cerrar_ot"):
            QMessageBox.warning(self, "Acceso denegado",
                                 "No tiene permiso para cerrar OTs.")
            return
        from app.views.ordenes.cierre_ot_form import CierreOTForm
        dlg = CierreOTForm(ot_id=ot_id, parent=self)
        if dlg.exec():
            self.cargar_datos()

    def _anular(self):
        ot_id = self.tabla.id_seleccionado()
        if not ot_id:
            return
        if not session_usuario.puede("editar"):
            QMessageBox.warning(self, "Acceso denegado",
                                 "No tiene permiso para anular OTs.")
            return
        motivo, ok = QInputDialog.getText(
            self, "Anular OT", "Ingrese el motivo de anulación (obligatorio):")
        if ok and motivo.strip():
            ok2, msg = OTService.anular_ot(ot_id, motivo)
            if ok2:
                QMessageBox.information(self, "Anulada", msg)
                self.cargar_datos()
            else:
                QMessageBox.critical(self, "Error", msg)
        elif ok:
            QMessageBox.warning(self, "Motivo requerido",
                                 "El motivo de anulación es obligatorio.")

    def _adjuntos(self):
        ot_id = self.tabla.id_seleccionado()
        if not ot_id:
            return
        from app.views.shared.adjuntos_widget import AdjuntosDialog
        dlg = AdjuntosDialog("ordenes_trabajo", ot_id, parent=self)
        dlg.exec()

    def _historial_ot(self):
        ot_id = self.tabla.id_seleccionado()
        if not ot_id:
            return
        from app.core.database import get_session
        from app.models.auditoria import Auditoria
        session = get_session()
        try:
            entradas = (session.query(Auditoria)
                        .filter_by(tabla_afectada="ordenes_trabajo",
                                   registro_id=ot_id)
                        .order_by(Auditoria.fecha_hora.desc())
                        .limit(20).all())
            texto = "\n".join(
                f"{e.fecha_hora.strftime('%d/%m/%Y %H:%M')} | "
                f"{e.username} | {e.accion}"
                for e in entradas
            ) or "Sin historial registrado."
            QMessageBox.information(self, "Historial de la OT", texto)
        finally:
            session.close()

    def _imprimir(self):
        ot_id = self.tabla.id_seleccionado()
        if not ot_id:
            return
        from PySide6.QtWidgets import QFileDialog
        ruta, _ = QFileDialog.getSaveFileName(
            self, "Imprimir OT", "OT.pdf", "PDF (*.pdf)")
        if ruta:
            self._generar_pdf_ot(ot_id, ruta)

    def _generar_pdf_ot(self, ot_id: int, ruta: str):
        try:
            from reportlab.lib.pagesizes import A4
            from reportlab.platypus import (SimpleDocTemplate, Paragraph,
                                             Spacer, Table, TableStyle)
            from reportlab.lib.styles import getSampleStyleSheet
            from reportlab.lib import colors
            from reportlab.lib.units import cm
            from app.core.database import get_session
            from app.models.orden_trabajo import OrdenTrabajo

            session = get_session()
            ot = session.query(OrdenTrabajo).get(ot_id)
            session.close()
            if not ot:
                return

            doc = SimpleDocTemplate(ruta, pagesize=A4)
            styles = getSampleStyleSheet()
            story = []

            story.append(Paragraph(
                "Software PMP — Orden de Trabajo", styles["Title"]))
            story.append(Spacer(1, 0.3 * cm))

            datos = [
                ["Campo", "Valor"],
                ["Número OT", ot.numero],
                ["Tipo", ot.tipo_ot],
                ["Equipo", ot.equipo.nombre if ot.equipo else "-"],
                ["Estado", ot.estado],
                ["Prioridad", ot.prioridad],
                ["Fecha programada",
                 ot.fecha_programada.strftime("%d/%m/%Y") if ot.fecha_programada else "-"],
                ["Horario", f"{ot.hora_inicio_prog or '-'} — {ot.hora_fin_prog or '-'}"],
                ["Responsable",
                 ot.responsable.nombre_completo if ot.responsable else "-"],
                ["Descripción", ot.descripcion_trabajo or "-"],
                ["Costo total", f"{ot.costo_total:,.2f}"],
            ]
            t = Table(datos, colWidths=[5 * cm, 13 * cm])
            t.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0),
                 colors.HexColor("#1565C0")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1),
                 [colors.HexColor("#F5F5F5"), colors.white]),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("PADDING", (0, 0), (-1, -1), 6),
            ]))
            story.append(t)
            doc.build(story)
            QMessageBox.information(self, "Impreso", f"OT exportada: {ruta}")
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def _exportar(self):
        from PySide6.QtWidgets import QFileDialog
        ruta, _ = QFileDialog.getSaveFileName(
            self, "Exportar OTs", "ordenes_trabajo.xlsx",
            "Excel (*.xlsx)")
        if not ruta:
            return
        try:
            import pandas as pd
            filtros = {}
            estado = self.combo_estado.currentText()
            if estado != "Todos":
                filtros["estado"] = estado
            ots = OTService.listar_ots(filtros)
            datos = [{
                "Número": o.numero, "Tipo": o.tipo_ot,
                "Equipo": o.equipo.nombre if o.equipo else "-",
                "Estado": o.estado, "Prioridad": o.prioridad,
                "Fecha Programada": (
                    o.fecha_programada.strftime("%d/%m/%Y")
                    if o.fecha_programada else "-"),
                "Costo Total": o.costo_total or 0,
            } for o in ots]
            pd.DataFrame(datos).to_excel(ruta, index=False)
            QMessageBox.information(self, "Exportar", f"Exportado: {ruta}")
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))
