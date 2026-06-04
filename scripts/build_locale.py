#!/usr/bin/env python3
"""
Genera locale/es/LC_MESSAGES/django.{po,mo} y locale/en/...
Sin gettext-bin instalado, usando polib.

Es un sustituto mínimo de `manage.py makemessages` + `compilemessages`
con un mapa de traducción ES→EN escrito a mano para los strings que
hay en los templates del kernel.
"""
import os
import re
import sys
from pathlib import Path

import polib

ROOT = Path("/home/alejandro/Documents/Works/QueAI")
LOCALE = ROOT / "locale"

# Mapa explícito ES → EN para todo lo marcado con trans/blocktrans.
# Cada entrada corresponde al msgid exacto (lo que aparece dentro del
# {% trans "..." %} o entre las tags blocktrans, normalizado).
EN = {
    # base.html
    "Hub": "Hub",
    "Marketplace": "Marketplace",
    "Monitor": "Monitor",
    "Docker engine activo": "Docker engine running",
    "Mi cuenta": "My account",
    "Audit log": "Audit log",
    "Cerrar sesión": "Sign out",
    "Modular · Model-agnostic · Open source": "Modular · Model-agnostic · Open source",

    # welcome.html
    "Bienvenida": "Welcome",
    "Kyubit dando la bienvenida": "Kyubit greeting you",
    "Bienvenido a <em>QueAI</em>": "Welcome to <em>QueAI</em>",
    "El kernel está listo. Tres pasos para empezar a usarlo —\n            puedes saltarlos y volver más tarde cuando quieras.":
        "The kernel is ready. Three steps to get going —\n            feel free to skip them and come back later.",
    "01 · Kernel": "01 · Kernel",
    "02 · Marketplace": "02 · Marketplace",
    "03 · Plugins": "03 · Plugins",
    "¿Qué hace el kernel?": "What does the kernel do?",
    "QueAI gestiona módulos de IA empaquetados como contenedores Docker.\n                Cada módulo es independiente, expone su propia UI y se instala con\n                un click desde el Hub.":
        "QueAI manages AI modules packaged as Docker containers.\n                Each module is independent, exposes its own UI and installs\n                with one click from the Hub.",
    "Ver arquitectura →": "See architecture →",
    "Instala tu primer módulo": "Install your first module",
    "En el Marketplace encuentras OCR, STT y TTS oficiales. Descárgalos,\n                instálalos desde el Hub y empieza a usarlos en local.":
        "The Marketplace ships official OCR, STT and TTS. Download them,\n                install from the Hub and start running them locally.",
    "Ir al Marketplace →": "Open Marketplace →",
    "Crea tu propio plugin": "Build your own plugin",
    "Cualquier microservicio con un <code>manifest.json</code> y un\n                <code>docker-compose.yml</code> puede ser un plugin de QueAI.\n                Hay una plantilla lista para clonar.":
        "Any microservice with a <code>manifest.json</code> and a\n                <code>docker-compose.yml</code> can be a QueAI plugin.\n                There's a template ready to clone.",
    "Guía de plugins →": "Plugin guide →",
    "Explorar Marketplace": "Explore Marketplace",
    "Continuar al inicio": "Continue to home",

    # login.html
    "QueAI — Iniciar sesión": "QueAI — Sign in",
    "Iniciar <em>sesión</em>": "<em>Sign</em> in",
    "Usuario o contraseña incorrectos.": "Wrong username or password.",
    "Usuario": "Username",
    "Contraseña": "Password",
    "Entrar": "Sign in",

    # home.html
    "Inicio": "Home",
    "Orquestador modular de IA": "Modular AI orchestrator",
    "Instala, configura y monitorea módulos de IA desde una sola interfaz.\n            Local, cloud o híbrido — cada módulo es un contenedor con su propia API.":
        "Install, configure and monitor AI modules from one place.\n            Local, cloud or hybrid — every module is a container with its own API.",
    "01 · Hub": "01 · Hub",
    "Hub de módulos": "Module Hub",
    "Instala, detén, configura y consulta logs de todos tus plugins desde un solo lugar.":
        "Install, stop, configure and tail logs for every plugin in one place.",
    "Abrir Hub →": "Open Hub →",
    "Nuevos módulos": "New modules",
    "Descarga del registro oficial o añade un plugin desde una URL de Git.":
        "Pull from the official registry or add a plugin from a Git URL.",
    "Explorar →": "Browse →",
    "03 · Monitor": "03 · Monitor",
    "Métricas en vivo": "Live metrics",
    "CPU, RAM y red en tiempo real para cada contenedor activo.":
        "Real-time CPU, RAM and network for every running container.",
    "Ver dashboard →": "Open dashboard →",
    "modular · model-agnostic · open source":
        "modular · model-agnostic · open source",

    # Hub (module_manager.html)
    "Sin módulos detectados": "No modules detected",
    "Agrega plugins en la carpeta <code>/plugins</code> o <a href=\"{{ mp_url }}\">descárgalos desde el Marketplace</a>.":
        "Drop plugins into the <code>/plugins</code> folder or <a href=\"{{ mp_url }}\">grab them from the Marketplace</a>.",
    "Sin descripción disponible.": "No description available.",
    "Instalar": "Install",
    "Abrir aplicación": "Open app",
    "Logs": "Logs",
    "Docs": "Docs",
    "Detener": "Stop",
    "Reanudar": "Resume",
    "Detalle": "Details",

    # Marketplace (marketplace.html)
    "Registro oficial vacío": "Official registry empty",
    "No hay plugins disponibles. Usa la instalación directa desde Git.":
        "No plugins available. Use the direct Git install instead.",
    "Instalación desde Git": "Install from Git",
    "pega una URL de repositorio": "paste a repository URL",
    "Descargar": "Download",
    "Buscar": "Search",
    "Todos": "All",
    "Actualización": "Updates",
    "Descargados": "Downloaded",
    "Sin descargar": "Not downloaded",
    "Actualizar": "Update",
    "descargado": "downloaded",
    # blocktrans con counter — gettext lo serializa con msgid_plural
    # Lo manejamos como entrada de plural más abajo.

    # Monitor (system_monitor.html)
    "// métricas en tiempo real": "// real-time metrics",
    "actualiza cada 3s": "refreshes every 3s",
    "Memoria RAM": "Memory",
    "Red I/O": "Network I/O",
    "Sin módulos instalados": "No modules installed",
    "Instala módulos desde el <a href=\"{{ hub_url }}\">Hub</a> para comenzar a monitorearlos aquí.":
        "Install modules from the <a href=\"{{ hub_url }}\">Hub</a> to start monitoring them here.",

    # Settings (LANGUAGES)
    "Español": "Spanish",
    "English": "English",
}

