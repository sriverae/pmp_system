"""
Modelos: Trabajador, AusenciaTrabajador.
"""
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, func, Date
from sqlalchemy.orm import relationship
from app.models.base import Base


class Trabajador(Base):
    __tablename__ = "trabajadores"

    id = Column(Integer, primary_key=True, autoincrement=True)
    codigo = Column(String(50), unique=True, nullable=False)
    nombres = Column(String(150), nullable=False)
    apellidos = Column(String(150), nullable=False)
    dni = Column(String(20), unique=True, nullable=True)
    cargo = Column(String(150), nullable=True)
    especialidad = Column(String(150), nullable=True)
    turno = Column(String(50), nullable=True)
    empresa = Column(String(200), nullable=True)
    horas_max_dia = Column(Float, default=8.0)
    tarifa_hora = Column(Float, default=0.0)
    estado = Column(String(30), default="Activo")
    # Estados: Activo / Inactivo / Suspendido
    observaciones = Column(String(500), nullable=True)
    fecha_ingreso = Column(Date, nullable=True)
    fecha_creacion = Column(DateTime, default=func.now())

    ausencias = relationship("AusenciaTrabajador", back_populates="trabajador",
                             cascade="all, delete-orphan")

    @property
    def nombre_completo(self):
        return f"{self.nombres} {self.apellidos}"

    def tiene_ausencia_en(self, fecha_inicio, fecha_fin) -> bool:
        """Verifica si el trabajador tiene ausencia registrada en el rango dado."""
        for aus in self.ausencias:
            if aus.fecha_inicio <= fecha_fin and aus.fecha_fin >= fecha_inicio:
                return True
        return False

    def __repr__(self):
        return f"<Trabajador {self.codigo} - {self.nombre_completo}>"


class AusenciaTrabajador(Base):
    __tablename__ = "ausencias_trabajadores"

    id = Column(Integer, primary_key=True, autoincrement=True)
    trabajador_id = Column(Integer, ForeignKey("trabajadores.id"), nullable=False)
    fecha_inicio = Column(Date, nullable=False)
    fecha_fin = Column(Date, nullable=False)
    tipo_ausencia = Column(String(80), nullable=False)
    # Tipos: Vacaciones / Permiso / Descanso médico / Suspensión / Ausencia
    observaciones = Column(String(300), nullable=True)
    registrado_por = Column(Integer, ForeignKey("usuarios.id"), nullable=True)
    fecha_registro = Column(DateTime, default=func.now())

    trabajador = relationship("Trabajador", back_populates="ausencias")

    def __repr__(self):
        return f"<Ausencia {self.trabajador_id} {self.tipo_ausencia}>"
