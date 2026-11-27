from __future__ import annotations

import hashlib
import shutil
import time
import unicodedata
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from tareas.errores import AccionNoValida
from tareas.ia import ProveedorIA


@dataclass(frozen=True)
class ResultadoOperacion:
    origen: str
    destino: str
    estado: str


class Accion(ABC):
    """Clase base para todas las acciones configurables en acciones.json."""

    requiere_ia: bool = False

    def __init__(self, nombre: str, descripcion: str = "") -> None:
        assert nombre.strip(), "Toda acción debe tener un nombre no vacío"
        self.nombre = nombre
        self.descripcion = descripcion

    @abstractmethod
    def ejecutar(
        self,
        carpeta: Path,
        simular: bool = False,
        proveedor_ia: ProveedorIA | None = None,
        registro_acciones: dict[str, Accion] | None = None,
    ) -> list[ResultadoOperacion]:
        """Ejecuta la acción sobre la carpeta indicada."""

    @staticmethod
    def _exigir_campo(datos: dict[str, Any], campo: str, tipo_esperado: type, nombre_accion: str) -> Any:
        if campo not in datos:
            raise AccionNoValida(f"Acción '{nombre_accion}': falta el campo obligatorio '{campo}'.")
        valor = datos[campo]
        if tipo_esperado is int and isinstance(valor, bool):
            raise AccionNoValida(
                f"Acción '{nombre_accion}': el campo '{campo}' debe ser int, no bool."
            )
        if not isinstance(valor, tipo_esperado):
            raise AccionNoValida(
                f"Acción '{nombre_accion}': el campo '{campo}' debe ser de tipo {tipo_esperado.__name__}."
            )
        return valor

    @staticmethod
    def desde_dict(datos: Any) -> Accion:
        """Fábrica estática que valida el diccionario JSON y construye la subclase adecuada."""
        if not isinstance(datos, dict):
            raise AccionNoValida("Cada elemento de 'acciones' debe ser un objeto JSON.")

        nombre = Accion._exigir_campo(datos, "nombre", str, "<sin-nombre>")
        if not nombre.strip():
            raise AccionNoValida("El campo 'nombre' de una acción no puede estar vacío.")

        tipo = Accion._exigir_campo(datos, "tipo", str, nombre)
        descripcion = datos.get("descripcion", "")
        if not isinstance(descripcion, str):
            raise AccionNoValida(f"Acción '{nombre}': el campo 'descripcion' debe ser texto (str).")

        if tipo == "ordenar":
            categorias = Accion._exigir_campo(datos, "categorias", dict, nombre)
            if not categorias:
                raise AccionNoValida(f"Acción '{nombre}': 'categorias' no puede estar vacío.")
            for cat, exts in categorias.items():
                if not isinstance(cat, str) or not isinstance(exts, list) or not all(isinstance(e, str) for e in exts):
                    raise AccionNoValida(
                        f"Acción '{nombre}': la categoría '{cat}' debe mapear a una lista de extensiones (str)."
                    )
            return AccionOrdenar(nombre=nombre, descripcion=descripcion, categorias=categorias)

        if tipo == "renombrar_limpio":
            return AccionRenombrar(nombre=nombre, descripcion=descripcion)

        if tipo == "limpiar_temporales":
            dias = Accion._exigir_campo(datos, "dias_antiguedad", int, nombre)
            if dias < 0:
                raise AccionNoValida(f"Acción '{nombre}': 'dias_antiguedad' debe ser >= 0.")
            extensiones = datos.get("extensiones", [".tmp", ".bak", ".log", ".old"])
            if not isinstance(extensiones, list) or not all(isinstance(e, str) for e in extensiones):
                raise AccionNoValida(f"Acción '{nombre}': 'extensiones' debe ser una lista de cadenas.")
            return AccionLimpiarTemporales(
                nombre=nombre,
                descripcion=descripcion,
                dias_antiguedad=dias,
                extensiones=[e.lower() for e in extensiones],
            )

        if tipo == "duplicados":
            eliminar = datos.get("eliminar", False)
            if not isinstance(eliminar, bool):
                raise AccionNoValida(f"Acción '{nombre}': 'eliminar' debe ser booleano (true/false).")
            return AccionDuplicados(nombre=nombre, descripcion=descripcion, eliminar=eliminar)

        if tipo == "resumir_ia":
            extensiones = datos.get("extensiones", [".txt", ".md"])
            if not isinstance(extensiones, list) or not all(isinstance(e, str) for e in extensiones):
                raise AccionNoValida(f"Acción '{nombre}': 'extensiones' debe ser una lista de cadenas.")
            return AccionResumirIA(
                nombre=nombre,
                descripcion=descripcion,
                extensiones=[e.lower() for e in extensiones],
            )

        if tipo == "renombrar_ia":
            extensiones = datos.get("extensiones", [".txt", ".md"])
            if not isinstance(extensiones, list) or not all(isinstance(e, str) for e in extensiones):
                raise AccionNoValida(f"Acción '{nombre}': 'extensiones' debe ser una lista de cadenas.")
            return AccionRenombrarIA(
                nombre=nombre,
                descripcion=descripcion,
                extensiones=[e.lower() for e in extensiones],
            )

        if tipo == "encadenar":
            pasos = Accion._exigir_campo(datos, "pasos", list, nombre)
            if len(pasos) < 2 or not all(isinstance(p, str) for p in pasos):
                raise AccionNoValida(
                    f"Acción '{nombre}': 'pasos' debe ser una lista con al menos 2 nombres de acción."
                )
            return AccionEncadenada(nombre=nombre, descripcion=descripcion, pasos=pasos)

        raise AccionNoValida(f"Acción '{nombre}': tipo '{tipo}' no soportado.")


