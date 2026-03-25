"""
Modelos: Rol, Permiso, Usuario.
"""
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, func
from sqlalchemy.orm import relationship
from app.models.base import Base


class Rol(Base):
    __tablename__ = "roles"

    id = Column(Integer, primary_key=True, autoincrement=True)
    nombre = Column(String(100), unique=True, nullable=False)
    descripcion = Column(String(300), nullable=True)

    usuarios = relationship("Usuario", back_populates="rol")

    def __repr__(self):
        return f"<Rol {self.nombre}>"


class Permiso(Base):
    """Tabla de permisos granulares por rol (extensible)."""
    __tablename__ = "permisos"

    id = Column(Integer, primary_key=True, autoincrement=True)
    rol_id = Column(Integer, ForeignKey("roles.id"), nullable=False)
    modulo = Column(String(100), nullable=False)
    accion = Column(String(100), nullable=False)
    permitido = Column(Boolean, default=True)


class Usuario(Base):
    __tablename__ = "usuarios"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(100), unique=True, nullable=False)
    password_hash = Column(String(256), nullable=False)
    nombre = Column(String(150), nullable=False)
    apellido = Column(String(150), nullable=True)
    email = Column(String(200), nullable=True)
    rol_id = Column(Integer, ForeignKey("roles.id"), nullable=False)
    activo = Column(Boolean, default=True)
    intentos_fallidos = Column(Integer, default=0)
    bloqueado_hasta = Column(DateTime, nullable=True)
    ultimo_login = Column(DateTime, nullable=True)
    fecha_creacion = Column(DateTime, default=func.now())

    rol = relationship("Rol", back_populates="usuarios")

    @property
    def nombre_completo(self):
        if self.apellido:
            return f"{self.nombre} {self.apellido}"
        return self.nombre

    def __repr__(self):
        return f"<Usuario {self.username}>"
