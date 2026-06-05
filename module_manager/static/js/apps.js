const csrfToken =
  document.querySelector("meta[name=\"csrf-token\"]")?.content?.trim() ?? "";

function openApp(url) {
  // Cache-bust: añadimos ?_t=<ms> al URL antes de cargarlo en el iframe.
  // Sin esto el browser sirve el HTML del plugin desde su caché tras un
  // rebuild del container y el usuario sigue viendo la versión vieja.
  // El plugin ignora el query string (FastAPI lo permite).
  const sep = url.includes("?") ? "&" : "?";
  const busted = `${url}${sep}_t=${Date.now()}`;
  document.getElementById("appIframe").src = busted;
  document.getElementById("appModal").classList.add("open");
}

function closeApp() {
  document.getElementById("appModal").classList.remove("open");
  document.getElementById("appIframe").src = "";
}

// Helper i18n con fallback al texto en español si window.i18n no se cargó
// (p. ej. cuando el script se sirve desde una página que no lo expuso).
const t = (key, fallback) => (window.i18n && window.i18n[key]) || fallback;

async function showLogs(folder) {
  const content = document.getElementById("logsContent");
  content.textContent =
    t("connecting_docker", "> Conectando con Docker daemon...") +
    "\n" +
    t("loading_streams", "> Cargando streams...");
  document.getElementById("logsModal").classList.add("open");
  try {
    const r = await fetch(`/manager/logs/${folder}/`);
    const d = await r.json();
    content.textContent = d.status === "ok" ? d.logs : "ERROR: " + d.message;
  } catch {
    content.textContent = t("error_kernel", "CRITICAL ERROR: No se pudo contactar con el Kernel.");
  }
}

let currentConfigFolder = "";

async function openConfigEditor(folder) {
  currentConfigFolder = folder;
  document.getElementById("configTitle").textContent = folder;
  const editor = document.getElementById("envEditor");
  editor.value = t("loading_config", "# Cargando configuración...");
  document.getElementById("configModal").classList.add("open");

  try {
    const r = await fetch(`/manager/get_env/${folder}/`);
    const d = await r.json();
    if (d.status === "ok") {
      editor.value = d.content;
    } else {
      editor.value = "# ERROR: " + d.message;
    }
  } catch {
    editor.value = t("error_filesystem", "# ERROR: No se pudo conectar con el sistema de archivos.");
  }
}

function closeConfigEditor() {
  document.getElementById("configModal").classList.remove("open");
}

async function saveConfig(event) {
  const content = document.getElementById("envEditor").value;
  const btn = event?.currentTarget ?? event?.target;
  if (!btn) return;
  const originalText = btn.textContent;

  btn.textContent = t("applying", "Aplicando…");
  btn.disabled = true;

  const formData = new FormData();
  formData.append("folder_name", currentConfigFolder);
  formData.append("content", content);
  formData.append("csrfmiddlewaretoken", csrfToken);

  try {
    const r = await fetch(`/manager/save_env/`, {
      method: "POST",
      body: formData,
    });
    const d = await r.json();
    if (d.status === "ok") {
      window.location.reload();
    } else {
      alert(t("save_error", "Error al guardar: ") + d.message);
      btn.textContent = originalText;
      btn.disabled = false;
    }
  } catch {
    alert(t("kernel_comm_error", "Error de comunicación con el Kernel."));
    btn.textContent = originalText;
    btn.disabled = false;
  }
}