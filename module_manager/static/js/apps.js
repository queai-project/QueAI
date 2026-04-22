const csrfToken =
  document.querySelector("meta[name=\"csrf-token\"]")?.content?.trim() ?? "";

function openApp(url) {
  document.getElementById("appIframe").src = url;
  document.getElementById("appModal").classList.add("open");
}

function closeApp() {
  document.getElementById("appModal").classList.remove("open");
  document.getElementById("appIframe").src = "";
}

async function showLogs(folder) {
  const content = document.getElementById("logsContent");
  content.textContent = "> Conectando con Docker daemon...\n> Cargando streams...";
  document.getElementById("logsModal").classList.add("open");
  try {
    const r = await fetch(`/manager/logs/${folder}/`);
    const d = await r.json();
    content.textContent = d.status === "ok" ? d.logs : "ERROR: " + d.message;
  } catch {
    content.textContent = "CRITICAL ERROR: No se pudo contactar con el Kernel.";
  }
}

let currentConfigFolder = "";

async function openConfigEditor(folder) {
  currentConfigFolder = folder;
  document.getElementById("configTitle").textContent = folder;
  const editor = document.getElementById("envEditor");
  editor.value = "# Cargando configuración...";
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
    editor.value = "# ERROR: No se pudo conectar con el sistema de archivos.";
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

  btn.textContent = "Aplicando…";
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
      alert("Error al guardar: " + d.message);
      btn.textContent = originalText;
      btn.disabled = false;
    }
  } catch {
    alert("Error de comunicación con el Kernel.");
    btn.textContent = originalText;
    btn.disabled = false;
  }
}