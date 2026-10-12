from datetime import datetime, timedelta, timezone


# El contrato fija hora de Colombia (UTC-5). Colombia no tiene horario de verano,
# así que un offset fijo es exacto y no depende de tzdata (que falta en Windows).
ZONA_COLOMBIA = timezone(timedelta(hours=-5), name="America/Bogota")

ESTADOS_CERRADOS = {"completada", "cancelada"}
ALIAS_ESTADO = {
    "entregada": "completada",
    "completado": "completada",
}


def _reloj() -> datetime:
    return datetime.now(ZONA_COLOMBIA)


def ahora() -> datetime:
    """Fecha y hora actual en Colombia, sin tzinfo (igual que lo que se guarda en la BD)."""
    return _reloj().astimezone(ZONA_COLOMBIA).replace(tzinfo=None)


def hoy_iso() -> str:
    return ahora().date().isoformat()


def normalizar_estado(estado: object) -> str:
    texto = str(estado or "pendiente").strip().lower()
    return ALIAS_ESTADO.get(texto, texto or "pendiente")


def _a_colombia(valor: datetime) -> datetime:
    if valor.tzinfo:
        return valor.astimezone(ZONA_COLOMBIA).replace(tzinfo=None)
    return valor


def parsear_fecha(valor: object) -> datetime | None:
    if valor is None or valor == "":
        return None
    if isinstance(valor, datetime):
        return _a_colombia(valor)
    texto = str(valor).replace("Z", "+00:00")
    if len(texto) == 10 and texto[4] == "-" and texto[7] == "-":
        texto = f"{texto}T23:59:00"
    try:
        parsed = datetime.fromisoformat(texto)
    except ValueError:
        return None
    return _a_colombia(parsed)


def parsear_fecha_entrega(fecha: object, hora: object = None) -> datetime | None:
    if fecha is None or fecha == "":
        return None
    texto = str(fecha)
    if hora and "T" not in texto:
        hora_txt = str(hora)
        texto = f"{texto}T{hora_txt}:00" if len(hora_txt) == 5 else f"{texto}T{hora_txt}"
    return parsear_fecha(texto)


def estado_efectivo(estado: str, fecha_entrega: datetime | None, momento: datetime | None = None) -> str:
    """vencida es un conteo derivado: no es un estado persistido por tareas-service.

    Se compara fecha y hora de entrega (hora Colombia); sin hora_entrega vence a las 23:59.
    """
    canonico = normalizar_estado(estado)
    if canonico in ESTADOS_CERRADOS:
        return canonico
    referencia = momento or ahora()
    if fecha_entrega and fecha_entrega < referencia:
        return "vencida"
    return canonico or "pendiente"
