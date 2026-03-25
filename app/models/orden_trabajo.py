"""
Modelos: OrdenTrabajo, OTTecnico, OTMaterialPrevisto, OTMaterialConsumido.
"""
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, func, Text, Time
from sqlalchemy.orm import relationship
from app.models.base import Base


class OrdenTrabajo(Base):
    __tablename__ = "ordenes_trabajo"

    id = Column(Integer, primary_key=True, autoincrement=True)
    numero = Column(String(30), unique=True, nullable=False)
    tipo_ot = Column(String(50), nullable=False)
    # Tipos: Preventivo / Correctivo / Inspección / Predictivo / Emergencia / Mejora
    equipo_id = Column(Integer, ForeignKey("equipos.id"), nullable=False)
    plan_id = Column(Integer, ForeignKey("planes_mantenimiento.id"), nullable=True)
    prioridad = Column(String(20), default="Normal")
    # Prioridad: Urgente / Alta / Normal / Baja
    criticidad = Column(String(20), default="Media")
    estado = Column(String(30), default="Borrador")
    # Estados: Borrador / Programada / Liberada / En proceso / Cerrada / Anulada

    # Programación
    fecha_programada = Column(DateTime, nullable=True)
    hora_inicio_prog = Column(String(8), nullable=True)  # "HH:MM"
    hora_fin_prog = Column(String(8), nullable=True)     # "HH:MM"
    duracion_estimada = Column(Float, default=1.0)        # horas

    # Responsable y personal
    responsable_id = Column(Integer, ForeignKey("trabajadores.id"), nullable=True)

    # Descripción
    descripcion_trabajo = Column(Text, nullable=True)
    procedimiento = Column(Text, nullable=True)
    observaciones = Column(Text, nullable=True)

    # Ejecución real
    fecha_real_inicio = Column(DateTime, nullable=True)
    fecha_real_fin = Column(DateTime, nullable=True)
    horas_hombre_real = Column(Float, default=0.0)
    actividades_realizadas = Column(Text, nullable=True)
    causa_falla = Column(String(300), nullable=True)
    accion_correctiva = Column(Text, nullable=True)
    condicion_final_equipo = Column(String(100), nullable=True)

    # Costos
    costo_mano_obra = Column(Float, default=0.0)
    costo_materiales = Column(Float, default=0.0)
    costo_otros = Column(Float, default=0.0)
    costo_total = Column(Float, default=0.0)
    tiempo_fuera_servicio = Column(Float, default=0.0)  # horas

    # Control
    motivo_reprogramacion = Column(Text, nullable=True)
    fecha_anterior_reprog = Column(DateTime, nullable=True)
    motivo_anulacion = Column(String(300), nullable=True)
    fecha_liberacion = Column(DateTime, nullable=True)
    fecha_cierre = Column(DateTime, nullable=True)
    creado_por = Column(Integer, ForeignKey("usuarios.id"), nullable=True)
    cerrado_por = Column(Integer, ForeignKey("usuarios.id"), nullable=True)
    fecha_creacion = Column(DateTime, default=func.now())

    # Relaciones
    equipo = relationship("Equipo", back_populates="ordenes")
    plan = relationship("PlanMantenimiento", back_populates="ordenes")
    responsable = relationship("Trabajador", foreign_keys=[responsable_id])
    tecnicos = relationship("OTTecnico", back_populates="ot",
                            cascade="all, delete-orphan")
    materiales_previstos = relationship("OTMaterialPrevisto", back_populates="ot",
                                        cascade="all, delete-orphan")
    materiales_consumidos = relationship("OTMaterialConsumido", back_populates="ot",
                                         cascade="all, delete-orphan")
    historial_entries = relationship("HistorialEquipo", back_populates="ot")

    def calcular_costo_total(self):
        """Recalcula y actualiza costo_total."""
        self.costo_total = (
            (self.costo_mano_obra or 0.0)
            + (self.costo_materiales or 0.0)
            + (self.costo_otros or 0.0)
        )
        return self.costo_total

    def es_editable(self) -> bool:
        """Solo se puede editar en estados no finales."""
        return self.estado in ("Borrador", "Programada")

    def __repr__(self):
        return f"<OT {self.numero} [{self.estado}]>"


class OTTecnico(Base):
    __tablename__ = "ot_tecnicos"

    id = Column(Integer, primary_key=True, autoincrement=True)
    ot_id = Column(Integer, ForeignKey("ordenes_trabajo.id"), nullable=False)
    trabajador_id = Column(Integer, ForeignKey("trabajadores.id"), nullable=False)
    rol = Column(String(80), default="Técnico ejecutor")
    horas_asignadas = Column(Float, default=0.0)

    ot = relationship("OrdenTrabajo", back_populates="tecnicos")
    trabajador = relationship("Trabajador")

    def __repr__(self):
        return f"<OTTecnico ot={self.ot_id} trab={self.trabajador_id}>"


class OTMaterialPrevisto(Base):
    __tablename__ = "ot_materiales_previstos"

    id = Column(Integer, primary_key=True, autoincrement=True)
    ot_id = Column(Integer, ForeignKey("ordenes_trabajo.id"), nullable=False)
    material_id = Column(Integer, ForeignKey("materiales.id"), nullable=False)
    cantidad_prevista = Column(Float, nullable=False, default=1.0)
    obligatorio = Column(Boolean, default=False)

    ot = relationship("OrdenTrabajo", back_populates="materiales_previstos")
    material = relationship("Material")

    def __repr__(self):
        return f"<OTMatPrev ot={self.ot_id} mat={self.material_id}>"


class OTMaterialConsumido(Base):
    __tablename__ = "ot_materiales_consumidos"

    id = Column(Integer, primary_key=True, autoincrement=True)
    ot_id = Column(Integer, ForeignKey("ordenes_trabajo.id"), nullable=False)
    material_id = Column(Integer, ForeignKey("materiales.id"), nullable=False)
    cantidad_consumida = Column(Float, nullable=False, default=1.0)
    costo_unitario = Column(Float, default=0.0)
    costo_total_linea = Column(Float, default=0.0)

    ot = relationship("OrdenTrabajo", back_populates="materiales_consumidos")
    material = relationship("Material")

    def __repr__(self):
        return f"<OTMatCons ot={self.ot_id} mat={self.material_id}>"
