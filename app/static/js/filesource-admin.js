"use strict";

var API = "/api/v1/filesources";
var sources = [];
var editingId = null;

// ── Helpers ──

function showToast(msg, type) {
    var t = document.getElementById("toast");
    t.textContent = msg;
    t.className = "toast toast-" + type + " show";
    clearTimeout(t._timer);
    t._timer = setTimeout(function () { t.classList.remove("show"); }, 4000);
}

function protocolBadge(p) {
    return '<span class="badge badge-' + p + '">' + p.toUpperCase() + "</span>";
}

function statusDot(s) {
    var cls = s === "success" ? "status-success" : s === "failed" ? "status-failed" : "status-untested";
    return '<span class="status-dot ' + cls + '"></span>' + s;
}

function fmtSize(bytes) {
    if (!bytes) return "0";
    if (bytes < 1024) return bytes + " B";
    if (bytes < 1048576) return (bytes / 1024).toFixed(1) + " KB";
    return (bytes / 1048576).toFixed(1) + " MB";
}

// ── Load sources ──

async function loadSources() {
    try {
        var res = await fetch(API + "/");
        var body = await res.json();
        sources = body.data ? body.data.sources || [] : [];
        renderTable();
    } catch (e) {
        console.error("Load error", e);
    }
}

function renderTable() {
    var tbody = document.getElementById("sourceBody");
    if (!sources.length) {
        tbody.innerHTML = '<tr><td colspan="7" class="empty-state"><p>No file sources configured yet.</p></td></tr>';
        return;
    }
    var html = "";
    sources.forEach(function (s) {
        html += "<tr>";
        html += "<td><strong>" + esc(s.name) + "</strong>";
        if (s.description) html += "<br><small style='color:var(--text-muted)'>" + esc(s.description) + "</small>";
        html += "</td>";
        html += "<td>" + protocolBadge(s.protocol) + "</td>";
        html += "<td>" + esc(s.host || "—") + (s.port ? ":" + s.port : "") + "</td>";
        html += "<td>" + statusDot(s.connection_status) + "</td>";
        html += '<td><label class="toggle"><input type="checkbox"' + (s.is_enabled ? " checked" : "") + ' onchange="toggleEnable(' + s.id + ",this.checked)" + '"><span class="slider"></span></label></td>';
        html += '<td class="actions-cell">';
        html += '<button class="btn btn-sm btn-outline" onclick="openEdit(' + s.id + ')">Edit</button>';
        html += '<button class="btn btn-sm btn-success" onclick="testConn(' + s.id + ')">Test</button>';
        html += '<button class="btn btn-sm btn-primary" onclick="scanSource(' + s.id + ')">Scan</button>';
        html += '<button class="btn btn-sm btn-warning" onclick="pullFiles(' + s.id + ')">Pull&nbsp;Copy</button>';
        html += '<button class="btn btn-sm btn-danger" onclick="confirmDelete(' + s.id + ",\'" + esc(s.name) + "\')" + '">Del</button>';
        html += "</td>";
        html += "</tr>";
    });
    tbody.innerHTML = html;
}

function esc(s) {
    if (!s) return "";
    var d = document.createElement("div");
    d.textContent = s;
    return d.innerHTML;
}

// ── Modal ──

function openModal(title) {
    document.getElementById("modalTitle").textContent = title;
    document.getElementById("modalOverlay").classList.add("open");
}

function closeModal() {
    document.getElementById("modalOverlay").classList.remove("open");
    document.getElementById("sourceForm").reset();
    document.getElementById("testResultBox").textContent = "";
    document.getElementById("testResultBox").style.display = "none";
    editingId = null;
    updateProtocolFields();
}

function openAdd() {
    editingId = null;
    document.getElementById("sourceForm").reset();
    document.getElementById("fPassword").value = "";
    document.getElementById("fPassphrase").value = "";
    openModal("Add File Source");
    updateProtocolFields();
}

function openEdit(id) {
    var src = sources.find(function (s) { return s.id === id; });
    if (!src) return;
    editingId = id;
    document.getElementById("fName").value = src.name;
    document.getElementById("fDescription").value = src.description || "";
    document.getElementById("fProtocol").value = src.protocol;
    document.getElementById("fHost").value = src.host || "";
    document.getElementById("fPort").value = src.port || "";
    document.getElementById("fBasePath").value = src.base_path;
    document.getElementById("fShareName").value = src.share_name || "";
    document.getElementById("fDomain").value = src.domain || "";
    document.getElementById("fAuthType").value = src.auth_type;
    document.getElementById("fUsername").value = src.username || "";
    document.getElementById("fPassword").value = "";
    document.getElementById("fKeyFilePath").value = src.key_file_path || "";
    document.getElementById("fPassphrase").value = "";
    document.getElementById("fTimeout").value = src.timeout_seconds;
    document.getElementById("fRetries").value = src.max_retries;
    document.getElementById("fEnabled").checked = src.is_enabled;
    document.getElementById("fSyncBase").checked = src.sync_to_base_folder;
    document.getElementById("fAutoScan").checked = src.auto_scan_enabled;
    openModal("Edit File Source");
    updateProtocolFields();
}

