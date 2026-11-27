from __future__ import annotations

import json
from pathlib import Path

from tareas.acciones import Accion, AccionEncadenada
from tareas.errores import AccionNoValida, ConfigError


class Configuracion:
    """Gestiona la carga y validación estricta del fichero externo acciones.json."""

    def __init__(self, acciones: dict[str, Accion]) -> None:
        self._acciones = acciones

    @property
    def acciones(self) -> list[Accion]:
        return list(self._acciones.values())

    def obtener(self, nombre: str) -> Accion:
        if nombre not in self._acciones:
            disponibles = ", ".join(self._acciones.keys()) or "ninguna"
            raise AccionNoValida(f"La acción '{nombre}' no existe. Disponibles: {disponibles}.")
        return self._acciones[nombre]

    @staticmethod
    def desde_archivo(ruta: Path) -> Configuracion:
        if not ruta.exists():
            raise ConfigError(f"No se encuentra el fichero de configuración: {ruta}")
        try:
            datos = json.loads(ruta.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise ConfigError(f"Error de sintaxis JSON en '{ruta}' (línea {exc.lineno}): {exc.msg}") from exc

        if not isinstance(datos, dict):
            raise ConfigError("La raíz de acciones.json debe ser un objeto JSON ({...}).")
        if "acciones" not in datos:
            raise ConfigError("Falta el campo obligatorio 'acciones' en acciones.json.")
        if not isinstance(datos["acciones"], list) or not datos["acciones"]:
            raise ConfigError("El campo 'acciones' debe ser una lista no vacía.")

        registro: dict[str, Accion] = {}
        for item in datos["acciones"]:
            accion = Accion.desde_dict(item)
            if accion.nombre in registro:
                raise ConfigError(f"Nombre de acción duplicado en acciones.json: '{accion.nombre}'.")
            registro[accion.nombre] = accion

        for accion in registro.values():
            if isinstance(accion, AccionEncadenada):
                for paso in accion.pasos:
                    if paso not in registro:
                        raise AccionNoValida(
                            f"Acción '{accion.nombre}': el paso encadenado '{paso}' no está definido."
                        )
                    if paso == accion.nombre:
                        raise AccionNoValida(
                            f"Acción '{accion.nombre}': no puede encadenarse a sí misma."
                        )

        return Configuracion(registro)
