from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class EventoEntrada(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    evento_id: str | None = Field(default=None, alias="eventoId")
    evento: str
    version: str = "1.0"
    occurred_at: datetime | None = Field(default=None, alias="occurredAt")
    payload: dict[str, Any] = Field(default_factory=dict)


class EventoRespuesta(BaseModel):
    aceptado: bool
    duplicado: bool = False
    evento_id: str
    tipo: str
    mensaje: str


class TareasResumen(BaseModel):
    total: int
    completadas: int
    pendientes: int
    vencidas: int
    porcentaje_completado: float


class GruposResumen(BaseModel):
    total_grupos: int
    grupos_activos: int


class MateriaResumen(BaseModel):
    materia_id: int
    nombre: str
    tareas_completadas: int
    tareas_total: int


class EstadisticasUsuario(BaseModel):
    usuario_id: int
    nombre: str
    periodo: str | None = None
    tareas: TareasResumen
    grupos: GruposResumen
    materias: list[MateriaResumen]
    fecha_calculo: str
    # Solo aparecen cuando alguna dependencia no respondió y se sirve la caché (contrato I.7).
    # Zod descarta claves desconocidas por defecto, así que no rompen estadisticasUsuarioSchema.
    en_cache: bool | None = None
    actualizado_en: str | None = None
    dependencias_no_disponibles: list[str] | None = None


class EstadisticasMateria(BaseModel):
    materia_id: int
    nombre: str
    nrc: str | None = None
    periodo: str | None = None
    tareas: TareasResumen
    grupos: GruposResumen
    fecha_calculo: str


class EstadisticasGrupo(BaseModel):
    grupo_id: int
    nombre: str
    materia_id: int
    integrantes: int
    tareas: TareasResumen
    fecha_calculo: str


class CatalogoItem(BaseModel):
    id: int
    nombre: str
    extra: str | None = None


class ErrorRespuesta(BaseModel):
    codigo: int
    mensaje: str
    dependencia: str | None = None