function updateProtocolFields() {
    var proto = document.getElementById("fProtocol").value;
    var remote = proto !== "local";
    document.getElementById("hostGroup").classList.toggle("hidden", !remote);
    document.getElementById("portGroup").classList.toggle("hidden", !remote);
    document.getElementById("smbFields").classList.toggle("hidden", proto !== "smb");
    document.getElementById("authSection").classList.toggle("hidden", proto === "local" || proto === "nfs");
}

// ── Save ──

async function saveSource() {
    var form = document.getElementById("sourceForm");
    var data = {
        name: form.fName.value.trim(),
        description: form.fDescription.value.trim() || null,
        protocol: form.fProtocol.value,
        host: form.fHost.value.trim() || null,
        port: form.fPort.value ? parseInt(form.fPort.value) : null,
        base_path: form.fBasePath.value.trim(),
        share_name: form.fShareName.value.trim() || null,
        domain: form.fDomain.value.trim() || null,
        auth_type: form.fAuthType.value,
        username: form.fUsername.value.trim() || null,
        key_file_path: form.fKeyFilePath.value.trim() || null,
        timeout_seconds: parseInt(form.fTimeout.value) || 30,
        max_retries: parseInt(form.fRetries.value) || 3,
        is_enabled: form.fEnabled.checked,
        sync_to_base_folder: form.fSyncBase.checked,
        auto_scan_enabled: form.fAutoScan.checked,
    };
    if (form.fPassword.value) data.password = form.fPassword.value;
    if (form.fPassphrase.value) data.passphrase = form.fPassphrase.value;

    if (!data.name || !data.base_path) {
        showToast("Name and Base Path are required", "error");
        return;
    }

    var url = editingId ? API + "/" + editingId : API + "/";
    var method = editingId ? "PUT" : "POST";

    try {
        var res = await fetch(url, {
            method: method,
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify(data),
        });
        var body = await res.json();
        if (body.success) {
            showToast(body.message || "Saved", "success");
            closeModal();
            loadSources();
        } else {
            showToast(body.message || body.error_message || "Save failed", "error");
        }
    } catch (e) {
        showToast("Request failed: " + e.message, "error");
    }
}

// ── Toggle enable ──

async function toggleEnable(id, enabled) {
    try {
        await fetch(API + "/" + id, {
            method: "PUT",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify({is_enabled: enabled}),
        });
        loadSources();
    } catch (e) {
        showToast("Toggle failed", "error");
    }
}

// ── Delete ──

function confirmDelete(id, name) {
    if (confirm("Delete source '" + name + "'? This cannot be undone.")) {
        deleteSource(id);
    }
}

async function deleteSource(id) {
    try {
        var res = await fetch(API + "/" + id, {method: "DELETE"});
        var body = await res.json();
        showToast(body.message || "Deleted", body.success ? "success" : "error");
        loadSources();
    } catch (e) {
        showToast("Delete failed: " + e.message, "error");
    }
}

// ── Test connection ──

async function testConn(id) {
    showToast("Testing connection...", "info");
    try {
        var res = await fetch(API + "/" + id + "/test", {method: "POST"});
        var body = await res.json();
        var msg = body.source_name + ": " + body.message;
        showToast(msg, body.success ? "success" : "error");
        loadSources();
    } catch (e) {
        showToast("Test failed: " + e.message, "error");
    }
}

async function testFromModal() {
    if (!editingId) { showToast("Save the source first, then test", "info"); return; }
    var box = document.getElementById("testResultBox");
    box.style.display = "block";
    box.textContent = "Testing...";
    try {
        var res = await fetch(API + "/" + editingId + "/test", {method: "POST"});
        var body = await res.json();
        box.textContent = JSON.stringify(body, null, 2);
        showToast(body.message || (body.success ? "OK" : "Failed"), body.success ? "success" : "error");
        loadSources();
    } catch (e) {
        box.textContent = "Error: " + e.message;
    }
}

// ── Pull files ──

async function pullFiles(id) {
    showToast("Pulling files...", "info");
    try {
        var res = await fetch(API + "/" + id + "/pull", {method: "POST"});
        var body = await res.json();
        var msg = (body.source_name || "") + ": " + body.message;
        showToast(msg, body.success ? "success" : "error");
        loadSources();
    } catch (e) {
        showToast("Pull failed: " + e.message, "error");
    }
}

// ── Scan (direct vectorize, no copy) ──

async function scanSource(id) {
    showToast("Scanning and vectorizing directly...", "info");
    try {
        var res = await fetch(API + "/" + id + "/scan", {method: "POST"});
        var body = await res.json();
        var msg = (body.source_name || "") + ": " + body.message;
        showToast(msg, body.success ? "success" : "error");
        loadSources();
    } catch (e) {
        showToast("Scan failed: " + e.message, "error");
    }
}

// ── Init ──

loadSources();
setInterval(loadSources, 15000);
