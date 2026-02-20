"use strict";

var API = "/api/v1/sync";
var refreshTimer = null;

function showToast(msg, type) {
    var t = document.getElementById("toast");
    t.textContent = msg;
    t.className = "toast toast-" + type + " show";
    clearTimeout(t._timer);
    t._timer = setTimeout(function () { t.classList.remove("show"); }, 4000);
}

function setLoading(btnId, loading) {
    var btn = document.getElementById(btnId);
    btn.disabled = loading;
    if (loading) { btn.dataset.origText = btn.textContent; btn.textContent = "Working..."; }
    else { btn.textContent = btn.dataset.origText || btn.textContent; }
}

function showResult(boxId, data) {
    var box = document.getElementById(boxId);
    box.classList.add("visible");
    box.style.display = "block";
    box.textContent = typeof data === "string" ? data : JSON.stringify(data, null, 2);
}

function formatInterval(seconds) {
    if (seconds < 60) return seconds + "s";
    if (seconds < 3600) return Math.floor(seconds / 60) + "m " + (seconds % 60) + "s";
    var h = Math.floor(seconds / 3600);
    var m = Math.floor((seconds % 3600) / 60);
    return h + "h " + m + "m";
}

async function refreshStatus() {
    try {
        var res = await ADMIN_AUTH.adminFetch(API + "/status");
        if (!res.ok) throw new Error("Status fetch failed");
        var data = await res.json();
        var s = data.status || "idle";
        var badgeClass = s === "running" ? "badge-running" : "badge-idle";
        document.getElementById("statusBadge").innerHTML =
            '<span class="badge ' + badgeClass + '">' + s.toUpperCase() + "</span>";
        var iv = data.current_interval_seconds;
        document.getElementById("intervalValue").textContent = iv ? formatInterval(iv) + " (" + iv + "s)" : "\u2014";
        document.getElementById("nextAutoSync").textContent = data.next_auto_sync_ist || "\u2014";
        document.getElementById("nextScheduledSync").textContent = data.next_scheduled_sync_ist || "None";
        document.getElementById("syncsCompleted").textContent = data.total_syncs_completed ?? 0;
        document.getElementById("syncsFailed").textContent = data.total_syncs_failed ?? 0;
        if (iv) document.getElementById("intervalInput").placeholder = "Current: " + iv;

        var lr = data.last_sync_result;
        var box = document.getElementById("lastSyncResult");
        if (lr) {
            var lines = [];
            lines.push("Status:    " + (lr.success ? "SUCCESS" : "FAILED"));
            if (lr.sync_id) lines.push("Sync ID:   " + lr.sync_id);
            if (lr.trigger_source) lines.push("Source:    " + lr.trigger_source);
            if (lr.started_at_ist) lines.push("Started:   " + lr.started_at_ist);
            if (lr.completed_at_ist) lines.push("Completed: " + lr.completed_at_ist);
            if (lr.duration_seconds != null) lines.push("Duration:  " + lr.duration_seconds + "s");
            if (lr.details) {
                var d = lr.details;
                lines.push(""); lines.push("--- Details ---");
                if (d.new_files_added != null) lines.push("New files added:       " + d.new_files_added);
                if (d.new_files_skipped_duplicate != null) lines.push("Duplicates skipped:    " + d.new_files_skipped_duplicate);
                if (d.deleted_files_removed != null) lines.push("Deleted files removed: " + d.deleted_files_removed);
                if (d.chunks_added != null) lines.push("Chunks added:          " + d.chunks_added);
                if (d.chunks_removed != null) lines.push("Chunks removed:        " + d.chunks_removed);
            }
            if (lr.errors && lr.errors.length > 0) {
                lines.push(""); lines.push("--- Errors ---");
                lr.errors.forEach(function (e) { lines.push("  " + (typeof e === "string" ? e : JSON.stringify(e))); });
            }
            box.textContent = lines.join("\n");
        } else {
            box.textContent = "No sync has been executed via the admin panel yet.";
        }
    } catch (err) { console.error("Status refresh error:", err); }
}

async function forceSync() {
    setLoading("btnForceSync", true);
    try {
        var res = await ADMIN_AUTH.adminFetch(API + "/trigger", { method: "POST" });
        var data = await res.json();
        showResult("forceSyncResult", data);
        showToast(data.message || (data.success ? "Sync completed" : "Sync failed"), data.success ? "success" : "error");
        refreshStatus();
    } catch (err) { showResult("forceSyncResult", "Error: " + err.message); showToast("Request failed: " + err.message, "error"); }
    finally { setLoading("btnForceSync", false); }
}

async function failsafeSync() {
    setLoading("btnFailsafe", true);
    try {
        var res = await ADMIN_AUTH.adminFetch(API + "/failsafe", { method: "POST" });
        var data = await res.json();
        showResult("failsafeResult", data);
        showToast(data.message || (data.success ? "Failsafe sync succeeded" : "Failsafe sync failed"), data.success ? "success" : "error");
        refreshStatus();
    } catch (err) { showResult("failsafeResult", "Error: " + err.message); showToast("Request failed: " + err.message, "error"); }
    finally { setLoading("btnFailsafe", false); }
}

async function scheduleSync() {
    var raw = document.getElementById("scheduleInput").value;
    if (!raw) { showToast("Please select a date and time", "error"); return; }
    var formatted = raw.replace("T", " ");
    var parts = formatted.split(":"); var timeStr = parts.length === 2 ? formatted + ":00" : formatted;
    setLoading("btnSchedule", true);
    try {
        var res = await ADMIN_AUTH.adminFetch(API + "/schedule", {
            method: "POST", body: JSON.stringify({ scheduled_time: timeStr }),
        });
        var data = await res.json();
        showResult("scheduleResult", data);
        showToast(data.message || (data.success ? "Scheduled" : "Scheduling failed"), data.success ? "success" : "error");
        refreshStatus();
    } catch (err) { showResult("scheduleResult", "Error: " + err.message); showToast("Request failed: " + err.message, "error"); }
    finally { setLoading("btnSchedule", false); }
}

async function updateInterval() {
    var val = parseInt(document.getElementById("intervalInput").value, 10);
    if (!val || val < 1 || val > 86400) { showToast("Interval must be between 1 and 86400 seconds", "error"); return; }
    setLoading("btnInterval", true);
    try {
        var res = await ADMIN_AUTH.adminFetch(API + "/interval", {
            method: "PUT", body: JSON.stringify({ interval_seconds: val }),
        });
        var data = await res.json();
        showResult("intervalResult", data);
        showToast(data.message || (data.success ? "Interval updated" : "Update failed"), data.success ? "success" : "error");
        refreshStatus();
    } catch (err) { showResult("intervalResult", "Error: " + err.message); showToast("Request failed: " + err.message, "error"); }
    finally { setLoading("btnInterval", false); }
}

refreshStatus();
refreshTimer = setInterval(refreshStatus, 5000);
