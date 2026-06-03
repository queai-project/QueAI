"""
OpenAPI 3.0 schema construido a mano.

Mantenerlo a mano es razonable porque la API es pequeña (14 endpoints) y
no añade dependencias pesadas como drf-spectacular. Si crece, migramos.
"""

from __future__ import annotations

from django.conf import settings


def _path(summary, tags=None, *, params=None, body=None, responses=None, security=True):
    op = {
        "summary": summary,
        "tags": tags or ["plugins"],
    }
    if params:
        op["parameters"] = params
    if body:
        op["requestBody"] = body
    if security:
        op["security"] = [{"bearerAuth": []}]
    op["responses"] = responses or {
        "200": {"description": "OK"},
        "401": {"description": "Falta token"},
        "403": {"description": "Token inválido"},
        "404": {"description": "Plugin no encontrado"},
    }
    return op


def _folder_param():
    return {
        "in": "path",
        "name": "folder_name",
        "required": True,
        "schema": {"type": "string"},
        "description": "Nombre de la carpeta del plugin (ej. QueAI-OCR-CPU-LOCAL-MS).",
    }


def build_schema() -> dict:
    return {
        "openapi": "3.0.3",
        "info": {
            "title": "QueAI Kernel API",
            "version": getattr(settings, "QUEAI_VERSION", "") or "0.0.0",
            "description": (
                "API REST del kernel QueAI. Misma lógica que la UI pero accesible "
                "desde scripts, CI y la CLI `queai`.\n\n"
                "Autenticación: header `Authorization: Bearer <QUEAI_API_TOKEN>`."
            ),
        },
        "servers": [
            {"url": "/api/v1", "description": "Kernel local"},
        ],
        "components": {
            "securitySchemes": {
                "bearerAuth": {
                    "type": "http",
                    "scheme": "bearer",
                    "description": "Token definido en QUEAI_API_TOKEN del .env del kernel.",
                }
            },
            "schemas": {
                "Plugin": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "folder_name": {"type": "string"},
                        "display_name": {"type": "string"},
                        "version": {"type": "string"},
                        "description": {"type": "string"},
                        "author": {"type": "string"},
                        "license": {"type": "string"},
                        "logo": {"type": "string"},
                        "entry_points": {
                            "type": "object",
                            "properties": {
                                "ui": {"type": "string"},
                                "config": {"type": "string"},
                                "docs": {"type": "string"},
                            },
                        },
                        "state": {
                            "type": "object",
                            "properties": {
                                "installed": {"type": "boolean"},
                                "running": {"type": "boolean", "nullable": True},
                            },
                        },
                    },
                },
                "ErrorResponse": {
                    "type": "object",
                    "required": ["error", "detail"],
                    "properties": {
                        "error": {"type": "string"},
                        "detail": {"type": "string"},
                    },
                },
            },
        },
        "paths": {
            "/health": {
                "get": _path(
                    "Salud del kernel (público, sin auth)",
                    tags=["meta"],
                    security=False,
                    responses={"200": {"description": "OK"}, "503": {"description": "Degradado"}},
                )
            },
            "/plugins/": {
                "get": _path("Lista todos los plugins conocidos por el catálogo")
            },
            "/plugins/{folder_name}/": {
                "get": _path("Detalle de un plugin", params=[_folder_param()])
            },
            "/plugins/{folder_name}/install": {
                "post": _path("Instala el módulo (docker compose up --build)", params=[_folder_param()])
            },
            "/plugins/{folder_name}/start": {
                "post": _path("Inicia el módulo detenido", params=[_folder_param()])
            },
            "/plugins/{folder_name}/stop": {
                "post": _path("Detiene el módulo", params=[_folder_param()])
            },
            "/plugins/{folder_name}/uninstall": {
                "post": _path(
                    "down --rmi all --volumes (la carpeta del plugin se conserva)",
                    params=[_folder_param()],
                )
            },
            "/plugins/{folder_name}/delete": {
                "post": _path(
                    "uninstall + borrado de la carpeta del plugin",
                    params=[_folder_param()],
                )
            },
            "/plugins/{folder_name}/logs": {
                "get": _path(
                    "Últimas N líneas de logs (default 150, máx 2000)",
                    params=[
                        _folder_param(),
                        {
                            "in": "query",
                            "name": "tail",
                            "schema": {"type": "integer", "default": 150, "minimum": 1, "maximum": 2000},
                        },
                    ],
                )
            },
            "/plugins/{folder_name}/stats": {
                "get": _path(
                    "CPU/RAM/red de los contenedores del módulo (docker stats --no-stream)",
                    params=[_folder_param()],
                )
            },
            "/plugins/{folder_name}/env": {
                "get": _path(
                    "Lee el .env del módulo (lo crea desde .env.example si no existe)",
                    params=[_folder_param()],
                ),
                "put": _path(
                    "Guarda el .env y opcionalmente recrea el contenedor",
                    params=[_folder_param()],
                    body={
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "required": ["content"],
                                    "properties": {
                                        "content": {"type": "string"},
                                        "apply": {"type": "boolean", "default": True},
                                    },
                                }
                            }
                        },
                    },
                ),
            },
            "/marketplace/": {
                "get": _path(
                    "Lista plugins del registry remoto con estado local cruzado",
                    tags=["marketplace"],
                )
            },
            "/marketplace/download": {
                "post": _path(
                    "Clona un plugin desde una URL Git al directorio plugins/",
                    tags=["marketplace"],
                    body={
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "required": ["git_url"],
                                    "properties": {"git_url": {"type": "string"}},
                                }
                            }
                        },
                    },
                )
            },
        },
    }
