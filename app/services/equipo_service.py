"""
Servicio de Equipos.
"""
from typing import List, Optional, Tuple
from datetime import datetime

from app.core.database import get_session
from app.core.session import session_usuario
from app.models.equipo import Equipo, LecturaContador
from app.models.historial import HistorialEquipo
from app.models.orden_trabajo import OrdenTrabajo
from app.services.auditoria_service import AuditoriaService


class EquipoService:

    @staticmethod
    def listar(solo_activos: bool = False, area: str = None,
               criticidad: str = None, texto: str = None) -> List[Equipo]:
        session = get_session()
        try:
            q = session.query(Equipo)
            if solo_activos:
                q = q.filter(Equipo.estado == "Activo")
            if area:
                q = q.filter(Equipo.area == area)
            if criticidad:
                q = q.filter(Equipo.criticidad == criticidad)
            if texto:
                like = f"%{texto}%"
                q = q.filter(
                    (Equipo.codigo.ilike(like)) |
                    (Equipo.nombre.ilike(like)) |
                    (Equipo.descripcion.ilike(like))
                )
            return q.order_by(Equipo.codigo).all()
        finally:
            session.close()

    @staticmethod
    def obtener(equipo_id: int) -> Optional[Equipo]:
        session = get_session()
        try:
            return session.query(Equipo).get(equipo_id)
        finally:
            session.close()

    @staticmethod
    def crear(datos: dict) -> Tuple[bool, str, Optional[int]]:
        """Crea un nuevo equipo."""
        if not datos.get("codigo"):
            return False, "El código es obligatorio.", None
        if not datos.get("nombre"):
            return False, "El nombre es obligatorio.", None
        if not datos.get("criticidad"):
            return False, "La criticidad es obligatoria.", None

        session = get_session()
        try:
            # Código único
            existente = session.query(Equipo).filter_by(
                codigo=datos["codigo"]).first()
            if existente:
                return False, f"Ya existe un equipo con código '{datos['codigo']}'.", None

            # Serie única si se provee
            if datos.get("serie"):
                dup = session.query(Equipo).filter_by(serie=datos["serie"]).first()
                if dup:
                    return False, f"Ya existe un equipo con serie '{datos['serie']}'.", None

            equipo = Equipo(
                codigo=datos["codigo"],
                nombre=datos["nombre"],
                descripcion=datos.get("descripcion"),
                ubicacion=datos.get("ubicacion"),
                area=datos.get("area"),
                centro_costo=datos.get("centro_costo"),
                marca=datos.get("marca"),
                modelo=datos.get("modelo"),
                serie=datos.get("serie"),
                fabricante=datos.get("fabricante"),
                criticidad=datos["criticidad"],
                tipo_contador=datos.get("tipo_contador"),
                lectura_inicial=float(datos.get("lectura_inicial", 0)),
                lectura_actual=float(datos.get("lectura_inicial", 0)),
                estado="Activo",
                costo_reposicion=float(datos.get("costo_reposicion", 0)),
                observaciones=datos.get("observaciones")
            )
            session.add(equipo)
            session.flush()

            # Registrar en historial
            session.add(HistorialEquipo(
                equipo_id=equipo.id,
                tipo_evento="Alta",
                fecha=datetime.now(),
                descripcion=f"Equipo dado de alta. Código: {equipo.codigo}",
                usuario_id=session_usuario.usuario_id
            ))

            session.commit()
            AuditoriaService.registrar(
                "Equipos", "Crear equipo",
                tabla="equipos", registro_id=equipo.id,
                valor_nuevo={"codigo": equipo.codigo, "nombre": equipo.nombre}
            )
            return True, "Equipo creado exitosamente.", equipo.id

        except Exception as e:
            session.rollback()
            return False, str(e), None
        finally:
            session.close()

    @staticmethod
    def actualizar(equipo_id: int, datos: dict) -> Tuple[bool, str]:
        session = get_session()
        try:
            equipo = session.query(Equipo).get(equipo_id)
            if not equipo:
                return False, "Equipo no encontrado."

            # Verificar código único si cambia
            if datos.get("codigo") and datos["codigo"] != equipo.codigo:
                dup = session.query(Equipo).filter(
                    Equipo.codigo == datos["codigo"],
                    Equipo.id != equipo_id
                ).first()
                if dup:
                    return False, f"Código '{datos['codigo']}' ya está en uso."

            anterior = {"codigo": equipo.codigo, "nombre": equipo.nombre,
                        "estado": equipo.estado}

            campos = ["nombre", "descripcion", "ubicacion", "area", "centro_costo",
                      "marca", "modelo", "serie", "fabricante", "criticidad",
                      "tipo_contador", "costo_reposicion", "observaciones"]
            for campo in campos:
                if campo in datos:
                    setattr(equipo, campo, datos[campo])
            if "codigo" in datos:
                equipo.codigo = datos["codigo"]

            session.commit()
            AuditoriaService.registrar(
                "Equipos", "Editar equipo",
                tabla="equipos", registro_id=equipo_id,
                valor_anterior=anterior,
                valor_nuevo={"codigo": equipo.codigo, "nombre": equipo.nombre}
            )
            return True, "Equipo actualizado."
        except Exception as e:
            session.rollback()
            return False, str(e)
        finally:
            session.close()

    @staticmethod
    def dar_de_baja(equipo_id: int, motivo: str = "") -> Tuple[bool, str]:
        """
        Da de baja un equipo.
        RESTRICCIÓN: No dar de baja si tiene OTs en proceso.
        """
        session = get_session()
        try:
            equipo = session.query(Equipo).get(equipo_id)
            if not equipo:
                return False, "Equipo no encontrado."
            if equipo.estado == "Dado de baja":
                return False, "El equipo ya está dado de baja."

            # Verificar OTs activas
            ot_activa = session.query(OrdenTrabajo).filter(
                OrdenTrabajo.equipo_id == equipo_id,
                OrdenTrabajo.estado.in_(["En proceso", "Liberada"])
            ).first()
            if ot_activa:
                return (False,
                        f"No se puede dar de baja: el equipo tiene la OT "
                        f"{ot_activa.numero} en estado '{ot_activa.estado}'.")

            equipo.estado = "Dado de baja"
            session.add(HistorialEquipo(
                equipo_id=equipo_id,
                tipo_evento="Baja",
                fecha=datetime.now(),
                descripcion=f"Equipo dado de baja. Motivo: {motivo}",
                usuario_id=session_usuario.usuario_id
            ))
            session.commit()

            AuditoriaService.registrar(
                "Equipos", "Dar de baja equipo",
                tabla="equipos", registro_id=equipo_id,
                valor_anterior={"estado": "Activo"},
                valor_nuevo={"estado": "Dado de baja", "motivo": motivo}
            )
            return True, "Equipo dado de baja."
        except Exception as e:
            session.rollback()
            return False, str(e)
        finally:
            session.close()

    @staticmethod
    def reactivar(equipo_id: int) -> Tuple[bool, str]:
        session = get_session()
        try:
            equipo = session.query(Equipo).get(equipo_id)
            if not equipo:
                return False, "Equipo no encontrado."
            equipo.estado = "Activo"
            session.commit()
            AuditoriaService.registrar(
                "Equipos", "Reactivar equipo",
                tabla="equipos", registro_id=equipo_id
            )
            return True, "Equipo reactivado."
        except Exception as e:
            session.rollback()
            return False, str(e)
        finally:
            session.close()

    @staticmethod
    def registrar_lectura_contador(equipo_id: int, lectura: float,
                                    observaciones: str = "") -> Tuple[bool, str]:
        """Registra nueva lectura de contador y actualiza lectura_actual del equipo."""
        if lectura < 0:
            return False, "La lectura no puede ser negativa."

        session = get_session()
        try:
            equipo = session.query(Equipo).get(equipo_id)
            if not equipo:
                return False, "Equipo no encontrado."
            if lectura < equipo.lectura_actual:
                return (False,
                        f"La lectura ({lectura}) no puede ser menor a la actual "
                        f"({equipo.lectura_actual}).")

            equipo.lectura_actual = lectura
            session.add(LecturaContador(
                equipo_id=equipo_id,
                lectura=lectura,
                usuario_id=session_usuario.usuario_id,
                observaciones=observaciones
            ))
            session.commit()
            AuditoriaService.registrar(
                "Equipos", "Registrar lectura contador",
                tabla="lecturas_contador", registro_id=equipo_id,
                valor_nuevo={"lectura": lectura}
            )
            return True, f"Lectura {lectura} registrada."
        except Exception as e:
            session.rollback()
            return False, str(e)
        finally:
            session.close()
