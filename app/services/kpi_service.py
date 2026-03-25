"""
Servicio de KPIs de Mantenimiento.

Fórmulas implementadas:
  MTTR  = Σ(tiempo_fuera_servicio) / cantidad_fallas
  MTBF  = (tiempo_total_operacion - Σ tiempo_parado) / cantidad_fallas
  Disponibilidad = MTBF / (MTBF + MTTR) * 100
  % Preventivo   = OTs_cerradas_preventivo / total_OTs_cerradas * 100
  % Correctivo   = OTs_cerradas_correctivo / total_OTs_cerradas * 100
  Cumplimiento   = OTs_preventivas_cerradas_a_tiempo / OTs_preventivas_programadas * 100
  Repetitividad  = fallas con causa repetida / total_fallas

Solo se usan OTs en estado 'Cerrada'. Anuladas y borradores quedan excluidos.
"""
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass

from app.core.database import get_session
from app.models.orden_trabajo import OrdenTrabajo
from app.models.equipo import Equipo
from app.models.historial import HistorialEquipo


@dataclass
class KPIResultado:
    mttr: float = 0.0           # horas
    mtbf: float = 0.0           # horas
    disponibilidad: float = 0.0 # porcentaje
    pct_preventivo: float = 0.0 # porcentaje
    pct_correctivo: float = 0.0 # porcentaje
    cumplimiento_plan: float = 0.0  # porcentaje
    total_fallas: int = 0
    ots_abiertas: int = 0
    ots_proceso: int = 0
    ots_vencidas: int = 0
    ots_cerradas: int = 0
    costo_periodo: float = 0.0
    tiempo_muerto_total: float = 0.0  # horas
    top_equipos_fallas: List[Dict] = None

    def __post_init__(self):
        if self.top_equipos_fallas is None:
            self.top_equipos_fallas = []


