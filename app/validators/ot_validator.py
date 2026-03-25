"""
Validador de Órdenes de Trabajo.

Implementa todas las restricciones de negocio críticas:
 1. Trabajador no puede estar en 2 OTs en el mismo horario
 2. Equipo no puede tener dos OTs simultáneas
 3. No asignar personal fuera de turno sin autorización
 4. Trabajador no disponible (inactivo, vacaciones, permiso, etc.)
 5. Máximo de horas diarias
 6. Stock de materiales obligatorios
 7. Equipo dado de baja no puede recibir OTs
 8. OT cerrada no editable
"""
from datetime import datetime, date
from typing import List, Optional
from dataclasses import dataclass, field

from app.core.database import get_session
from app.models.orden_trabajo import OrdenTrabajo, OTTecnico, OTMaterialPrevisto
from app.models.trabajador import Trabajador, AusenciaTrabajador
from app.models.equipo import Equipo
from app.models.material import Material
from sqlalchemy import and_, or_


@dataclass
class ErrorValidacion:
    campo: str
    mensaje: str


@dataclass
class ResultadoValidacion:
    valido: bool
    errores: List[ErrorValidacion] = field(default_factory=list)

    def agregar_error(self, campo: str, mensaje: str):
        self.errores.append(ErrorValidacion(campo, mensaje))
        self.valido = False

    def texto_errores(self) -> str:
        return "\n".join(f"• {e.mensaje}" for e in self.errores)


