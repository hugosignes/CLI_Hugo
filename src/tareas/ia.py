from __future__ import annotations

import os
import re
import ssl
from pathlib import Path

import httpx

from tareas.errores import ErrorIA


class ProveedorIA:
    """Cliente desacoplado compatible con la API del centro (OpenAI-compatible) y Ollama."""

    def __init__(
        self,
        modelo: str | None = None,
        url_base: str | None = None,
        api_key: str | None = None,
        ca_cert: str | None = None,
        timeout: float = 30.0,
    ) -> None:
        self._modelo = (
            modelo
            or os.getenv("TAREAS_MODELO")
            or os.getenv("OPENAI_MODEL")
            or "Qwen38-DualSpark-medium"
        )
        self._url_base = (
            url_base
            or os.getenv("TAREAS_API_URL")
            or os.getenv("TAREAS_OLLAMA_URL")
            or os.getenv("OPENAI_BASE_URL")
            or "https://ia.simarro/llmapi/v1"
        ).rstrip("/")
        self._api_key = (
            api_key
            if api_key is not None
            else (os.getenv("TAREAS_API_KEY") or os.getenv("OPENAI_API_KEY") or "")
        )
        self._ca_cert = (
            ca_cert
            if ca_cert is not None
            else (
                os.getenv("TAREAS_CA_CERT")
                or os.getenv("SSL_CERT_FILE")
                or os.getenv("NODE_EXTRA_CA_CERTS")
                or ""
            )
        )
        self._timeout = timeout

    @property
    def modelo(self) -> str:
        return self._modelo

    def _verify_ssl(self) -> ssl.SSLContext | bool:
        candidatos = [
            self._ca_cert,
            "ca-simarro.crt",
            str(Path.home() / ".config" / "opencode" / "ca-simarro.crt"),
        ]
        for ruta in candidatos:
            if ruta:
                p = Path(ruta).expanduser().resolve()
                if p.is_file():
                    return ssl.create_default_context(cafile=str(p))
        return True

    def _headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"
        return headers

    def _es_formato_openai(self) -> bool:
        return "/v1" in self._url_base or "/chat/completions" in self._url_base or "/llmapi" in self._url_base

    def _endpoint_y_payload(self, prompt: str) -> tuple[str, dict]:
        if self._es_formato_openai():
            endpoint = (
                self._url_base
                if self._url_base.endswith("/chat/completions")
                else f"{self._url_base}/chat/completions"
            )
            payload = {
                "model": self._modelo,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.2,
            }
            return endpoint, payload

        endpoint = (
            self._url_base
            if self._url_base.endswith("/api/generate")
            else f"{self._url_base}/api/generate"
        )
        payload = {"model": self._modelo, "prompt": prompt, "stream": False}
        return endpoint, payload

    @staticmethod
    def _extraer_texto(datos: dict) -> str:
        if "choices" in datos and isinstance(datos["choices"], list) and datos["choices"]:
            mensaje = datos["choices"][0].get("message", {})
            return str(mensaje.get("content", "")).strip()
        return str(datos.get("response", "")).strip()

    def _consultar(self, prompt: str) -> str:
        assert prompt.strip(), "El prompt enviado al proveedor IA no puede estar vacío"
        endpoint, payload = self._endpoint_y_payload(prompt)
        try:
            respuesta = httpx.post(
                endpoint,
                json=payload,
                headers=self._headers(),
                verify=self._verify_ssl(),
                timeout=self._timeout,
            )
            respuesta.raise_for_status()
            datos = respuesta.json()
            texto = self._extraer_texto(datos)
            if not texto:
                raise ErrorIA(f"El modelo '{self._modelo}' devolvió una respuesta vacía.")
            return texto
        except httpx.TimeoutException as exc:
            raise ErrorIA(f"Tiempo de espera agotado conectando con IA ({endpoint}).") from exc
        except httpx.HTTPError as exc:
            raise ErrorIA(f"Sin conexión o error SSL/HTTP con el servicio de IA ({endpoint}): {exc}") from exc
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
