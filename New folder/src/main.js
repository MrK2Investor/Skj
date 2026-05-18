const $ = (id) => document.getElementById(id);

const gatewayUrlInput = $("gatewayUrl");
const userIdInput = $("userId");
const fileInput = $("fileInput");
const imageAction = $("imageAction");
const objectIdInput = $("objectIdInput");
const logBox = $("logBox");
const billingAccount = $("billingAccount");
const billingEvents = $("billingEvents");
const objectsList = $("objectsList");
const uploadProgress = $("uploadProgress");
const processProgress = $("processProgress");

const STORAGE_KEY = "appify-ui-settings";

function normalizeUrl(value) {
  return value.trim().replace(/\/$/, "");
}

function getSettings() {
  return {
    gatewayUrl: normalizeUrl(gatewayUrlInput.value),
    userId: userIdInput.value.trim() || "demo-user",
  };
}

function saveSettings() {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(getSettings()));
  log("Nastavení uloženo.");
}

function loadSettings() {
  const raw = localStorage.getItem(STORAGE_KEY);
  if (!raw) return;
  try {
    const settings = JSON.parse(raw);
    if (settings.gatewayUrl) gatewayUrlInput.value = settings.gatewayUrl;
    if (settings.userId) userIdInput.value = settings.userId;
  } catch {
    localStorage.removeItem(STORAGE_KEY);
  }
}

function log(message, data = null) {
  const time = new Date().toLocaleTimeString();
  const line = data
    ? `[${time}] ${message}\n${JSON.stringify(data, null, 2)}\n\n`
    : `[${time}] ${message}\n`;
  logBox.textContent = line + logBox.textContent;
}

async function apiFetch(path, options = {}) {
  const { gatewayUrl, userId } = getSettings();
  const headers = new Headers(options.headers || {});
  headers.set("x-user-id", userId);
  return fetch(`${gatewayUrl}${path}`, { ...options, headers });
}