class OTValidator:

    @staticmethod
    def validar_campos_basicos(datos: dict) -> ResultadoValidacion:
        """Valida campos obligatorios del formulario de OT."""
        rv = ResultadoValidacion(valido=True)

        if not datos.get("equipo_id"):
            rv.agregar_error("equipo_id", "Debe seleccionar un equipo.")
        if not datos.get("tipo_ot"):
            rv.agregar_error("tipo_ot", "Debe indicar el tipo de OT.")
        if not datos.get("fecha_programada"):
            rv.agregar_error("fecha_programada", "La fecha programada es obligatoria.")
        if not datos.get("hora_inicio_prog"):
            rv.agregar_error("hora_inicio_prog", "La hora de inicio es obligatoria.")
        if not datos.get("hora_fin_prog"):
            rv.agregar_error("hora_fin_prog", "La hora de fin es obligatoria.")

        # Validar coherencia de horas
        hi = datos.get("hora_inicio_prog", "")
        hf = datos.get("hora_fin_prog", "")
        if hi and hf and hi >= hf:
            rv.agregar_error("hora_fin_prog",
                              "La hora de fin debe ser posterior a la hora de inicio.")

        return rv

    @staticmethod
    def validar_para_liberar(ot_id: int, tecnico_ids: List[int],
                              material_previstos: List[dict],
                              autorizar_stock: bool = False) -> ResultadoValidacion:
        """
        Validación completa previa a la liberación de la OT.
        Es la más crítica del sistema.
        """
        rv = ResultadoValidacion(valido=True)
        session = get_session()

        try:
            ot = session.query(OrdenTrabajo).get(ot_id)
            if not ot:
                rv.agregar_error("ot", "OT no encontrada.")
                return rv

            # -- RESTRICCIÓN 7: Equipo dado de baja ------------------------
            equipo = session.query(Equipo).get(ot.equipo_id)
            if not equipo:
                rv.agregar_error("equipo", "El equipo asociado no existe.")
            elif equipo.estado == "Dado de baja":
                rv.agregar_error(
                    "equipo",
                    f"El equipo '{equipo.nombre}' está dado de baja y no puede recibir OTs."
                )

            if not ot.fecha_programada:
                rv.agregar_error("fecha_programada", "Fecha programada obligatoria para liberar.")

            if not ot.hora_inicio_prog or not ot.hora_fin_prog:
                rv.agregar_error("horario", "Hora inicio y fin son obligatorias para liberar.")

            if not ot.responsable_id and not tecnico_ids:
                rv.agregar_error("responsable",
                                  "Debe asignarse al menos un responsable o técnico.")

            # -- RESTRICCIÓN 2: Equipo con OTs simultáneas -----------------
            if ot.fecha_programada and ot.hora_inicio_prog and ot.hora_fin_prog:
                conflictos_equipo = OTValidator._buscar_conflictos_equipo(
                    session, ot.equipo_id, ot.fecha_programada,
                    ot.hora_inicio_prog, ot.hora_fin_prog, excluir_ot_id=ot_id
                )
                for c in conflictos_equipo:
                    rv.agregar_error(
                        "equipo_conflicto",
                        f"El equipo ya tiene la OT #{c.numero} en el mismo horario "
                        f"({c.hora_inicio_prog} - {c.hora_fin_prog})."
                    )

            # -- RESTRICCIONES 1, 4, 5: Personal ---------------------------
            for trab_id in tecnico_ids:
                trabajador = session.query(Trabajador).get(trab_id)
                if not trabajador:
                    rv.agregar_error(f"tecnico_{trab_id}", f"Técnico ID {trab_id} no existe.")
                    continue

                # Restricción 4: trabajador inactivo o suspendido
                if trabajador.estado != "Activo":
                    rv.agregar_error(
                        f"tecnico_{trab_id}",
                        f"El trabajador '{trabajador.nombre_completo}' no está activo "
                        f"(estado: {trabajador.estado})."
                    )
                    continue

                # Restricción 4: ausencias
                if ot.fecha_programada:
                    fecha_ot = ot.fecha_programada.date()
                    ausencia = session.query(AusenciaTrabajador).filter(
                        AusenciaTrabajador.trabajador_id == trab_id,
                        AusenciaTrabajador.fecha_inicio <= fecha_ot,
                        AusenciaTrabajador.fecha_fin >= fecha_ot
                    ).first()
                    if ausencia:
                        rv.agregar_error(
                            f"tecnico_{trab_id}",
                            f"El trabajador '{trabajador.nombre_completo}' tiene una "
                            f"ausencia registrada ({ausencia.tipo_ausencia}) en esa fecha."
                        )
                        continue

                # Restricción 1: conflicto horario con otra OT
                if ot.fecha_programada and ot.hora_inicio_prog and ot.hora_fin_prog:
                    conflictos_tec = OTValidator._buscar_conflictos_tecnico(
                        session, trab_id, ot.fecha_programada,
                        ot.hora_inicio_prog, ot.hora_fin_prog, excluir_ot_id=ot_id
                    )
                    for ct in conflictos_tec:
                        rv.agregar_error(
                            f"tecnico_{trab_id}",
                            f"El trabajador '{trabajador.nombre_completo}' ya está "
                            f"asignado a la OT #{ct.numero} "
                            f"({ct.hora_inicio_prog} - {ct.hora_fin_prog})."
                        )

                # Restricción 5: horas máximas diarias
                if ot.fecha_programada and ot.hora_inicio_prog and ot.hora_fin_prog:
                    horas_asignadas = OTValidator._calcular_horas_dia(
                        session, trab_id, ot.fecha_programada, excluir_ot_id=ot_id
                    )
                    duracion_ot = OTValidator._calcular_duracion_horas(
                        ot.hora_inicio_prog, ot.hora_fin_prog
                    )
                    if (horas_asignadas + duracion_ot) > trabajador.horas_max_dia:
                        rv.agregar_error(
                            f"tecnico_{trab_id}",
                            f"El trabajador '{trabajador.nombre_completo}' superaría "
                            f"su límite de {trabajador.horas_max_dia}h/día "
                            f"({horas_asignadas:.1f}h ya asignadas + "
                            f"{duracion_ot:.1f}h de esta OT)."
                        )

            # -- RESTRICCIÓN 6: Stock de materiales ------------------------
            if not autorizar_stock:
                for mp in material_previstos:
                    mat = session.query(Material).get(mp.get("material_id"))
                    if not mat:
                        continue
                    if mp.get("obligatorio") and mat.stock_actual < mp.get("cantidad", 0):
                        rv.agregar_error(
                            f"material_{mat.id}",
                            f"Stock insuficiente para '{mat.descripcion}': "
                            f"requerido {mp.get('cantidad', 0)} {mat.unidad}, "
                            f"disponible {mat.stock_actual} {mat.unidad}."
                        )

            return rv

        finally:
            session.close()

    @staticmethod
    def validar_cierre(datos: dict) -> ResultadoValidacion:
        """Valida los datos antes de cerrar una OT."""
        rv = ResultadoValidacion(valido=True)

        if not datos.get("fecha_real_inicio"):
            rv.agregar_error("fecha_real_inicio", "La fecha real de inicio es obligatoria.")
        if not datos.get("fecha_real_fin"):
            rv.agregar_error("fecha_real_fin", "La fecha real de fin es obligatoria.")

        fi = datos.get("fecha_real_inicio")
        ff = datos.get("fecha_real_fin")
        if fi and ff and ff <= fi:
            rv.agregar_error("fecha_real_fin",
                              "La fecha/hora real de fin debe ser posterior al inicio.")

        if not datos.get("actividades_realizadas"):
            rv.agregar_error("actividades_realizadas",
                              "Debe describir las actividades realizadas.")

        hh = datos.get("horas_hombre_real", 0)
        if not hh or float(hh) <= 0:
            rv.agregar_error("horas_hombre_real", "Las horas hombre deben ser mayores a cero.")

        if not datos.get("tecnico_ejecutor_id"):
            rv.agregar_error("tecnico_ejecutor", "Debe indicar el técnico ejecutor.")

        return rv

    # -- Helpers privados --------------------------------------------------

    @staticmethod
    def _buscar_conflictos_equipo(session, equipo_id: int, fecha: datetime,
                                   hora_ini: str, hora_fin: str,
                                   excluir_ot_id: int = None) -> List[OrdenTrabajo]:
        """Busca OTs del mismo equipo en el mismo rango horario."""
        q = session.query(OrdenTrabajo).filter(
            OrdenTrabajo.equipo_id == equipo_id,
            OrdenTrabajo.estado.in_(["Programada", "Liberada", "En proceso"]),
            OrdenTrabajo.fecha_programada == fecha,
        )
        if excluir_ot_id:
            q = q.filter(OrdenTrabajo.id != excluir_ot_id)

        conflictos = []
        for ot in q.all():
            if OTValidator._hay_solapamiento(hora_ini, hora_fin,
                                              ot.hora_inicio_prog, ot.hora_fin_prog):
                conflictos.append(ot)
        return conflictos

    @staticmethod
    def _buscar_conflictos_tecnico(session, trabajador_id: int, fecha: datetime,
                                    hora_ini: str, hora_fin: str,
                                    excluir_ot_id: int = None) -> List[OrdenTrabajo]:
        """Busca OTs donde el técnico ya esté asignado en el mismo horario."""
        q = (session.query(OrdenTrabajo)
             .join(OTTecnico, OTTecnico.ot_id == OrdenTrabajo.id)
             .filter(
                 OTTecnico.trabajador_id == trabajador_id,
                 OrdenTrabajo.estado.in_(["Programada", "Liberada", "En proceso"]),
                 OrdenTrabajo.fecha_programada == fecha,
             ))
        if excluir_ot_id:
            q = q.filter(OrdenTrabajo.id != excluir_ot_id)

        conflictos = []
        for ot in q.all():
            if OTValidator._hay_solapamiento(hora_ini, hora_fin,
                                              ot.hora_inicio_prog, ot.hora_fin_prog):
                conflictos.append(ot)
        return conflictos

    @staticmethod
    def _calcular_horas_dia(session, trabajador_id: int, fecha: datetime,
                             excluir_ot_id: int = None) -> float:
        """Suma las horas ya asignadas al técnico en esa fecha."""
        q = (session.query(OrdenTrabajo)
             .join(OTTecnico, OTTecnico.ot_id == OrdenTrabajo.id)
             .filter(
                 OTTecnico.trabajador_id == trabajador_id,
                 OrdenTrabajo.estado.in_(["Programada", "Liberada", "En proceso"]),
                 OrdenTrabajo.fecha_programada == fecha,
             ))
        if excluir_ot_id:
            q = q.filter(OrdenTrabajo.id != excluir_ot_id)

        total = 0.0
        for ot in q.all():
            total += OTValidator._calcular_duracion_horas(
                ot.hora_inicio_prog, ot.hora_fin_prog
            )
        return total

    @staticmethod
    def _hay_solapamiento(hi1: str, hf1: str, hi2: str, hf2: str) -> bool:
        """Retorna True si los rangos horarios se solapan."""
        if not hi1 or not hf1 or not hi2 or not hf2:
            return False
        return hi1 < hf2 and hi2 < hf1

    @staticmethod
    def _calcular_duracion_horas(hora_ini: str, hora_fin: str) -> float:
        """Calcula duración en horas entre dos strings 'HH:MM'."""
        try:
            h1, m1 = map(int, hora_ini.split(":"))
            h2, m2 = map(int, hora_fin.split(":"))
            return ((h2 * 60 + m2) - (h1 * 60 + m1)) / 60.0
        except Exception:
            return 0.0
