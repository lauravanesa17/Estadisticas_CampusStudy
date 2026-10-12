from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.services.tiempo import ahora


class EventoRecibido(Base):
    __tablename__ = "eventos_recibidos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    evento_id: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    tipo: Mapped[str] = mapped_column(String(80), index=True)
    payload_json: Mapped[str] = mapped_column(Text)
    recibido_en: Mapped[datetime] = mapped_column(DateTime, default=ahora)


class UsuarioProyeccion(Base):
    __tablename__ = "usuarios"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nombre: Mapped[str] = mapped_column(String(120), default="")
    email: Mapped[str] = mapped_column(String(180), default="")
    rol: Mapped[str] = mapped_column(String(40), default="estudiante")


class MateriaProyeccion(Base):
    __tablename__ = "materias"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nombre: Mapped[str] = mapped_column(String(160), default="")
    nrc: Mapped[str] = mapped_column(String(20), default="")


class GrupoProyeccion(Base):
    __tablename__ = "grupos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nombre: Mapped[str] = mapped_column(String(160), default="")
    materia_id: Mapped[int] = mapped_column(Integer, default=0)
    creado_por: Mapped[int] = mapped_column(Integer, default=0)


class MiembroGrupo(Base):
    __tablename__ = "miembros_grupo"
    __table_args__ = (UniqueConstraint("grupo_id", "usuario_id", name="uq_grupo_usuario"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    grupo_id: Mapped[int] = mapped_column(Integer, index=True)
    usuario_id: Mapped[int] = mapped_column(Integer, index=True)
    rol: Mapped[str] = mapped_column(String(20), default="miembro")


class TareaProyeccion(Base):
    __tablename__ = "tareas"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    titulo: Mapped[str] = mapped_column(String(150), default="")
    usuario_id: Mapped[int] = mapped_column(Integer, index=True)
    materia_id: Mapped[int] = mapped_column(Integer, index=True)
    grupo_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    prioridad: Mapped[str] = mapped_column(String(20), default="media")
    estado: Mapped[str] = mapped_column(String(30), default="pendiente", index=True)
    fecha_entrega: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    fecha_completada: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    creado_en: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class SincronizacionUsuario(Base):
    """Cuándo se consultó por última vez a cada servicio para un usuario (vigencia de la caché)."""

    __tablename__ = "sincronizacion_usuarios"

    usuario_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    usuario_en: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    tareas_en: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    materias_en: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    grupos_en: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