async function readJsonOrText(response) {
  const contentType = response.headers.get("content-type") || "";
  if (contentType.includes("application/json")) return response.json();
  return response.text();
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function formatBytes(bytes) {
  if (bytes == null) return "-";
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KiB`;
  return `${(bytes / 1024 / 1024).toFixed(2)} MiB`;
}

function statusColor(status) {
  if (status === "ready") return "success";
  if (status === "payment_required") return "danger";
  return "warning";
}

async function loadObjects() {
  try {
    const response = await apiFetch("/objects");
    const data = await readJsonOrText(response);
    if (!response.ok) {
      log(`Výpis objektů selhal: HTTP ${response.status}`, data);
      return;
    }
    renderObjects(data);
  } catch (error) {
    log("Výpis objektů error", String(error));
  }
}

function renderObjects(items) {
  if (!items.length) {
    objectsList.innerHTML = "<p>Zatím žádné objekty v Gateway DB.</p>";
    return;
  }

  objectsList.innerHTML = items.map((item) => `
    <div class="object-row">
      <div class="object-main">
        <div class="object-title">${escapeHtml(item.filename)}</div>
        <div class="object-id">${escapeHtml(item.object_id)}</div>
        <div class="object-meta">
          <ion-badge color="${statusColor(item.status)}">${escapeHtml(item.status)}</ion-badge>
          <span>${escapeHtml(item.content_type)}</span>
          <span>${formatBytes(item.size)}</span>
          <span>volume: ${escapeHtml(item.volume_id ?? "-")}</span>
          <span>offset: ${escapeHtml(item.offset ?? "-")}</span>
          <span>billed: ${escapeHtml(item.billed_credits ?? 0)} kreditů</span>
        </div>
        <div class="object-date">${escapeHtml(new Date(item.created_at).toLocaleString())}</div>
      </div>
      <div class="object-actions">
        <ion-button size="small" fill="outline" data-action="use" data-id="${escapeHtml(item.object_id)}">Použít ID</ion-button>
        <ion-button size="small" color="success" data-action="download" data-id="${escapeHtml(item.object_id)}">Stáhnout</ion-button>
        <ion-button size="small" color="tertiary" data-action="process" data-id="${escapeHtml(item.object_id)}">Grayscale</ion-button>
        <ion-button size="small" color="danger" fill="outline" data-action="delete" data-id="${escapeHtml(item.object_id)}">Delete</ion-button>
      </div>
    </div>
  `).join("");

  objectsList.querySelectorAll("ion-button[data-action]").forEach((button) => {
    button.addEventListener("click", async () => {
      const action = button.getAttribute("data-action");
      const id = button.getAttribute("data-id");
      objectIdInput.value = id;
      if (action === "download") await downloadFile(id);
      if (action === "delete") await deleteFile(id);
      if (action === "process") await processImageObject(id);
    });
  });
}

async function uploadFile() {
  const file = fileInput.files?.[0];
  if (!file) return log("Nejdřív vyber soubor.");

  const formData = new FormData();
  formData.append("file", file);
  uploadProgress.classList.remove("hidden");

  try {
    const response = await apiFetch("/upload", { method: "POST", body: formData });
    const data = await readJsonOrText(response);
    if (!response.ok) return log(`Upload selhal: HTTP ${response.status}`, data);
    log("Upload přijat Gateway. Stav bude nejdřív uploading, potom ready po storage.ack.", data);
    objectIdInput.value = data.object_id || "";
    setTimeout(loadObjects, 500);
    setTimeout(loadObjects, 1500);
    await loadBilling();
  } catch (error) {
    log("Upload error", String(error));
  } finally {
    uploadProgress.classList.add("hidden");
  }
}

async function processImageObject(objectId = objectIdInput.value.trim()) {
  if (!objectId) return log("Zadej object_id obrázku, který chceš upravit.");
  const action = imageAction.value || "grayscale";
  processProgress.classList.remove("hidden");

  try {
    const response = await apiFetch(`/image/process/${encodeURIComponent(objectId)}?action=${encodeURIComponent(action)}`, {
      method: "POST",
    });
    const data = await readJsonOrText(response);
    if (!response.ok) return log(`Image process selhal: HTTP ${response.status}`, data);
    log("Gateway poslala obrázek do Image Workeru a výsledek ukládá jako nový objekt.", data);
    objectIdInput.value = data.object_id || objectId;
    setTimeout(loadObjects, 500);
    setTimeout(loadObjects, 1500);
    await loadBilling();
  } catch (error) {
    log("Image process error", String(error));
  } finally {
    processProgress.classList.add("hidden");
  }
}

async function downloadFile(objectId = objectIdInput.value.trim()) {
  if (!objectId) return log("Zadej object_id.");

  try {
    const response = await apiFetch(`/download/${encodeURIComponent(objectId)}`);
    if (!response.ok) {
      const error = await readJsonOrText(response);
      return log(`Download selhal: HTTP ${response.status}`, error);
    }

    const blob = await response.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = objectId;
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);

    log("Soubor stažen přes Gateway. Tím se započítá egress billing.", { object_id: objectId, bytes: blob.size });
    await loadBilling();
  } catch (error) {
    log("Download error", String(error));
  }
}

async function deleteFile(objectId = objectIdInput.value.trim()) {
  if (!objectId) return log("Zadej object_id.");

  try {
    const response = await apiFetch(`/download/${encodeURIComponent(objectId)}`, { method: "DELETE" });
    const data = await readJsonOrText(response);
    if (!response.ok) return log(`Delete selhal: HTTP ${response.status}`, data);
    log("Soft delete hotový.", data);
    await loadObjects();
    await loadBilling();
  } catch (error) {
    log("Delete error", String(error));
  }
}

async function loadBilling() {
  try {
    const accountResponse = await apiFetch("/billing/account");
    const accountData = await readJsonOrText(accountResponse);
    billingAccount.textContent = JSON.stringify(accountData, null, 2);

    const eventsResponse = await apiFetch("/billing/events");
    const eventsData = await readJsonOrText(eventsResponse);
    billingEvents.textContent = JSON.stringify(eventsData, null, 2);

    log("Billing načten.");
  } catch (error) {
    log("Billing error", String(error));
  }
}

async function refreshAll() {
  await loadObjects();
  await loadBilling();
}

$("saveSettingsBtn").addEventListener("click", saveSettings);
$("refreshBtn").addEventListener("click", refreshAll);
$("loadBillingBtn").addEventListener("click", loadBilling);
$("uploadBtn").addEventListener("click", uploadFile);
$("processImageBtn").addEventListener("click", () => processImageObject());
$("downloadBtn").addEventListener("click", () => downloadFile());
$("deleteBtn").addEventListener("click", () => deleteFile());

loadSettings();
log("UI načteno. Image Worker se volá přes Gateway, ne přímo z browseru.");
refreshAll();
