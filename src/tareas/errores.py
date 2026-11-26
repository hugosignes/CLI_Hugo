class ErrorCLI(Exception):
    """Excepción base de la CLI con código de salida asociado."""

    codigo_salida: int = 1

    def __init__(self, mensaje: str, codigo_salida: int | None = None) -> None:
        super().__init__(mensaje)
        if codigo_salida is not None:
            self.codigo_salida = codigo_salida


class ErrorEjecucion(ErrorCLI):
    codigo_salida = 1


class ErrorIA(ErrorEjecucion):
    """Fallo de red, tiempo de espera o respuesta inválida del proveedor IA."""

    codigo_salida = 1


class RutaNoValida(ErrorCLI):
    """Carpeta o ruta inexistente o sin permisos."""

    codigo_salida = 2


class ConfigError(ErrorCLI):
    """Error estructural o de tipos en acciones.json."""

    codigo_salida = 3


class AccionNoValida(ConfigError):
    """Una acción concreta tiene campos faltantes, tipos erróneos o tipo desconocido."""

    codigo_salida = 3
