"""
Módulo Reportes — Generación de reportes PDF y Excel.
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFrame, QComboBox, QDateEdit,
    QCheckBox, QGroupBox, QMessageBox, QTextEdit,
    QFileDialog, QProgressBar
)
from PySide6.QtCore import Qt, QDate, QThread, QObject, Signal

from app.services.kpi_service import KPIService
from app.services.ot_service import OTService
from app.services.material_service import MaterialService
from app.views.shared.styles import (
    COLOR_TEXT_PRIMARY, COLOR_TEXT_SECONDARY, COLOR_ACCENT_BLUE,
    COLOR_BORDER, COLOR_BG_PANEL, COLOR_SUCCESS
)
from datetime import datetime


class GeneradorReporteWorker(QObject):
    """Worker para generar reportes en hilo separado."""
    terminado = Signal(str)  # ruta del archivo
    error = Signal(str)
    progreso = Signal(int)

    def __init__(self, tipo: str, ruta: str, params: dict):
        super().__init__()
        self.tipo = tipo
        self.ruta = ruta
        self.params = params

    def run(self):
        try:
            if self.tipo == "kpi_pdf":
                self._generar_kpi_pdf()
            elif self.tipo == "ots_excel":
                self._generar_ots_excel()
            elif self.tipo == "inventario_excel":
                self._generar_inventario_excel()
            elif self.tipo == "completo_pdf":
                self._generar_reporte_completo()
            self.terminado.emit(self.ruta)
        except Exception as e:
            self.error.emit(str(e))

    def _generar_kpi_pdf(self):
        from reportlab.lib.pagesizes import A4, landscape
        from reportlab.platypus import (SimpleDocTemplate, Paragraph,
                                         Spacer, Table, TableStyle, HRFlowable)
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib import colors
        from reportlab.lib.units import cm

        kpi = KPIService.calcular_kpis(
            self.params.get("desde"), self.params.get("hasta"))
        doc = SimpleDocTemplate(self.ruta, pagesize=A4)
        styles = getSampleStyleSheet()
        story = []

        # Título
        story.append(Paragraph(
            "REPORTE DE KPIs — SOFTWARE PMP", styles["Title"]))
        story.append(Paragraph(
            f"Período: {self.params.get('desde','').strftime('%d/%m/%Y') if self.params.get('desde') else '-'} "
            f"— {self.params.get('hasta','').strftime('%d/%m/%Y') if self.params.get('hasta') else '-'}",
            styles["Normal"]))
        story.append(Paragraph(
            f"Generado: {datetime.now().strftime('%d/%m/%Y %H:%M')}",
            styles["Normal"]))
        story.append(Spacer(1, 0.5 * cm))
        story.append(HRFlowable(width="100%"))
        story.append(Spacer(1, 0.3 * cm))

        self.progreso.emit(25)

        # Tabla KPIs
        tabla_data = [
            ["Indicador", "Valor", "Referencia", "Estado"],
            ["MTTR (h)",
             f"{kpi.mttr:.2f}",
             "<= 4 h ideal",
             "OK" if kpi.mttr <= 4 else "[!]"],
            ["MTBF (h)",
             f"{kpi.mtbf:.2f}",
             ">= 500 h ideal",
             "OK" if kpi.mtbf >= 500 else "[!]"],
            ["Disponibilidad (%)",
             f"{kpi.disponibilidad:.1f}",
             ">= 95% ideal",
             "OK" if kpi.disponibilidad >= 95 else "[!]"],
            ["% Preventivo",
             f"{kpi.pct_preventivo:.1f}",
             ">= 70% ideal",
             "OK" if kpi.pct_preventivo >= 70 else "[!]"],
            ["% Correctivo",
             f"{kpi.pct_correctivo:.1f}",
             "<= 30% ideal",
             "OK" if kpi.pct_correctivo <= 30 else "[!]"],
            ["Cumplimiento Plan (%)",
             f"{kpi.cumplimiento_plan:.1f}",
             ">= 90% ideal",
             "OK" if kpi.cumplimiento_plan >= 90 else "[!]"],
            ["Total Fallas",
             str(kpi.total_fallas), "", ""],
            ["OTs Cerradas",
             str(kpi.ots_cerradas), "", ""],
            ["OTs Vencidas",
             str(kpi.ots_vencidas), "",
             "[!]" if kpi.ots_vencidas > 0 else ""],
            ["Tiempo Muerto Total (h)",
             f"{kpi.tiempo_muerto_total:.1f}", "", ""],
            ["Costo Total Período",
             f"{kpi.costo_periodo:,.2f}", "", ""],
        ]
        t = Table(tabla_data,
                  colWidths=[7 * cm, 3 * cm, 4 * cm, 2 * cm])
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0),
             colors.HexColor("#1565C0")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 10),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1),
             [colors.HexColor("#F5F5F5"), colors.white]),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("PADDING", (0, 0), (-1, -1), 6),
            ("ALIGN", (1, 1), (3, -1), "CENTER"),
        ]))
        story.append(t)

        self.progreso.emit(70)

        # Top equipos
        if kpi.top_equipos_fallas:
            story.append(Spacer(1, 0.5 * cm))
            story.append(Paragraph(
                "Top equipos con mayor número de fallas:",
                styles["Heading2"]))
            top_data = [["Equipo", "Fallas", "Tiempo Muerto (h)", "Costo"]]
            for t_eq in kpi.top_equipos_fallas[:5]:
                top_data.append([
                    t_eq["nombre"],
                    str(t_eq["fallas"]),
                    f"{t_eq['tiempo_muerto']:.1f}",
                    f"{t_eq['costo']:,.2f}",
                ])
            t2 = Table(top_data,
                       colWidths=[8 * cm, 2 * cm, 4 * cm, 3 * cm])
            t2.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0),
                 colors.HexColor("#37474F")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1),
                 [colors.HexColor("#ECEFF1"), colors.white]),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("PADDING", (0, 0), (-1, -1), 5),
            ]))
            story.append(t2)

        self.progreso.emit(90)
        doc.build(story)
        self.progreso.emit(100)

    def _generar_ots_excel(self):
        import pandas as pd
        ots = OTService.listar_ots(self.params)
        datos = [{
            "Número": o.numero,
            "Tipo": o.tipo_ot,
            "Equipo": o.equipo.nombre if o.equipo else "-",
            "Estado": o.estado,
            "Prioridad": o.prioridad,
            "Fecha Programada": (
                o.fecha_programada.strftime("%d/%m/%Y")
                if o.fecha_programada else "-"),
            "Fecha Cierre": (
                o.fecha_cierre.strftime("%d/%m/%Y")
                if o.fecha_cierre else "-"),
            "Horas Reales": o.horas_reales or 0,
            "Costo Total": o.costo_total or 0,
            "Causa Raíz": o.causa_raiz or "-",
        } for o in ots]
        pd.DataFrame(datos).to_excel(self.ruta, index=False)

    def _generar_inventario_excel(self):
        import pandas as pd
        mats = MaterialService.listar()
        datos = [{
            "Código": m.codigo,
            "Descripción": m.descripcion,
            "Categoría": m.categoria,
            "Unidad": m.unidad,
            "Stock actual": m.stock_actual,
            "Stock mínimo": m.stock_minimo,
            "Alerta": m.alerta_stock,
            "Costo unit.": m.costo_unitario,
            "Valor total": m.stock_actual * m.costo_unitario,
            "Proveedor": m.proveedor,
            "Estado": m.estado,
        } for m in mats]
        pd.DataFrame(datos).to_excel(self.ruta, index=False)

    def _generar_reporte_completo(self):
        """Reporte PDF completo: portada, KPIs, OTs resumen, inventario."""
        self._generar_kpi_pdf()


class ReportesWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._construir_ui()

    def _construir_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(16)

        lbl = QLabel("[Rep]  Generación de Reportes")
        lbl.setStyleSheet(
            f"font-size: 18px; font-weight: 700; color: {COLOR_TEXT_PRIMARY};")
        layout.addWidget(lbl)

        # Filtros de período
        fil = QGroupBox("Período del reporte")
        fil_lay = QHBoxLayout(fil)
        self.fecha_desde = QDateEdit()
        self.fecha_desde.setDate(QDate.currentDate().addDays(-30))
        self.fecha_desde.setCalendarPopup(True)
        self.fecha_hasta = QDateEdit()
        self.fecha_hasta.setDate(QDate.currentDate())
        self.fecha_hasta.setCalendarPopup(True)
        fil_lay.addWidget(QLabel("Desde:"))
        fil_lay.addWidget(self.fecha_desde)
        fil_lay.addWidget(QLabel("Hasta:"))
        fil_lay.addWidget(self.fecha_hasta)
        fil_lay.addStretch()
        layout.addWidget(fil)

        # Grilla de reportes disponibles
        grilla = QHBoxLayout()
        grilla.setSpacing(16)

        reportes = [
            ("[KPI] KPIs en PDF",
             "Resumen de indicadores clave (MTTR, MTBF, disponibilidad) en PDF.",
             self._generar_kpis_pdf, "#1565C0"),
            ("[OT] Listado de OTs en Excel",
             "Todas las OTs del período con estado, costos y fechas.",
             self._generar_ots_excel, "#2E7D32"),
            ("[Mat] Inventario de Materiales",
             "Stock actual, alertas y valorización del almacén.",
             self._generar_inventario_excel, "#6A1B9A"),
            ("[Doc] Reporte Completo PDF",
             "Informe ejecutivo con KPIs, OTs y análisis de fallas.",
             self._generar_completo_pdf, "#B71C1C"),
        ]

        for titulo, desc, cb, color in reportes:
            card = self._crear_card_reporte(titulo, desc, cb, color)
            grilla.addWidget(card)

        layout.addLayout(grilla)

        # Barra de progreso
        self.progress = QProgressBar()
        self.progress.setValue(0)
        self.progress.setVisible(False)
        layout.addWidget(self.progress)

        self.lbl_status = QLabel("")
        self.lbl_status.setStyleSheet(
            f"color: {COLOR_SUCCESS}; font-weight: 600;")
        layout.addWidget(self.lbl_status)

        layout.addStretch()

    def _crear_card_reporte(self, titulo: str, desc: str,
                             cb, color: str) -> QFrame:
        card = QFrame()
        card.setStyleSheet(
            f"background-color: {COLOR_BG_PANEL}; border-radius: 8px; "
            f"border: 1px solid {COLOR_BORDER}; border-top: 4px solid {color};")
        card.setMinimumSize(200, 160)
        lay = QVBoxLayout(card)
        lay.setContentsMargins(16, 14, 16, 14)
        lay.setSpacing(8)

        lbl_t = QLabel(titulo)
        lbl_t.setStyleSheet(
            f"font-weight: 700; font-size: 13px; "
            f"color: {COLOR_TEXT_PRIMARY}; border: none;")
        lbl_t.setWordWrap(True)

        lbl_d = QLabel(desc)
        lbl_d.setStyleSheet(
            f"font-size: 11px; color: {COLOR_TEXT_SECONDARY}; border: none;")
        lbl_d.setWordWrap(True)

        btn = QPushButton("Generar")
        btn.setFixedHeight(32)
        btn.setStyleSheet(
            f"background-color: {color}; color: white; font-weight: 600; "
            f"border-radius: 4px; border: none;")
        btn.clicked.connect(cb)

        lay.addWidget(lbl_t)
        lay.addWidget(lbl_d)
        lay.addStretch()
        lay.addWidget(btn)
        return card

    def _get_params(self) -> dict:
        fd = self.fecha_desde.date()
        fh = self.fecha_hasta.date()
        return {
            "desde": datetime(fd.year(), fd.month(), fd.day()),
            "hasta": datetime(fh.year(), fh.month(), fh.day(), 23, 59, 59),
        }

    def _generar_kpis_pdf(self):
        ruta, _ = QFileDialog.getSaveFileName(
            self, "Guardar Reporte KPIs", "kpis_pmp.pdf", "PDF (*.pdf)")
        if not ruta:
            return
        self._ejecutar_reporte("kpi_pdf", ruta, self._get_params())

    def _generar_ots_excel(self):
        ruta, _ = QFileDialog.getSaveFileName(
            self, "Guardar OTs Excel", "ordenes_trabajo.xlsx",
            "Excel (*.xlsx)")
        if not ruta:
            return
        params = self._get_params()
        params["fecha_desde"] = params.pop("desde")
        params["fecha_hasta"] = params.pop("hasta")
        self._ejecutar_reporte("ots_excel", ruta, params)

    def _generar_inventario_excel(self):
        ruta, _ = QFileDialog.getSaveFileName(
            self, "Guardar Inventario", "inventario_materiales.xlsx",
            "Excel (*.xlsx)")
        if not ruta:
            return
        self._ejecutar_reporte("inventario_excel", ruta, {})

    def _generar_completo_pdf(self):
        ruta, _ = QFileDialog.getSaveFileName(
            self, "Guardar Reporte Completo", "reporte_pmp_completo.pdf",
            "PDF (*.pdf)")
        if not ruta:
            return
        self._ejecutar_reporte("completo_pdf", ruta, self._get_params())

    def _ejecutar_reporte(self, tipo: str, ruta: str, params: dict):
        self.progress.setValue(0)
        self.progress.setVisible(True)
        self.lbl_status.setText("Generando reporte...")

        self._thread = QThread()
        self._worker = GeneradorReporteWorker(tipo, ruta, params)
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.progreso.connect(self.progress.setValue)
        self._worker.terminado.connect(self._on_reporte_ok)
        self._worker.error.connect(self._on_reporte_error)
        self._worker.terminado.connect(self._thread.quit)
        self._worker.error.connect(self._thread.quit)
        self._thread.start()

    def _on_reporte_ok(self, ruta: str):
        self.progress.setVisible(False)
        self.lbl_status.setText(f"[OK] Reporte generado: {ruta}")
        QMessageBox.information(self, "Reporte listo",
                                 f"Reporte guardado exitosamente:\n{ruta}")

    def _on_reporte_error(self, msg: str):
        self.progress.setVisible(False)
        self.lbl_status.setText(f"[ERR] Error: {msg}")
        QMessageBox.critical(self, "Error al generar reporte", msg)
