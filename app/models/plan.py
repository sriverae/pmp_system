"""
Modelos: PlanMantenimiento, ChecklistPlan, PlanMaterial.
"""
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, func, Text, Date
from sqlalchemy.orm import relationship
from app.models.base import Base


class PlanMantenimiento(Base):
    __tablename__ = "planes_mantenimiento"

    id = Column(Integer, primary_key=True, autoincrement=True)
    codigo = Column(String(50), unique=True, nullable=False)
    equipo_id = Column(Integer, ForeignKey("equipos.id"), nullable=False)
    descripcion = Column(String(300), nullable=False)
    tipo_mantenimiento = Column(String(50), nullable=False)
    # Tipos: Preventivo / Predictivo / Lubricación / Inspección / Overhaul
    frecuencia = Column(Float, nullable=False)
    unidad_frecuencia = Column(String(30), nullable=False)
    # Unidades: Días / Semanas / Meses / Horas / Kilómetros / Ciclos
    criterio = Column(String(20), default="Fecha")
    # Criterio: Fecha / Contador
    contador_asociado_id = Column(Integer, ForeignKey("lecturas_contador.id"), nullable=True)
    duracion_estimada = Column(Float, default=1.0)  # horas
    prioridad = Column(String(20), default="Normal")
    criticidad = Column(String(20), default="Media")
    responsable_id = Column(Integer, ForeignKey("trabajadores.id"), nullable=True)
    procedimiento = Column(Text, nullable=True)
    fecha_inicio = Column(Date, nullable=True)
    fecha_fin = Column(Date, nullable=True)
    ultima_ejecucion = Column(DateTime, nullable=True)
    proxima_ejecucion = Column(DateTime, nullable=True)
    estado = Column(String(30), default="Activo")
    # Estados: Activo / Pausado / Cerrado
    fecha_creacion = Column(DateTime, default=func.now())
    creado_por = Column(Integer, ForeignKey("usuarios.id"), nullable=True)

    equipo = relationship("Equipo", back_populates="planes")
    responsable = relationship("Trabajador", foreign_keys=[responsable_id])
    checklist = relationship("ChecklistPlan", back_populates="plan",
                             cascade="all, delete-orphan", order_by="ChecklistPlan.orden")
    materiales = relationship("PlanMaterial", back_populates="plan",
                              cascade="all, delete-orphan")
    ordenes = relationship("OrdenTrabajo", back_populates="plan")

    def calcular_proxima_ejecucion(self):
        """
        Recalcula la fecha/hora de próxima ejecución según criterio y frecuencia.
        Si criterio = Fecha, suma la frecuencia en la unidad indicada a la última ejecución.
        """
        from datetime import datetime, timedelta
        from dateutil.relativedelta import relativedelta

        base = self.ultima_ejecucion or datetime.now()
        freq = int(self.frecuencia)
        unidad = self.unidad_frecuencia.lower()

        if unidad == "días":
            return base + timedelta(days=freq)
        elif unidad == "semanas":
            return base + timedelta(weeks=freq)
        elif unidad == "meses":
            return base + relativedelta(months=freq)
        elif unidad == "años":
            return base + relativedelta(years=freq)
        else:
            # Para horas/kilómetros/ciclos, usar días como aproximación
            return base + timedelta(days=freq)

    def __repr__(self):
        return f"<Plan {self.codigo} - {self.descripcion}>"


class ChecklistPlan(Base):
    __tablename__ = "checklist_plan"

    id = Column(Integer, primary_key=True, autoincrement=True)
    plan_id = Column(Integer, ForeignKey("planes_mantenimiento.id"), nullable=False)
    orden = Column(Integer, default=0)
    descripcion = Column(String(300), nullable=False)
    obligatorio = Column(Boolean, default=False)

    plan = relationship("PlanMantenimiento", back_populates="checklist")

    def __repr__(self):
        return f"<Checklist {self.plan_id} #{self.orden}>"


class PlanMaterial(Base):
    __tablename__ = "plan_materiales"

    id = Column(Integer, primary_key=True, autoincrement=True)
    plan_id = Column(Integer, ForeignKey("planes_mantenimiento.id"), nullable=False)
    material_id = Column(Integer, ForeignKey("materiales.id"), nullable=False)
    cantidad_sugerida = Column(Float, default=1.0)

    plan = relationship("PlanMantenimiento", back_populates="materiales")
    material = relationship("Material")

    def __repr__(self):
        return f"<PlanMaterial plan={self.plan_id} mat={self.material_id}>"