# Plurales: msgid singular / msgid plural -> (en_singular, en_plural)
PLURALS = {
    ("{{ counter }} módulo", "{{ counter }} módulos"):
        ("{{ counter }} module", "{{ counter }} modules"),
}


def write_po(lang: str, translations: dict, plurals: dict, plural_form: str):
    po = polib.POFile()
    po.metadata = {
        "Project-Id-Version": "QueAI 1.0",
        "Language": lang,
        "MIME-Version": "1.0",
        "Content-Type": "text/plain; charset=UTF-8",
        "Content-Transfer-Encoding": "8bit",
        "Plural-Forms": plural_form,
    }
    for msgid, msgstr in translations.items():
        po.append(polib.POEntry(msgid=msgid, msgstr=msgstr))
    for (m_s, m_p), (e_s, e_p) in plurals.items():
        entry = polib.POEntry(msgid=m_s, msgid_plural=m_p)
        if lang == "es":
            entry.msgstr_plural = {0: m_s, 1: m_p}
        else:
            entry.msgstr_plural = {0: e_s, 1: e_p}
        po.append(entry)

    dest = LOCALE / lang / "LC_MESSAGES"
    dest.mkdir(parents=True, exist_ok=True)
    po.save(str(dest / "django.po"))
    po.save_as_mofile(str(dest / "django.mo"))
    print(f"  ✓ {lang}: {len(po)} entries → django.po + django.mo")


# Español: msgid == msgstr (es el idioma fuente). Pero necesitamos el .mo
# para que LocaleMiddleware lo "active" oficialmente.
write_po("es", {k: k for k in EN.keys()}, PLURALS,
         "nplurals=2; plural=(n != 1);")
write_po("en", EN, PLURALS, "nplurals=2; plural=(n != 1);")
