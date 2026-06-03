"""
Cliente HTTP fino sobre httpx.
"""

from __future__ import annotations

from typing import Any

import httpx


class APIError(Exception):
    def __init__(self, status: int, detail: str):
        super().__init__(f"[{status}] {detail}")
        self.status = status
        self.detail = detail


class QueaiClient:
    def __init__(self, endpoint: str, token: str | None, *, timeout: float = 30.0):
        self.endpoint = endpoint.rstrip("/")
        self.token = token
        self._http = httpx.Client(timeout=timeout)

    def _headers(self, with_auth: bool = True) -> dict[str, str]:
        h = {"Accept": "application/json"}
        if with_auth and self.token:
            h["Authorization"] = f"Bearer {self.token}"
        return h

    def _request(self, method: str, path: str, *, json: Any = None, params: dict | None = None, with_auth: bool = True) -> Any:
        url = f"{self.endpoint}/api/v1{path}"
        try:
            res = self._http.request(method, url, json=json, params=params, headers=self._headers(with_auth))
        except httpx.HTTPError as e:
            raise APIError(0, f"No se pudo conectar con {url}: {e}") from e
        if res.status_code >= 400:
            try:
                body = res.json()
                detail = body.get("detail") or body.get("error") or res.text
            except ValueError:
                detail = res.text or "error sin detalle"
            raise APIError(res.status_code, detail)
        if res.status_code == 204 or not res.content:
            return None
        return res.json()

    # ----- meta -----
    def health(self) -> dict:
        return self._request("GET", "/health", with_auth=False)

    # ----- catálogo -----
    def plugins_list(self) -> dict:
        return self._request("GET", "/plugins/")

    def plugin_detail(self, folder: str) -> dict:
        return self._request("GET", f"/plugins/{folder}/")

    # ----- lifecycle -----
    def install(self, folder: str) -> dict:
        return self._request("POST", f"/plugins/{folder}/install")

    def start(self, folder: str) -> dict:
        return self._request("POST", f"/plugins/{folder}/start")

    def stop(self, folder: str) -> dict:
        return self._request("POST", f"/plugins/{folder}/stop")

    def uninstall(self, folder: str) -> dict:
        return self._request("POST", f"/plugins/{folder}/uninstall")

    def delete(self, folder: str) -> dict:
        return self._request("POST", f"/plugins/{folder}/delete")

    # ----- logs / stats -----
    def logs(self, folder: str, tail: int = 150) -> dict:
        return self._request("GET", f"/plugins/{folder}/logs", params={"tail": tail})

    def logs_stream(self, folder: str, tail: int = 50):
        """Generador que yieldea cada línea recibida por SSE."""
        url = f"{self.endpoint}/api/v1/plugins/{folder}/logs/stream?tail={tail}"
        with self._http.stream("GET", url, headers=self._headers()) as res:
            if res.status_code >= 400:
                raise APIError(res.status_code, res.text or "stream error")
            for raw in res.iter_lines():
                line = raw.strip()
                if not line:
                    continue
                if line.startswith(":"):  # comment / keep-alive
                    continue
                if line.startswith("data:"):
                    yield line[5:].strip()
                elif line.startswith("event: error"):
                    yield "[server error]"

    def stats(self, folder: str) -> dict:
        return self._request("GET", f"/plugins/{folder}/stats")

    # ----- env -----
    def env_get(self, folder: str) -> dict:
        return self._request("GET", f"/plugins/{folder}/env")

    def env_put(self, folder: str, content: str, apply: bool = True) -> dict:
        return self._request("PUT", f"/plugins/{folder}/env", json={"content": content, "apply": apply})

    # ----- audit -----
    def audit_list(self, *, action: str | None = None, target: str | None = None,
                   source: str | None = None, limit: int = 100) -> dict:
        params: dict[str, str | int] = {"limit": limit}
        if action: params["action"] = action
        if target: params["target"] = target
        if source: params["source"] = source
        return self._request("GET", "/audit/", params=params)

    # ----- backup / restore -----
    def backup_download(self, dest_path: str) -> int:
        """Descarga el tar.gz a dest_path. Devuelve bytes escritos."""
        url = f"{self.endpoint}/api/v1/backup"
        total = 0
        with self._http.stream("GET", url, headers=self._headers()) as res:
            if res.status_code >= 400:
                raise APIError(res.status_code, res.text or "backup error")
            with open(dest_path, "wb") as out:
                for chunk in res.iter_bytes(64 * 1024):
                    out.write(chunk)
                    total += len(chunk)
        return total

    def restore_upload(self, src_path: str) -> dict:
        url = f"{self.endpoint}/api/v1/restore"
        with open(src_path, "rb") as f:
            res = self._http.post(url, headers=self._headers(), files={"backup": (src_path, f, "application/gzip")})
        if res.status_code >= 400:
            try:
                body = res.json()
                detail = body.get("detail") or body.get("error") or res.text
            except Exception:
                detail = res.text or "restore error"
            raise APIError(res.status_code, detail)
        return res.json()

    def restore_apply(self) -> dict:
        return self._request("POST", "/restore/apply")

    # ----- marketplace -----
    def marketplace_list(self) -> dict:
        return self._request("GET", "/marketplace/")

    def marketplace_download(self, git_url: str) -> dict:
        return self._request("POST", "/marketplace/download", json={"git_url": git_url})
