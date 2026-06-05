#!/usr/bin/env python3
"""
Genera locale/es/LC_MESSAGES/django.{po,mo} y locale/en/...
Sin gettext-bin instalado, usando polib.

Es un sustituto mínimo de `manage.py makemessages` + `compilemessages`
con un mapa de traducción ES→EN escrito a mano para los strings que
hay en los templates del kernel.
"""
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
    "El kernel está listo. Tres pasos para empezar a usarlo — puedes saltarlos y volver más tarde cuando quieras.":
        "The kernel is ready. Three steps to get going — feel free to skip them and come back later.",
    "01 · Kernel": "01 · Kernel",
    "02 · Marketplace": "02 · Marketplace",
    "03 · Plugins": "03 · Plugins",
    "¿Qué hace el kernel?": "What does the kernel do?",
    "QueAI gestiona módulos de IA empaquetados como contenedores Docker. Cada módulo es independiente, expone su propia UI y se instala con un click desde el Hub.":
        "QueAI manages AI modules packaged as Docker containers. Each module is independent, exposes its own UI and installs with one click from the Hub.",
    "Ver arquitectura →": "See architecture →",
    "Instala tu primer módulo": "Install your first module",
    "En el Marketplace encuentras OCR, STT y TTS oficiales. Descárgalos, instálalos desde el Hub y empieza a usarlos en local.":
        "The Marketplace ships official OCR, STT and TTS. Download them, install from the Hub and start running them locally.",
    "Ir al Marketplace →": "Open Marketplace →",
    "Crea tu propio plugin": "Build your own plugin",
    "Cualquier microservicio con un <code>manifest.json</code> y un <code>docker-compose.yml</code> puede ser un plugin de QueAI. Hay una plantilla lista para clonar.":
        "Any microservice with a <code>manifest.json</code> and a <code>docker-compose.yml</code> can be a QueAI plugin. There's a template ready to clone.",
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
    "Instala, configura y monitorea módulos de IA desde una sola interfaz. Local, cloud o híbrido — cada módulo es un contenedor con su propia API.":
        "Install, configure and monitor AI modules from one place. Local, cloud or hybrid — every module is a container with its own API.",
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
    "Descargando…": "Downloading…",
    "Instalando…": "Installing…",
    "Deteniendo…": "Stopping…",
    "Iniciando…": "Starting…",
    "Actualizando…": "Updating…",
    "Procesando…": "Processing…",
    "esto puede tardar unos minutos": "this may take a few minutes",
    "Clonando repositorio…": "Cloning repository…",
    "Instalando {{ name }}": "Installing {{ name }}",
    "Iniciando {{ name }}": "Starting {{ name }}",
    "Actualizando {{ name }}": "Updating {{ name }}",
    "Descargando {{ name }}": "Downloading {{ name }}",
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

    # Hub filtros
    "Buscar módulo": "Search module",
    "Activos": "Running",
    "Detenidos": "Stopped",
    "Sin instalar": "Not installed",
    "Re-escanear plugins en disco": "Re-scan plugins on disk",
    "Configuración de módulo": "Module configuration",
    "CLAVE=VALOR": "KEY=VALUE",
    "OTRA_CLAVE=VALOR": "ANOTHER_KEY=VALUE",
    "El contenedor se reiniciará al guardar": "The container will restart on save",
    "Guardar y aplicar": "Save and apply",

    # Audit log (Audit log y Usuario ya están en navbar/login arriba)
    "— acción —": "— action —",
    "— fuente —": "— source —",
    "target contiene…": "target contains…",
    "solo errores": "errors only",
    "Filtrar": "Filter",
    "Limpiar": "Clear",
    "Cuándo": "When",
    "Fuente": "Source",
    "Acción": "Action",
    "Target": "Target",
    "Resultado": "Result",
    "Mensaje": "Message",
    "ok": "ok",
    "fail": "fail",
    "← anterior": "← previous",
    "siguiente →": "next →",
    "Sin eventos para esos filtros.": "No events match these filters.",

    # account.html (Mi cuenta ya está en navbar arriba)
    "Información del usuario": "User information",
    "Datos del usuario actual y estado de la sesión.":
        "Current user data and session status.",
    "Email": "Email",
    "Superuser": "Superuser",
    "sí": "yes",
    "no": "no",
    "Último login": "Last login",
    "Cambiar contraseña": "Change password",
    "Define una nueva contraseña. La sesión actual no se cerrará.":
        "Set a new password. Your current session will not be closed.",
    "Contraseña actual": "Current password",
    "Nueva contraseña": "New password",
    "Confirma la nueva contraseña": "Confirm the new password",

    # Mensajes flash (Python views.py)
    "Contraseña actualizada correctamente.": "Password updated successfully.",
    "Revisa los errores del formulario.": "Check the form for errors.",
    "Módulo %(folder)s instalado y activado.": "Module %(folder)s installed and started.",
    "Error al instalar: %(err)s": "Install failed: %(err)s",
    "Módulo %(folder)s reanudado.": "Module %(folder)s resumed.",
    "Error al iniciar: %(err)s": "Start failed: %(err)s",
    "Módulo %(folder)s detenido.": "Module %(folder)s stopped.",
    "Error al detener: %(err)s": "Stop failed: %(err)s",
    "Módulo %(folder)s desinstalado.": "Module %(folder)s uninstalled.",
    "Error al desinstalar el módulo: %(err)s": "Uninstall failed: %(err)s",
    "Módulo %(folder)s eliminado completamente del sistema.": "Module %(folder)s completely removed from the system.",
    "Error al eliminar el módulo: %(err)s": "Delete failed: %(err)s",
    "Configuración de %(folder)s actualizada y aplicada.": "Configuration for %(folder)s updated and applied.",
    "No se pudo conectar con el Marketplace. Verifica tu conexión a internet.":
        "Couldn't reach the Marketplace. Check your internet connection.",
    "No se recibió una URL de Git válida.": "Missing a valid Git URL.",
    "El módulo '%(folder)s' ya está descargado y actualizado (v%(ver)s).":
        "Module '%(folder)s' is already downloaded and up to date (v%(ver)s).",
    "actualizado": "updated",
    "Módulo '%(folder)s' %(action)s con éxito.": "Module '%(folder)s' %(action)s successfully.",
    "Error al descargar/actualizar: %(err)s": "Download/update failed: %(err)s",

    # Confirmaciones / modales
    "¿Confirmar acción?": "Confirm action?",
    "Esta acción no se puede deshacer.": "This action cannot be undone.",
    "Cancelar": "Cancel",
    "Confirmar": "Confirm",
    "¿Desinstalar este módulo?": "Uninstall this module?",
    "Se detendrán los contenedores y se eliminarán imágenes y volúmenes. La carpeta del plugin se conserva.":
        "Containers will stop and images/volumes will be removed. The plugin folder is kept.",
    "Sí, desinstalar": "Yes, uninstall",
    "¿Borrar este módulo?": "Delete this module?",
    "Se eliminará por completo de tu equipo (contenedores, imágenes y carpeta local). Esta acción no se puede deshacer.":
        "It will be removed completely from your machine (containers, images and local folder). This cannot be undone.",
    "Sí, borrar": "Yes, delete",

    # Logs modal y editor de .env (JS strings via window.i18n)
    "▶ Terminal — stdout / stderr": "▶ Terminal — stdout / stderr",
    "Cerrar ✕": "Close ✕",
    "&gt; Conectando con Docker daemon...": "&gt; Connecting to Docker daemon...",
    "> Conectando con Docker daemon...": "> Connecting to Docker daemon...",
    "> Cargando streams...": "> Loading streams...",
    "CRITICAL ERROR: No se pudo contactar con el Kernel.":
        "CRITICAL ERROR: Couldn't contact the Kernel.",
    "# Cargando configuración...": "# Loading configuration...",
    "# ERROR: No se pudo conectar con el sistema de archivos.":
        "# ERROR: Couldn't reach the filesystem.",
    "Error al guardar: ": "Save failed: ",
    "Error de comunicación con el Kernel.": "Kernel communication error.",

}

# Plurales: msgid singular / msgid plural -> (en_singular, en_plural)
PLURALS = {
    ("{{ counter }} módulo", "{{ counter }} módulos"):
        ("{{ counter }} module", "{{ counter }} modules"),
    ("{{ counter }} evento · página {{ pn }} de {{ pt }}",
     "{{ counter }} eventos · página {{ pn }} de {{ pt }}"):
        ("{{ counter }} event · page {{ pn }} of {{ pt }}",
         "{{ counter }} events · page {{ pn }} of {{ pt }}"),
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
