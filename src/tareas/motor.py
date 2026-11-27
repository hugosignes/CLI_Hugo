from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from tareas.acciones import Accion, AccionEncadenada, ResultadoOperacion
from tareas.configuracion import Configuracion
from tareas.errores import ErrorIA, RutaNoValida
from tareas.ia import ProveedorIA


@dataclass
class InformeEjecucion:
    operaciones: list[ResultadoOperacion] = field(default_factory=list)
    avisos: list[str] = field(default_factory=list)


class Motor:
    """Orquesta operaciones del sistema y de IA con degradación elegante sin red."""

    def __init__(self, configuracion: Configuracion, proveedor_ia: ProveedorIA | None = None) -> None:
        self._config = configuracion
        self._ia = proveedor_ia or ProveedorIA()

    @staticmethod
    def _validar_carpeta(carpeta: Path) -> Path:
        if not carpeta.exists() or not carpeta.is_dir():
            raise RutaNoValida(f"La carpeta indicada no existe o no es un directorio: {carpeta}")
        return carpeta.resolve()

    def listar_carpeta(self, carpeta: Path) -> list[dict[str, Any]]:
        ruta = self._validar_carpeta(carpeta)
        return [
            {
                "nombre": f.name,
                "extension": f.suffix.lower(),
                "tamano_bytes": f.stat().st_size,
            }
            for f in sorted(ruta.iterdir())
            if f.is_file()
        ]

    def ejecutar(self, nombre_accion: str, carpeta: Path, simular: bool = False) -> InformeEjecucion:
        ruta = self._validar_carpeta(carpeta)
        accion = self._config.obtener(nombre_accion)
        registro = {a.nombre: a for a in self._config.acciones}
        informe = InformeEjecucion()

        pasos_a_ejecutar: list[Accion] = (
            [self._config.obtener(p) for p in accion.pasos]
            if isinstance(accion, AccionEncadenada)
            else [accion]
        )

        for paso in pasos_a_ejecutar:
            try:
                ops = paso.ejecutar(
                    carpeta=ruta,
                    simular=simular,
                    proveedor_ia=self._ia,
                    registro_acciones=registro,
                )
                informe.operaciones.extend(ops)
            except ErrorIA as err:
                aviso = f"IA no disponible en '{paso.nombre}' ({err}). Se continúa con las tareas locales."
                informe.avisos.append(aviso)

        return informe
