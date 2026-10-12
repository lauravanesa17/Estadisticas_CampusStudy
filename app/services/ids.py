def entero_id(valor: object) -> int | None:
    if valor is None or isinstance(valor, bool) or valor == "":
        return None
    if isinstance(valor, int):
        return valor if valor > 0 else None
    if isinstance(valor, dict):
        return entero_id(
            valor.get("usuario_id")
            or valor.get("materia_id")
            or valor.get("grupo_id")
            or valor.get("tarea_id")
            or valor.get("id")
        )
    texto = str(valor).strip()
    try:
        numero = int(texto)
    except ValueError:
        return None
    return numero if numero > 0 else None


def primer_id(*valores: object) -> int | None:
    for valor in valores:
        convertido = entero_id(valor)
        if convertido is not None:
            return convertido
    return None