class KPIService:

    @staticmethod
    def calcular_kpis(fecha_desde: datetime = None,
                      fecha_hasta: datetime = None,
                      equipo_id: int = None) -> KPIResultado:
        """
        Calcula todos los KPIs del periodo indicado.
        Si no se indica periodo, usa los últimos 90 días.
        """
        if not fecha_hasta:
            fecha_hasta = datetime.now()
        if not fecha_desde:
            fecha_desde = fecha_hasta - timedelta(days=90)

        session = get_session()
        try:
            # Query base: solo OTs cerradas en el periodo
            q_cerradas = (session.query(OrdenTrabajo)
                          .filter(
                              OrdenTrabajo.estado == "Cerrada",
                              OrdenTrabajo.fecha_cierre >= fecha_desde,
                              OrdenTrabajo.fecha_cierre <= fecha_hasta
                          ))
            if equipo_id:
                q_cerradas = q_cerradas.filter(OrdenTrabajo.equipo_id == equipo_id)
            ots_cerradas = q_cerradas.all()

            # OTs abiertas (programadas o liberadas)
            q_abiertas = (session.query(OrdenTrabajo)
                          .filter(OrdenTrabajo.estado.in_(["Programada", "Liberada"])))
            if equipo_id:
                q_abiertas = q_abiertas.filter(OrdenTrabajo.equipo_id == equipo_id)
            cnt_abiertas = q_abiertas.count()

            # OTs en proceso
            q_proceso = (session.query(OrdenTrabajo)
                         .filter(OrdenTrabajo.estado == "En proceso"))
            if equipo_id:
                q_proceso = q_proceso.filter(OrdenTrabajo.equipo_id == equipo_id)
            cnt_proceso = q_proceso.count()

            # OTs vencidas (programadas con fecha_programada < hoy)
            q_vencidas = (session.query(OrdenTrabajo)
                          .filter(
                              OrdenTrabajo.estado.in_(["Programada", "Liberada"]),
                              OrdenTrabajo.fecha_programada < datetime.now()
                          ))
            if equipo_id:
                q_vencidas = q_vencidas.filter(OrdenTrabajo.equipo_id == equipo_id)
            cnt_vencidas = q_vencidas.count()

            # -- Calcular MTTR ----------------------------------------------
            # MTTR = Σ(tiempo_fuera_servicio de correctivos) / cantidad de fallas correctivas
            correctivos = [o for o in ots_cerradas
                           if o.tipo_ot in ("Correctivo", "Emergencia")]
            total_fallas = len(correctivos)
            tiempo_fuera_total = sum(o.tiempo_fuera_servicio or 0.0 for o in correctivos)

            mttr = (tiempo_fuera_total / total_fallas) if total_fallas > 0 else 0.0

            # -- Calcular MTBF ----------------------------------------------
            # MTBF = (horas del periodo - tiempo_muerto_total) / cantidad_fallas
            horas_periodo = (fecha_hasta - fecha_desde).total_seconds() / 3600.0
            mtbf = ((horas_periodo - tiempo_fuera_total) / total_fallas
                    ) if total_fallas > 0 else horas_periodo

            # -- Disponibilidad ---------------------------------------------
            # Disponibilidad = MTBF / (MTBF + MTTR) * 100
            disponibilidad = (mtbf / (mtbf + mttr) * 100
                              ) if (mtbf + mttr) > 0 else 100.0

            # -- % Preventivo / Correctivo ----------------------------------
            total_cerradas = len(ots_cerradas)
            preventivos = [o for o in ots_cerradas
                           if o.tipo_ot in ("Preventivo", "Predictivo",
                                             "Lubricación", "Inspección")]
            pct_prev = (len(preventivos) / total_cerradas * 100
                        ) if total_cerradas > 0 else 0.0
            pct_corr = (len(correctivos) / total_cerradas * 100
                        ) if total_cerradas > 0 else 0.0

            # -- Cumplimiento del plan --------------------------------------
            # OTs preventivas cerradas en su fecha / OTs preventivas programadas en el periodo
            programadas_prev = (session.query(OrdenTrabajo)
                                .filter(
                                    OrdenTrabajo.tipo_ot.in_(
                                        ["Preventivo", "Predictivo", "Lubricación"]),
                                    OrdenTrabajo.fecha_programada >= fecha_desde,
                                    OrdenTrabajo.fecha_programada <= fecha_hasta
                                ).count())
            cerradas_prev_en_fecha = sum(
                1 for o in preventivos
                if o.fecha_cierre and o.fecha_programada
                and o.fecha_cierre.date() <= o.fecha_programada.date()
            )
            cumplimiento = (cerradas_prev_en_fecha / programadas_prev * 100
                            ) if programadas_prev > 0 else 0.0

            # -- Costo total del periodo ------------------------------------
            costo_periodo = sum(o.costo_total or 0.0 for o in ots_cerradas)

            # -- Top equipos con más fallas ---------------------------------
            conteo_fallas: Dict[int, Dict] = {}
            for o in correctivos:
                if o.equipo_id not in conteo_fallas:
                    eq = session.query(Equipo).get(o.equipo_id)
                    nombre_eq = eq.nombre if eq else f"ID {o.equipo_id}"
                    conteo_fallas[o.equipo_id] = {
                        "equipo_id": o.equipo_id,
                        "nombre": nombre_eq,
                        "fallas": 0,
                        "costo": 0.0,
                        "tiempo_muerto": 0.0
                    }
                conteo_fallas[o.equipo_id]["fallas"] += 1
                conteo_fallas[o.equipo_id]["costo"] += (o.costo_total or 0.0)
                conteo_fallas[o.equipo_id]["tiempo_muerto"] += (
                    o.tiempo_fuera_servicio or 0.0)

            top = sorted(conteo_fallas.values(),
                         key=lambda x: x["fallas"], reverse=True)[:10]

            return KPIResultado(
                mttr=round(mttr, 2),
                mtbf=round(mtbf, 2),
                disponibilidad=round(disponibilidad, 2),
                pct_preventivo=round(pct_prev, 2),
                pct_correctivo=round(pct_corr, 2),
                cumplimiento_plan=round(cumplimiento, 2),
                total_fallas=total_fallas,
                ots_abiertas=cnt_abiertas,
                ots_proceso=cnt_proceso,
                ots_vencidas=cnt_vencidas,
                ots_cerradas=total_cerradas,
                costo_periodo=round(costo_periodo, 2),
                tiempo_muerto_total=round(tiempo_fuera_total, 2),
                top_equipos_fallas=top
            )

        finally:
            session.close()

    @staticmethod
    def kpis_por_equipo(fecha_desde: datetime = None,
                        fecha_hasta: datetime = None) -> List[Dict]:
        """Retorna una lista de KPIs desglosados por equipo."""
        if not fecha_hasta:
            fecha_hasta = datetime.now()
        if not fecha_desde:
            fecha_desde = fecha_hasta - timedelta(days=90)

        session = get_session()
        try:
            equipos = session.query(Equipo).filter(Equipo.estado == "Activo").all()
            resultado = []
            for eq in equipos:
                kpi = KPIService.calcular_kpis(fecha_desde, fecha_hasta, eq.id)
                resultado.append({
                    "equipo_id": eq.id,
                    "codigo": eq.codigo,
                    "nombre": eq.nombre,
                    "area": eq.area,
                    "criticidad": eq.criticidad,
                    "mttr": kpi.mttr,
                    "mtbf": kpi.mtbf,
                    "disponibilidad": kpi.disponibilidad,
                    "fallas": kpi.total_fallas,
                    "costo": kpi.costo_periodo,
                    "tiempo_muerto": kpi.tiempo_muerto_total,
                })
            return resultado
        finally:
            session.close()
