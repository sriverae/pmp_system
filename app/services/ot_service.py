"""
Servicio de Órdenes de Trabajo.
Toda la lógica de negocio de OTs: crear, liberar, iniciar, cerrar, anular.
"""
from datetime import datetime
from typing import List, Optional, Tuple
from sqlalchemy.orm import joinedload

from app.core.database import get_session
from app.core.session import session_usuario
from app.models.orden_trabajo import (
    OrdenTrabajo, OTTecnico, OTMaterialPrevisto, OTMaterialConsumido
)
from app.models.material import Material, MovimientoMaterial
from app.models.historial import HistorialEquipo
from app.validators.ot_validator import OTValidator, ResultadoValidacion
from app.services.auditoria_service import AuditoriaService


class OTService:

    @staticmethod
    def generar_numero_ot() -> str:
        """Genera número único de OT: OT-YYYYMMDD-NNNN."""
        session = get_session()
        try:
            hoy = datetime.now().strftime("%Y%m%d")
            prefijo = f"OT-{hoy}-"
            ultimo = (session.query(OrdenTrabajo)
                      .filter(OrdenTrabajo.numero.like(f"{prefijo}%"))
                      .order_by(OrdenTrabajo.numero.desc())
                      .first())
            if ultimo:
                secuencia = int(ultimo.numero.split("-")[-1]) + 1
            else:
                secuencia = 1
            return f"{prefijo}{secuencia:04d}"
        finally:
            session.close()

    @staticmethod
    def crear_ot(datos: dict, tecnico_ids: List[int],
                  materiales_previstos: List[dict]) -> Tuple[bool, str, Optional[int]]:
        """
        Crea una OT en estado Borrador.
        Retorna (éxito, mensaje, ot_id).
        """
        rv = OTValidator.validar_campos_basicos(datos)
        if not rv.valido:
            return False, rv.texto_errores(), None

        session = get_session()
        try:
            numero = OTService.generar_numero_ot()
            ot = OrdenTrabajo(
                numero=numero,
                tipo_ot=datos["tipo_ot"],
                equipo_id=datos["equipo_id"],
                plan_id=datos.get("plan_id"),
                prioridad=datos.get("prioridad", "Normal"),
                criticidad=datos.get("criticidad", "Media"),
                estado="Borrador",
                fecha_programada=datos.get("fecha_programada"),
                hora_inicio_prog=datos.get("hora_inicio_prog"),
                hora_fin_prog=datos.get("hora_fin_prog"),
                duracion_estimada=datos.get("duracion_estimada", 1.0),
                responsable_id=datos.get("responsable_id"),
                descripcion_trabajo=datos.get("descripcion_trabajo"),
                procedimiento=datos.get("procedimiento"),
                observaciones=datos.get("observaciones"),
                creado_por=session_usuario.usuario_id
            )
            session.add(ot)
            session.flush()

            # Agregar técnicos
            for tid in tecnico_ids:
                session.add(OTTecnico(ot_id=ot.id, trabajador_id=tid))

            # Agregar materiales previstos
            for mp in materiales_previstos:
                session.add(OTMaterialPrevisto(
                    ot_id=ot.id,
                    material_id=mp["material_id"],
                    cantidad_prevista=mp.get("cantidad", 1.0),
                    obligatorio=mp.get("obligatorio", False)
                ))

            session.commit()

            AuditoriaService.registrar(
                "OT", "Crear OT",
                tabla="ordenes_trabajo", registro_id=ot.id,
                valor_nuevo={"numero": numero, "equipo_id": datos["equipo_id"]}
            )
            return True, f"OT {numero} creada exitosamente.", ot.id

        except Exception as e:
            session.rollback()
            return False, f"Error al crear OT: {str(e)}", None
        finally:
            session.close()

    @staticmethod
    def liberar_ot(ot_id: int, autorizar_stock: bool = False) -> Tuple[bool, str]:
        """
        Libera la OT luego de pasar todas las validaciones.
        Cambia estado a 'Liberada'.
        """
        session = get_session()
        try:
            ot = session.query(OrdenTrabajo).get(ot_id)
            if not ot:
                return False, "OT no encontrada."
            if ot.estado not in ("Borrador", "Programada"):
                return False, f"No se puede liberar una OT en estado '{ot.estado}'."

            tecnico_ids = [t.trabajador_id for t in ot.tecnicos]
            mat_prevs = [
                {"material_id": m.material_id,
                 "cantidad": m.cantidad_prevista,
                 "obligatorio": m.obligatorio}
                for m in ot.materiales_previstos
            ]

            rv = OTValidator.validar_para_liberar(
                ot_id, tecnico_ids, mat_prevs, autorizar_stock
            )
            if not rv.valido:
                return False, rv.texto_errores()

            estado_anterior = ot.estado
            ot.estado = "Liberada"
            ot.fecha_liberacion = datetime.now()
            session.commit()

            AuditoriaService.registrar(
                "OT", "Liberar OT",
                tabla="ordenes_trabajo", registro_id=ot_id,
                valor_anterior={"estado": estado_anterior},
                valor_nuevo={"estado": "Liberada"}
            )
            return True, f"OT {ot.numero} liberada exitosamente."

        except Exception as e:
            session.rollback()
            return False, f"Error al liberar OT: {str(e)}"
        finally:
            session.close()

    @staticmethod
    def iniciar_ot(ot_id: int) -> Tuple[bool, str]:
        """Pasa la OT a estado 'En proceso' y registra la hora real de inicio."""
        session = get_session()
        try:
            ot = session.query(OrdenTrabajo).get(ot_id)
            if not ot:
                return False, "OT no encontrada."
            if ot.estado != "Liberada":
                return False, "Solo se puede iniciar una OT en estado 'Liberada'."

            ot.estado = "En proceso"
            ot.fecha_real_inicio = datetime.now()
            session.commit()

            AuditoriaService.registrar("OT", "Iniciar OT",
                                        tabla="ordenes_trabajo", registro_id=ot_id)
            return True, f"OT {ot.numero} iniciada."
        except Exception as e:
            session.rollback()
            return False, str(e)
        finally:
            session.close()

    @staticmethod
    def cerrar_ot(ot_id: int, datos_cierre: dict,
                   consumos: List[dict]) -> Tuple[bool, str]:
        """
        Cierra la OT, registra consumos reales de materiales,
        actualiza historial del equipo y recalcula costos.
        """
        rv = OTValidator.validar_cierre(datos_cierre)
        if not rv.valido:
            return False, rv.texto_errores()

        session = get_session()
        try:
            ot = session.query(OrdenTrabajo).get(ot_id)
            if not ot:
                return False, "OT no encontrada."
            if ot.estado not in ("Liberada", "En proceso"):
                return False, f"No se puede cerrar una OT en estado '{ot.estado}'."

            # Registrar consumos de materiales
            costo_materiales = 0.0
            for cons in consumos:
                mat = session.query(Material).get(cons["material_id"])
                if not mat:
                    continue
                cant = float(cons.get("cantidad", 0))
                if cant <= 0:
                    continue

                # Descontar stock
                stock_ant = mat.stock_actual
                mat.stock_actual -= cant
                costo_linea = cant * mat.costo_unitario
                costo_materiales += costo_linea

                # Registrar movimiento
                session.add(MovimientoMaterial(
                    material_id=mat.id,
                    tipo_movimiento="Consumo OT",
                    cantidad=cant,
                    costo_unitario=mat.costo_unitario,
                    ot_id=ot_id,
                    motivo=f"Consumo OT {ot.numero}",
                    usuario_id=session_usuario.usuario_id,
                    stock_anterior=stock_ant,
                    stock_posterior=mat.stock_actual
                ))

                # Agregar a consumidos de OT
                session.add(OTMaterialConsumido(
                    ot_id=ot_id,
                    material_id=mat.id,
                    cantidad_consumida=cant,
                    costo_unitario=mat.costo_unitario,
                    costo_total_linea=costo_linea
                ))

            # Calcular costo mano de obra
            costo_mo = float(datos_cierre.get("costo_mano_obra", 0))

            # Actualizar OT
            ot.fecha_real_inicio = datos_cierre.get("fecha_real_inicio") or ot.fecha_real_inicio
            ot.fecha_real_fin = datos_cierre["fecha_real_fin"]
            ot.horas_hombre_real = float(datos_cierre.get("horas_hombre_real", 0))
            ot.actividades_realizadas = datos_cierre.get("actividades_realizadas", "")
            ot.causa_falla = datos_cierre.get("causa_falla")
            ot.accion_correctiva = datos_cierre.get("accion_correctiva")
            ot.condicion_final_equipo = datos_cierre.get("condicion_final_equipo")
            ot.costo_mano_obra = costo_mo
            ot.costo_materiales = costo_materiales
            ot.costo_otros = float(datos_cierre.get("costo_otros", 0))
            ot.costo_total = costo_mo + costo_materiales + ot.costo_otros
            ot.tiempo_fuera_servicio = float(datos_cierre.get("tiempo_fuera_servicio", 0))
            ot.estado = "Cerrada"
            ot.fecha_cierre = datetime.now()
            ot.cerrado_por = session_usuario.usuario_id

            # Registrar en historial del equipo
            tipo_hist = ("Mantenimiento preventivo"
                         if ot.tipo_ot == "Preventivo" else "Mantenimiento correctivo")
            session.add(HistorialEquipo(
                equipo_id=ot.equipo_id,
                ot_id=ot_id,
                tipo_evento=tipo_hist,
                fecha=ot.fecha_real_fin,
                descripcion=ot.actividades_realizadas,
                costo=ot.costo_total,
                tiempo_fuera_servicio=ot.tiempo_fuera_servicio,
                usuario_id=session_usuario.usuario_id
            ))

            session.commit()

            AuditoriaService.registrar(
                "OT", "Cerrar OT",
                tabla="ordenes_trabajo", registro_id=ot_id,
                valor_nuevo={"estado": "Cerrada", "costo_total": ot.costo_total}
            )
            return True, f"OT {ot.numero} cerrada. Costo total: {ot.costo_total:.2f}"

        except Exception as e:
            session.rollback()
            return False, f"Error al cerrar OT: {str(e)}"
        finally:
            session.close()

    @staticmethod
    def anular_ot(ot_id: int, motivo: str) -> Tuple[bool, str]:
        """Anula una OT. Mantiene trazabilidad. No afecta KPIs."""
        if not motivo or not motivo.strip():
            return False, "El motivo de anulación es obligatorio."

        session = get_session()
        try:
            ot = session.query(OrdenTrabajo).get(ot_id)
            if not ot:
                return False, "OT no encontrada."
            if ot.estado == "Cerrada":
                return False, "No se puede anular una OT cerrada."
            if ot.estado == "Anulada":
                return False, "La OT ya está anulada."

            estado_ant = ot.estado
            ot.estado = "Anulada"
            ot.motivo_anulacion = motivo
            session.commit()

            AuditoriaService.registrar(
                "OT", "Anular OT",
                tabla="ordenes_trabajo", registro_id=ot_id,
                valor_anterior={"estado": estado_ant},
                valor_nuevo={"estado": "Anulada", "motivo": motivo}
            )
            return True, f"OT {ot.numero} anulada."
        except Exception as e:
            session.rollback()
            return False, str(e)
        finally:
            session.close()

    @staticmethod
    def reprogramar_ot(ot_id: int, nueva_fecha: datetime,
                        nueva_hora_ini: str, nueva_hora_fin: str,
                        motivo: str) -> Tuple[bool, str]:
        """Reprograma una OT, guarda fecha anterior y motivo."""
        if not motivo:
            return False, "El motivo de reprogramación es obligatorio."

        session = get_session()
        try:
            ot = session.query(OrdenTrabajo).get(ot_id)
            if not ot:
                return False, "OT no encontrada."
            if ot.estado not in ("Borrador", "Programada", "Liberada"):
                return False, f"No se puede reprogramar una OT en estado '{ot.estado}'."

            ot.fecha_anterior_reprog = ot.fecha_programada
            ot.fecha_programada = nueva_fecha
            ot.hora_inicio_prog = nueva_hora_ini
            ot.hora_fin_prog = nueva_hora_fin
            ot.motivo_reprogramacion = motivo
            session.commit()

            AuditoriaService.registrar(
                "OT", "Reprogramar OT",
                tabla="ordenes_trabajo", registro_id=ot_id,
                valor_anterior={"fecha": str(ot.fecha_anterior_reprog)},
                valor_nuevo={"fecha": str(nueva_fecha), "motivo": motivo}
            )
            return True, f"OT {ot.numero} reprogramada."
        except Exception as e:
            session.rollback()
            return False, str(e)
        finally:
            session.close()

    @staticmethod
    def listar_ots(filtros: dict = None) -> List[OrdenTrabajo]:
        """Lista OTs con filtros opcionales."""
        session = get_session()
        try:
            q = (session.query(OrdenTrabajo)
                 .options(
                     joinedload(OrdenTrabajo.equipo),
                     joinedload(OrdenTrabajo.responsable),
                 ))
            if filtros:
                if filtros.get("estado"):
                    q = q.filter(OrdenTrabajo.estado == filtros["estado"])
                if filtros.get("equipo_id"):
                    q = q.filter(OrdenTrabajo.equipo_id == filtros["equipo_id"])
                if filtros.get("tipo_ot"):
                    q = q.filter(OrdenTrabajo.tipo_ot == filtros["tipo_ot"])
                if filtros.get("fecha_desde"):
                    q = q.filter(OrdenTrabajo.fecha_programada >= filtros["fecha_desde"])
                if filtros.get("fecha_hasta"):
                    q = q.filter(OrdenTrabajo.fecha_programada <= filtros["fecha_hasta"])
                if filtros.get("prioridad"):
                    q = q.filter(OrdenTrabajo.prioridad == filtros["prioridad"])
            return q.order_by(OrdenTrabajo.fecha_programada.desc()).all()
        finally:
            session.close()
