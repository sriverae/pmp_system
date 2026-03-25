"""
Servicio de Planes de Mantenimiento.
Genera OTs automáticamente desde planes activos.
"""
from datetime import datetime, timedelta
from typing import List, Tuple, Optional
from sqlalchemy.orm import joinedload

from app.core.database import get_session
from app.core.session import session_usuario
from app.models.plan import PlanMantenimiento, ChecklistPlan, PlanMaterial
from app.models.orden_trabajo import OrdenTrabajo, OTMaterialPrevisto
from app.models.equipo import Equipo, LecturaContador
from app.services.auditoria_service import AuditoriaService
from app.services.ot_service import OTService


class PlanService:

    @staticmethod
    def listar(equipo_id: int = None, estado: str = None,
               texto: str = None) -> List[PlanMantenimiento]:
        session = get_session()
        try:
            q = session.query(PlanMantenimiento).options(
                joinedload(PlanMantenimiento.equipo),
                joinedload(PlanMantenimiento.responsable),
            )
            if equipo_id:
                q = q.filter_by(equipo_id=equipo_id)
            if estado:
                q = q.filter_by(estado=estado)
            if texto:
                like = f"%{texto}%"
                q = q.filter(
                    (PlanMantenimiento.codigo.ilike(like)) |
                    (PlanMantenimiento.descripcion.ilike(like))
                )
            return q.order_by(PlanMantenimiento.codigo).all()
        finally:
            session.close()

    @staticmethod
    def crear(datos: dict, checklist: List[dict],
               materiales: List[dict]) -> Tuple[bool, str, Optional[int]]:
        """Crea un plan de mantenimiento con checklist y materiales sugeridos."""
        if not datos.get("codigo"):
            return False, "El código del plan es obligatorio.", None
        if not datos.get("equipo_id"):
            return False, "Debe asociarse a un equipo.", None
        if not datos.get("frecuencia") or float(datos["frecuencia"]) <= 0:
            return False, "La frecuencia debe ser mayor a cero.", None
        if datos.get("criterio") == "Contador" and not datos.get("contador_asociado_id"):
            return False, "Para criterio Contador debe indicar el contador asociado.", None

        session = get_session()
        try:
            # Verificar código único
            dup = session.query(PlanMantenimiento).filter_by(
                codigo=datos["codigo"]).first()
            if dup:
                return False, f"Ya existe el plan con código '{datos['codigo']}'.", None

            # Verificar duplicado funcional (mismo equipo + descripción + tipo)
            dup_func = session.query(PlanMantenimiento).filter(
                PlanMantenimiento.equipo_id == datos["equipo_id"],
                PlanMantenimiento.descripcion == datos.get("descripcion"),
                PlanMantenimiento.tipo_mantenimiento == datos.get("tipo_mantenimiento"),
                PlanMantenimiento.estado == "Activo"
            ).first()
            if dup_func:
                return (False,
                        f"Ya existe un plan activo '{dup_func.codigo}' con la misma "
                        "descripción y tipo para ese equipo.", None)

            plan = PlanMantenimiento(
                codigo=datos["codigo"],
                equipo_id=datos["equipo_id"],
                descripcion=datos.get("descripcion", ""),
                tipo_mantenimiento=datos.get("tipo_mantenimiento", "Preventivo"),
                frecuencia=float(datos["frecuencia"]),
                unidad_frecuencia=datos.get("unidad_frecuencia", "Días"),
                criterio=datos.get("criterio", "Fecha"),
                contador_asociado_id=datos.get("contador_asociado_id"),
                duracion_estimada=float(datos.get("duracion_estimada", 1.0)),
                prioridad=datos.get("prioridad", "Normal"),
                criticidad=datos.get("criticidad", "Media"),
                responsable_id=datos.get("responsable_id"),
                procedimiento=datos.get("procedimiento"),
                fecha_inicio=datos.get("fecha_inicio"),
                fecha_fin=datos.get("fecha_fin"),
                alerta_dias_anticipacion=int(datos.get("alerta_dias_anticipacion", 7)),
                estado="Activo",
                creado_por=session_usuario.usuario_id
            )
            session.add(plan)
            session.flush()

            # Calcular próxima ejecución
            plan.proxima_ejecucion = plan.calcular_proxima_ejecucion()

            # Agregar checklist
            for i, item in enumerate(checklist):
                session.add(ChecklistPlan(
                    plan_id=plan.id,
                    orden=i + 1,
                    descripcion=item["descripcion"],
                    obligatorio=item.get("obligatorio", False)
                ))

            # Agregar materiales sugeridos
            for mat in materiales:
                session.add(PlanMaterial(
                    plan_id=plan.id,
                    material_id=mat["material_id"],
                    cantidad_sugerida=float(mat.get("cantidad", 1.0))
                ))

            session.commit()
            AuditoriaService.registrar(
                "Planes", "Crear plan",
                tabla="planes_mantenimiento", registro_id=plan.id,
                valor_nuevo={"codigo": plan.codigo}
            )
            return True, f"Plan {plan.codigo} creado.", plan.id

        except Exception as e:
            session.rollback()
            return False, str(e), None
        finally:
            session.close()

    @staticmethod
    def pausar(plan_id: int) -> Tuple[bool, str]:
        session = get_session()
        try:
            plan = session.query(PlanMantenimiento).get(plan_id)
            if not plan:
                return False, "Plan no encontrado."
            if plan.estado == "Pausado":
                return False, "El plan ya está pausado."
            plan.estado = "Pausado"
            session.commit()
            AuditoriaService.registrar("Planes", "Pausar plan",
                                        registro_id=plan_id)
            return True, "Plan pausado. No generará nuevas OTs."
        except Exception as e:
            session.rollback()
            return False, str(e)
        finally:
            session.close()

    @staticmethod
    def reactivar(plan_id: int) -> Tuple[bool, str]:
        session = get_session()
        try:
            plan = session.query(PlanMantenimiento).get(plan_id)
            if not plan:
                return False, "Plan no encontrado."
            plan.estado = "Activo"
            plan.proxima_ejecucion = plan.calcular_proxima_ejecucion()
            session.commit()
            AuditoriaService.registrar("Planes", "Reactivar plan",
                                        registro_id=plan_id)
            return True, "Plan reactivado."
        except Exception as e:
            session.rollback()
            return False, str(e)
        finally:
            session.close()

    @staticmethod
    def duplicar(plan_id: int, nuevo_codigo: str) -> Tuple[bool, str, Optional[int]]:
        """Crea una copia editable de un plan existente."""
        session = get_session()
        try:
            original = session.query(PlanMantenimiento).get(plan_id)
            if not original:
                return False, "Plan no encontrado.", None
            dup = session.query(PlanMantenimiento).filter_by(
                codigo=nuevo_codigo).first()
            if dup:
                return False, f"Ya existe el código '{nuevo_codigo}'.", None

            nuevo = PlanMantenimiento(
                codigo=nuevo_codigo,
                equipo_id=original.equipo_id,
                descripcion=f"[COPIA] {original.descripcion}",
                tipo_mantenimiento=original.tipo_mantenimiento,
                frecuencia=original.frecuencia,
                unidad_frecuencia=original.unidad_frecuencia,
                criterio=original.criterio,
                duracion_estimada=original.duracion_estimada,
                prioridad=original.prioridad,
                criticidad=original.criticidad,
                responsable_id=original.responsable_id,
                procedimiento=original.procedimiento,
                estado="Activo",
                alerta_dias_anticipacion=original.alerta_dias_anticipacion or 7,
                creado_por=session_usuario.usuario_id
            )
            session.add(nuevo)
            session.flush()
            nuevo.proxima_ejecucion = nuevo.calcular_proxima_ejecucion()

            for item in original.checklist:
                session.add(ChecklistPlan(
                    plan_id=nuevo.id,
                    orden=item.orden,
                    descripcion=item.descripcion,
                    obligatorio=item.obligatorio
                ))
            for pm in original.materiales:
                session.add(PlanMaterial(
                    plan_id=nuevo.id,
                    material_id=pm.material_id,
                    cantidad_sugerida=pm.cantidad_sugerida
                ))

            session.commit()
            return True, f"Plan duplicado como '{nuevo_codigo}'.", nuevo.id
        except Exception as e:
            session.rollback()
            return False, str(e), None
        finally:
            session.close()

    @staticmethod
    def generar_ots_desde_planes(fecha_limite: datetime = None) -> Tuple[int, List[str]]:
        """
        Genera OTs automáticamente para todos los planes activos cuya
        próxima_ejecucion <= fecha_limite.
        Evita duplicar OTs para el mismo equipo+plan en la misma ventana.
        Retorna (cantidad_generadas, lista_mensajes).
        """
        if not fecha_limite:
            fecha_limite = datetime.now()

        session = get_session()
        generadas = 0
        mensajes = []
        try:
            planes = session.query(PlanMantenimiento).filter(
                PlanMantenimiento.estado == "Activo",
                PlanMantenimiento.proxima_ejecucion <= fecha_limite
            ).all()

            for plan in planes:
                # Verificar equipo activo
                equipo = session.query(Equipo).get(plan.equipo_id)
                if not equipo or equipo.estado == "Dado de baja":
                    mensajes.append(
                        f"Plan {plan.codigo}: equipo inactivo, omitido.")
                    continue

                # Evitar OT duplicada en el mismo mes para el mismo plan
                ya_existe = session.query(OrdenTrabajo).filter(
                    OrdenTrabajo.plan_id == plan.id,
                    OrdenTrabajo.estado.notin_(["Anulada"]),
                    OrdenTrabajo.fecha_programada >= datetime(
                        fecha_limite.year, fecha_limite.month, 1)
                ).first()
                if ya_existe:
                    mensajes.append(
                        f"Plan {plan.codigo}: OT {ya_existe.numero} ya existe para este periodo.")
                    continue

                numero = OTService.generar_numero_ot()
                ot = OrdenTrabajo(
                    numero=numero,
                    tipo_ot=plan.tipo_mantenimiento,
                    equipo_id=plan.equipo_id,
                    plan_id=plan.id,
                    prioridad=plan.prioridad,
                    criticidad=plan.criticidad,
                    estado="Programada",
                    fecha_programada=plan.proxima_ejecucion,
                    duracion_estimada=plan.duracion_estimada,
                    responsable_id=plan.responsable_id,
                    descripcion_trabajo=plan.descripcion,
                    procedimiento=plan.procedimiento,
                    creado_por=session_usuario.usuario_id
                )
                session.add(ot)
                session.flush()

                # Copiar materiales sugeridos como previstos
                for pm in plan.materiales:
                    session.add(OTMaterialPrevisto(
                        ot_id=ot.id,
                        material_id=pm.material_id,
                        cantidad_prevista=pm.cantidad_sugerida,
                        obligatorio=False
                    ))

                # Actualizar plan
                plan.ultima_ejecucion = plan.proxima_ejecucion
                plan.proxima_ejecucion = plan.calcular_proxima_ejecucion()

                generadas += 1
                mensajes.append(f"OT {numero} generada para plan {plan.codigo}.")

            session.commit()
            AuditoriaService.registrar(
                "Planes", f"Generación automática OTs: {generadas} generadas"
            )
            return generadas, mensajes
        except Exception as e:
            session.rollback()
            return 0, [f"Error: {str(e)}"]
        finally:
            session.close()

    @staticmethod
    def obtener_alertas_mantenimiento(dias_max: int = 30) -> List[dict]:
        """
        Retorna planes activos con mantenimiento próximo según
        alerta_dias_anticipacion configurable por plan.
        """
        ahora = datetime.now()
        limite_global = ahora + timedelta(days=dias_max)
        session = get_session()
        try:
            planes = (session.query(PlanMantenimiento)
                      .options(joinedload(PlanMantenimiento.equipo))
                      .filter(
                          PlanMantenimiento.estado == "Activo",
                          PlanMantenimiento.proxima_ejecucion.isnot(None),
                          PlanMantenimiento.proxima_ejecucion <= limite_global
                      )
                      .order_by(PlanMantenimiento.proxima_ejecucion.asc())
                      .all())

            alertas = []
            for p in planes:
                if not p.proxima_ejecucion:
                    continue
                dias_alerta = int(p.alerta_dias_anticipacion or 7)
                delta_dias = (p.proxima_ejecucion.date() - ahora.date()).days
                if delta_dias <= dias_alerta:
                    alertas.append({
                        "plan_id": p.id,
                        "codigo": p.codigo,
                        "equipo": p.equipo.nombre if p.equipo else "-",
                        "tipo": p.tipo_mantenimiento,
                        "proxima_ejecucion": p.proxima_ejecucion,
                        "dias_restantes": delta_dias,
                        "dias_alerta": dias_alerta,
                        "prioridad": p.prioridad,
                    })
            return alertas
        finally:
            session.close()

    @staticmethod
    def registrar_lectura_diaria(equipo_id: int, lectura: float, observaciones: str = "") -> Tuple[bool, str]:
        """Registra lectura diaria de horómetro/km y actualiza el equipo."""
        session = get_session()
        try:
            eq = session.query(Equipo).get(equipo_id)
            if not eq:
                return False, "Equipo no encontrado."
            lectura = float(lectura)
            if lectura < 0:
                return False, "La lectura no puede ser negativa."

            session.add(LecturaContador(
                equipo_id=equipo_id,
                lectura=lectura,
                usuario_id=session_usuario.usuario_id,
                observaciones=observaciones or "Lectura diaria"
            ))
            eq.lectura_actual = lectura
            session.commit()
            return True, f"Lectura registrada para {eq.codigo}: {lectura:.2f}"
        except Exception as e:
            session.rollback()
            return False, str(e)
        finally:
            session.close()

    @staticmethod
    def obtener_estado_planes_contador(uso_diario_default: float = 8.0) -> List[dict]:
        """
        Retorna el estado de planes por contador (hrs/km) con faltante y
        días estimados para mantenimiento.
        """
        session = get_session()
        try:
            planes = (session.query(PlanMantenimiento)
                      .options(joinedload(PlanMantenimiento.equipo))
                      .filter(
                          PlanMantenimiento.estado == "Activo",
                          PlanMantenimiento.criterio.in_(["Contador", "Ambos"])
                      )
                      .order_by(PlanMantenimiento.codigo.asc())
                      .all())
            res = []
            for p in planes:
                eq = p.equipo
                if not eq:
                    continue
                lectura_actual = float(eq.lectura_actual or 0)
                frecuencia = float(p.frecuencia or 0)
                if frecuencia <= 0:
                    continue
                ciclo_actual = int(lectura_actual // frecuencia)
                meta_siguiente = (ciclo_actual + 1) * frecuencia
                faltante = max(0.0, meta_siguiente - lectura_actual)
                uso_diario = max(0.1, float(uso_diario_default or 8.0))
                dias_estimados = faltante / uso_diario
                res.append({
                    "plan_id": p.id,
                    "codigo": p.codigo,
                    "equipo_id": eq.id,
                    "equipo": eq.nombre,
                    "tipo_contador": eq.tipo_contador or "Hra/Km",
                    "lectura_actual": lectura_actual,
                    "meta_siguiente": meta_siguiente,
                    "faltante": faltante,
                    "dias_estimados": dias_estimados,
                    "prioridad": p.prioridad,
                })
            return res
        finally:
            session.close()

    @staticmethod
    def obtener_planes_no_programados(fecha_desde: datetime, fecha_hasta: datetime) -> List[dict]:
        """
        Planes activos con próxima ejecución en rango que aún no tienen OT
        programada/liberada/en proceso para esa fecha.
        """
        session = get_session()
        try:
            planes = (session.query(PlanMantenimiento)
                      .options(joinedload(PlanMantenimiento.equipo))
                      .filter(
                          PlanMantenimiento.estado == "Activo",
                          PlanMantenimiento.proxima_ejecucion.isnot(None),
                          PlanMantenimiento.proxima_ejecucion >= fecha_desde,
                          PlanMantenimiento.proxima_ejecucion <= fecha_hasta
                      )
                      .order_by(PlanMantenimiento.proxima_ejecucion.asc())
                      .all())
            res = []
            for p in planes:
                existente = (session.query(OrdenTrabajo.id)
                             .filter(
                                 OrdenTrabajo.plan_id == p.id,
                                 OrdenTrabajo.estado.in_(["Programada", "Liberada", "En proceso"]),
                                 OrdenTrabajo.fecha_programada.isnot(None)
                             )
                             .order_by(OrdenTrabajo.fecha_programada.desc())
                             .first())
                if existente:
                    continue
                res.append({
                    "plan_id": p.id,
                    "codigo_plan": p.codigo,
                    "equipo": p.equipo.nombre if p.equipo else "-",
                    "tipo_ot": p.tipo_mantenimiento,
                    "fecha_programada": p.proxima_ejecucion,
                    "prioridad": p.prioridad,
                })
            return res
        finally:
            session.close()