class AccionOrdenar(Accion):
    def __init__(self, nombre: str, descripcion: str, categorias: dict[str, list[str]]) -> None:
        super().__init__(nombre, descripcion)
        self._categorias = {k: [e.lower() for e in v] for k, v in categorias.items()}

    def ejecutar(self, carpeta: Path, simular: bool = False, **_: Any) -> list[ResultadoOperacion]:
        assert carpeta.is_dir(), "La carpeta destino debe existir"
        resultados: list[ResultadoOperacion] = []
        for fichero in sorted(carpeta.iterdir()):
            if not fichero.is_file():
                continue
            ext = fichero.suffix.lower()
            destino_cat = "Otros"
            for cat, exts in self._categorias.items():
                if ext in exts:
                    destino_cat = cat
                    break
            resultados.append(
                ResultadoOperacion(
                    origen=fichero.name,
                    destino=f"{destino_cat}/{fichero.name}",
                    estado="simulado" if simular else "movido",
                )
            )
            if not simular:
                destino_dir = carpeta / destino_cat
                destino_dir.mkdir(exist_ok=True)
                shutil.move(str(fichero), str(destino_dir / fichero.name))
        return resultados


class AccionRenombrar(Accion):
    @staticmethod
    def _normalizar(nombre: str) -> str:
        sin_tildes = "".join(
            c for c in unicodedata.normalize("NFD", nombre) if unicodedata.category(c) != "Mn"
        )
        return "_".join(sin_tildes.strip().split())

    def ejecutar(self, carpeta: Path, simular: bool = False, **_: Any) -> list[ResultadoOperacion]:
        resultados: list[ResultadoOperacion] = []
        for fichero in sorted(carpeta.iterdir()):
            if not fichero.is_file():
                continue
            nuevo = self._normalizar(fichero.stem) + fichero.suffix.lower()
            if nuevo != fichero.name and not (carpeta / nuevo).exists():
                resultados.append(
                    ResultadoOperacion(
                        origen=fichero.name,
                        destino=nuevo,
                        estado="simulado" if simular else "renombrado",
                    )
                )
                if not simular:
                    fichero.rename(carpeta / nuevo)
        return resultados


class AccionLimpiarTemporales(Accion):
    def __init__(
        self,
        nombre: str,
        descripcion: str,
        dias_antiguedad: int,
        extensiones: list[str],
    ) -> None:
        super().__init__(nombre, descripcion)
        self._dias = dias_antiguedad
        self._extensiones = extensiones

    def ejecutar(self, carpeta: Path, simular: bool = False, **_: Any) -> list[ResultadoOperacion]:
        limite_segundos = time.time() - (self._dias * 86400)
        resultados: list[ResultadoOperacion] = []
        for fichero in sorted(carpeta.iterdir()):
            if not fichero.is_file():
                continue
            if fichero.suffix.lower() in self._extensiones and fichero.stat().st_mtime <= limite_segundos:
                resultados.append(
                    ResultadoOperacion(
                        origen=fichero.name,
                        destino="papelera/eliminado",
                        estado="simulado" if simular else "eliminado",
                    )
                )
                if not simular:
                    fichero.unlink()
        return resultados


