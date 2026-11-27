from __future__ import annotations

import os
import re
import httpx

from tareas.errores import ErrorIA


class ProveedorIA:
    """Cliente desacoplado para modelos locales (Ollama) o compatibles con API HTTP."""

    def __init__(
        self,
        modelo: str | None = None,
        url_base: str | None = None,
        api_key: str | None = None,
        timeout: float = 30.0,
    ) -> None:
        self._modelo = modelo or os.getenv("TAREAS_MODELO", "llama3.2")
        self._url_base = url_base or os.getenv("TAREAS_OLLAMA_URL", "http://localhost:11434/api/generate")
        self._api_key = api_key if api_key is not None else os.getenv("TAREAS_API_KEY", "")
        self._timeout = timeout

    @property
    def modelo(self) -> str:
        return self._modelo

    def _headers(self) -> dict[str, str]:
        if self._api_key:
            return {"Authorization": f"Bearer {self._api_key}"}
        return {}

    def _consultar(self, prompt: str) -> str:
        assert prompt.strip(), "El prompt enviado al proveedor IA no puede estar vacío"
        try:
            respuesta = httpx.post(
                self._url_base,
                json={"model": self._modelo, "prompt": prompt, "stream": False},
                headers=self._headers(),
                timeout=self._timeout,
            )
            respuesta.raise_for_status()
            datos = respuesta.json()
            texto = datos.get("response", "").strip()
            if not texto:
                raise ErrorIA(f"El modelo '{self._modelo}' devolvió una respuesta vacía.")
            return texto
        except httpx.TimeoutException as exc:
            raise ErrorIA(f"Tiempo de espera agotado conectando con IA ({self._url_base}).") from exc
        except httpx.HTTPError as exc:
            raise ErrorIA(f"Sin conexión con el servicio de IA ({self._url_base}): {exc}") from exc
        except ValueError as exc:
            raise ErrorIA("Respuesta JSON inválida recibida desde el servicio de IA.") from exc

    def resumir_texto(self, texto: str, nombre_fichero: str) -> str:
        prompt = (
            f"Resume en máximo 3 viñetas breves y claras en español el archivo '{nombre_fichero}':\n\n"
            f"{texto[:6000]}"
        )
        return self._consultar(prompt)

    def sugerir_nombre(self, texto: str, extension: str) -> str:
        prompt = (
            "Propón un único nombre de archivo corto en español, en minúsculas y separado por guiones bajos "
            "(sin extensión, sin tildes ni caracteres especiales), que describa el contenido siguiente. "
            "Responde SOLO con el nombre:\n\n"
            f"{texto[:3000]}"
        )
        crudo = self._consultar(prompt).splitlines()[0].strip()
        limpio = re.sub(r"[^a-zA-Z0-9_-]", "_", crudo).strip("_").lower()
        if not limpio:
            raise ErrorIA("La IA no generó un identificador de archivo válido.")
        return f"{limpio[:50]}{extension.lower()}"
