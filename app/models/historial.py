"""
Modelo: HistorialEquipo — Registro histórico de eventos por equipo.
"""
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, func, Text
from sqlalchemy.orm import relationship
from app.models.base import Base


class HistorialEquipo(Base):
    __tablename__ = "historial_equipos"

    id = Column(Integer, primary_key=True, autoincrement=True)
    equipo_id = Column(Integer, ForeignKey("equipos.id"), nullable=False)
    ot_id = Column(Integer, ForeignKey("ordenes_trabajo.id"), nullable=True)
    tipo_evento = Column(String(80), nullable=False)
    # Tipos: Mantenimiento preventivo / Mantenimiento correctivo /
    #        Falla / Alta / Baja / Cambio estado / Lectura contador
    fecha = Column(DateTime, default=func.now())
    descripcion = Column(Text, nullable=True)
    costo = Column(Float, default=0.0)
    tiempo_fuera_servicio = Column(Float, default=0.0)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"), nullable=True)

    equipo = relationship("Equipo", back_populates="historial")
    ot = relationship("OrdenTrabajo", back_populates="historial_entries")

    def __repr__(self):
        return f"<Historial equipo={self.equipo_id} {self.tipo_evento}>"