class AccionDuplicados(Accion):
    def __init__(self, nombre: str, descripcion: str, eliminar: bool = False) -> None:
        super().__init__(nombre, descripcion)
        self._eliminar = eliminar

    @staticmethod
    def _sha256(ruta: Path) -> str:
        h = hashlib.sha256()
        with ruta.open("rb") as f:
            for bloque in iter(lambda: f.read(65536), b""):
                h.update(bloque)
        return h.hexdigest()

    def ejecutar(self, carpeta: Path, simular: bool = False, **_: Any) -> list[ResultadoOperacion]:
        vistos: dict[str, Path] = {}
        resultados: list[ResultadoOperacion] = []
        for fichero in sorted(carpeta.iterdir()):
            if not fichero.is_file():
                continue
            digest = self._sha256(fichero)
            if digest in vistos:
                estado = "detectado"
                if self._eliminar:
                    estado = "simulado_borrado" if simular else "eliminado"
                    if not simular:
                        fichero.unlink()
                resultados.append(
                    ResultadoOperacion(
                        origen=fichero.name,
                        destino=f"Duplicado de {vistos[digest].name}",
                        estado=estado,
                    )
                )
            else:
                vistos[digest] = fichero
        return resultados


class AccionResumirIA(Accion):
    requiere_ia = True

    def __init__(self, nombre: str, descripcion: str, extensiones: list[str]) -> None:
        super().__init__(nombre, descripcion)
        self._extensiones = extensiones

    def ejecutar(
        self,
        carpeta: Path,
        simular: bool = False,
        proveedor_ia: ProveedorIA | None = None,
        **_: Any,
    ) -> list[ResultadoOperacion]:
        ia = proveedor_ia or ProveedorIA()
        resultados: list[ResultadoOperacion] = []
        for fichero in sorted(carpeta.iterdir()):
            if not fichero.is_file() or fichero.suffix.lower() not in self._extensiones:
                continue
            if simular:
                resultados.append(
                    ResultadoOperacion(
                        origen=fichero.name,
                        destino=f"Resumen IA ({ia.modelo})",
                        estado="simulado",
                    )
                )
            else:
                texto = fichero.read_text(encoding="utf-8", errors="ignore")
                resumen = ia.resumir_texto(texto, fichero.name)
                resultados.append(
                    ResultadoOperacion(origen=fichero.name, destino=resumen, estado="resumido")
                )
        return resultados


class AccionRenombrarIA(Accion):
    requiere_ia = True

    def __init__(self, nombre: str, descripcion: str, extensiones: list[str]) -> None:
        super().__init__(nombre, descripcion)
        self._extensiones = extensiones

    def ejecutar(
        self,
        carpeta: Path,
        simular: bool = False,
        proveedor_ia: ProveedorIA | None = None,
        **_: Any,
    ) -> list[ResultadoOperacion]:
        ia = proveedor_ia or ProveedorIA()
        resultados: list[ResultadoOperacion] = []
        for fichero in sorted(carpeta.iterdir()):
            if not fichero.is_file() or fichero.suffix.lower() not in self._extensiones:
                continue
            texto = fichero.read_text(encoding="utf-8", errors="ignore")
            nuevo_nombre = ia.sugerir_nombre(texto, fichero.suffix)
            if nuevo_nombre != fichero.name and not (carpeta / nuevo_nombre).exists():
                resultados.append(
                    ResultadoOperacion(
                        origen=fichero.name,
                        destino=nuevo_nombre,
                        estado="simulado" if simular else "renombrado_ia",
                    )
                )
                if not simular:
                    fichero.rename(carpeta / nuevo_nombre)
        return resultados


class AccionEncadenada(Accion):
    def __init__(self, nombre: str, descripcion: str, pasos: list[str]) -> None:
        super().__init__(nombre, descripcion)
        self.pasos = pasos

    def ejecutar(
        self,
        carpeta: Path,
        simular: bool = False,
        proveedor_ia: ProveedorIA | None = None,
        registro_acciones: dict[str, Accion] | None = None,
    ) -> list[ResultadoOperacion]:
        if registro_acciones is None:
            raise AccionNoValida(f"Acción '{self.nombre}': no hay registro de acciones para encadenar.")
        resultados_totales: list[ResultadoOperacion] = []
        for paso in self.pasos:
            subaccion = registro_acciones.get(paso)
            if subaccion is None:
                raise AccionNoValida(f"Acción '{self.nombre}': el paso '{paso}' no existe en acciones.json.")
            resultados_totales.extend(
                subaccion.ejecutar(
                    carpeta=carpeta,
                    simular=simular,
                    proveedor_ia=proveedor_ia,
                    registro_acciones=registro_acciones,
                )
            )
        return resultados_totales
