/**
 * YouTube Downloader - Clean Client Controller
 */

let selectedQuality = "1080p";
let selectedAudioFormat = "m4a";
let currentMeta = null;
let eventSource = null;
let pollTimer = null;
let jobStartTime = null;
let timerTicker = null;

// Initialize on page load
document.addEventListener("DOMContentLoaded", () => {
  initTheme();
  initSystemChecks();
  initQualitySelector();
  initAudioSegments();
  fetchFilesList();
  initLogStream();
});

// ==============================================================================
// 1. Light / Dark Theme Management
// ==============================================================================
function initTheme() {
  const savedTheme = localStorage.getItem("theme");
  const prefersDark = window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches;
  const initialTheme = savedTheme || (prefersDark ? "dark" : "light");

  applyTheme(initialTheme);

  const toggleBtn = document.getElementById("theme-toggle");
  if (toggleBtn) {
    toggleBtn.addEventListener("click", () => {
      const current = document.documentElement.getAttribute("data-theme") || "light";
      const next = current === "light" ? "dark" : "light";
      applyTheme(next);
      localStorage.setItem("theme", next);
    });
  }
}

function applyTheme(theme) {
  document.documentElement.setAttribute("data-theme", theme);
}

// ==============================================================================
// 2. System Status Checks
// ==============================================================================
async function initSystemChecks() {
  try {
    const res = await fetch("/api/system");
    const data = await res.json();

    const ytdlpLabel = document.getElementById("ytdlp-label");
    const ytdlpDot = document.getElementById("ytdlp-dot");
    if (data.ytdlp_version) {
      ytdlpLabel.textContent = `yt-dlp v${data.ytdlp_version}`;
      ytdlpDot.className = "chip-dot dot-green";
    } else {
      ytdlpLabel.textContent = "yt-dlp missing";
      ytdlpDot.className = "chip-dot dot-orange";
    }

    const ffmpegLabel = document.getElementById("ffmpeg-label");
    const ffmpegDot = document.getElementById("ffmpeg-dot");
    if (data.ffmpeg_available) {
      ffmpegLabel.textContent = "FFmpeg Ready";
      ffmpegDot.className = "chip-dot dot-green";
    } else {
      ffmpegLabel.textContent = "FFmpeg Not Found";
      ffmpegDot.className = "chip-dot dot-orange";
    }

    if (data.aria2c_available) {
      const ariaChip = document.getElementById("aria2c-chip");
      if (ariaChip) ariaChip.classList.remove("hidden");
    }
  } catch (e) {
    console.error("System check error", e);
  }
}

// ==============================================================================
// 3. Quality & Audio Format Selectors
// ==============================================================================
function initQualitySelector() {
  const options = document.querySelectorAll(".quality-option");
  const audioGroup = document.getElementById("audio-container-group");

  options.forEach((opt) => {
    opt.addEventListener("click", () => {
      options.forEach((o) => o.classList.remove("active"));
      opt.classList.add("active");
      selectedQuality = opt.getAttribute("data-quality");

      if (selectedQuality === "audio") {
        audioGroup.classList.remove("hidden");
      } else {
        audioGroup.classList.add("hidden");
      }
    });
  });
}

function initAudioSegments() {
  const btns = document.querySelectorAll(".segment-btn");
  btns.forEach((btn) => {
    btn.addEventListener("click", () => {
      btns.forEach((b) => b.classList.remove("active"));
      btn.classList.add("active");
      selectedAudioFormat = btn.getAttribute("data-audio-fmt");
    });
  });
}

function handleSliderChange(type, val) {
  if (type === "workers") {
    document.getElementById("workers-count-label").textContent = `${val} Worker${val === "1" ? "" : "s"}`;
  } else if (type === "chunk") {
    document.getElementById("chunk-count-label").textContent = `${val} Videos`;
  }
}

function toggleAccordion(id) {
  const target = document.getElementById(id);
  const btn = target.previousElementSibling;
  target.classList.toggle("hidden");
  if (btn) btn.classList.toggle("open");
}

function showToast(msg) {
  const toast = document.getElementById("toast-popup");
  const text = document.getElementById("toast-text");
  text.textContent = msg;
  toast.classList.remove("hidden");
  setTimeout(() => {
    toast.classList.add("hidden");
  }, 3200);
}

function setDemoUrl(type) {
  const input = document.getElementById("url-input");
  if (type === "playlist") {
    input.value = "https://youtube.com/playlist?list=PL0c0N7xv8s06alYrdpsYjGXBs1IqIU8QS";
  } else {
    input.value = "https://www.youtube.com/watch?v=jZLHZcyQmJI";
  }
  inspectUrl();
}

async function pasteClipboard() {
  try {
    const text = await navigator.clipboard.readText();
    if (text) {
      document.getElementById("url-input").value = text.trim();
      inspectUrl();
    }
  } catch (err) {
    showToast("Clipboard access unavailable");
  }
}

// ==============================================================================
// 4. URL Inspection
// ==============================================================================
async function inspectUrl() {
  const url = document.getElementById("url-input").value.trim();
  if (!url) return;

  const btn = document.getElementById("btn-inspect");
  const spinner = document.getElementById("inspect-spinner");
  const label = document.getElementById("inspect-label");

  btn.disabled = true;
  spinner.classList.remove("hidden");
  label.textContent = "Inspecting...";

  try {
    const res = await fetch("/api/inspect", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url: url }),
    });

    const data = await res.json();
    if (!res.ok) {
      throw new Error(data.detail || "Could not fetch details");
    }

    currentMeta = data;
    renderMediaPreview(data);
    showToast(`Found: ${data.title}`);
  } catch (err) {
    showToast(`Error: ${err.message}`);
  } finally {
    btn.disabled = false;
    spinner.classList.add("hidden");
    label.textContent = "Fetch Details";
  }
}

function renderMediaPreview(meta) {
  const panel = document.getElementById("preview-panel");
  panel.classList.remove("hidden");

  document.getElementById("preview-title").textContent = meta.title;
  document.getElementById("preview-channel").textContent = meta.uploader || "Creator";
  document.getElementById("preview-count").textContent = `${meta.total_items} Video${meta.total_items === 1 ? "" : "s"}`;
  document.getElementById("preview-type-badge").textContent = meta.is_playlist ? "Playlist" : "Single Video";

  const thumbImg = document.getElementById("preview-thumb");
  if (meta.thumbnail) {
    thumbImg.src = meta.thumbnail;
  } else {
    thumbImg.src = "https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?w=500&auto=format&fit=crop&q=60";
  }

  // Populate preview list
  const listEl = document.getElementById("playlist-items-ol");
  listEl.innerHTML = "";
  if (meta.entries && meta.entries.length > 0) {
    meta.entries.forEach((item) => {
      const li = document.createElement("li");
      li.textContent = item.title || "Video item";
      listEl.appendChild(li);
    });
  } else {
    const li = document.createElement("li");
    li.textContent = meta.title;
    listEl.appendChild(li);
  }
}

// ==============================================================================
// 5. Download Execution & Dashboard
// ==============================================================================
async function startDownload() {
  const url = document.getElementById("url-input").value.trim();
  if (!url) {
    showToast("Please enter a YouTube link first");
    return;
  }

  const destFolder = document.getElementById("dest-folder").value.trim() || "./downloads";
  const workers = parseInt(document.getElementById("workers-slider").value) || 3;
  const chunkSize = parseInt(document.getElementById("chunk-slider").value) || 20;
  const startIdx = parseInt(document.getElementById("item-start").value) || 1;
  const endVal = document.getElementById("item-end").value.trim();
  const endIdx = endVal ? parseInt(endVal) : null;
  const browserCookies = document.getElementById("browser-cookies").value || null;
  const embedSubs = document.getElementById("chk-subs").checked;
  const embedThumb = document.getElementById("chk-thumb").checked;
  const autoResume = document.getElementById("chk-resume").checked;

  const payload = {
    url: url,
    output_dir: destFolder,
    quality: selectedQuality,
    audio_only: selectedQuality === "audio",
    audio_format: selectedAudioFormat,
    workers: workers,
    chunk_size: chunkSize,
    start: startIdx,
    end: endIdx,
    cookies_from_browser: browserCookies,
    embed_subs: embedSubs,
    embed_thumbnail: embedThumb,
    no_archive: !autoResume,
  };

  try {
    const res = await fetch("/api/download", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    const data = await res.json();
    if (!res.ok) {
      throw new Error(data.detail || "Download failed to initiate");
    }

    showToast("Download started!");
    displayDashboard(data);
  } catch (err) {
    showToast(`Download error: ${err.message}`);
  }
}

function displayDashboard(jobData) {
  const panel = document.getElementById("dashboard-panel");
  panel.classList.remove("hidden");
  panel.scrollIntoView({ behavior: "smooth" });

  document.getElementById("active-job-title").textContent = jobData.title || "YouTube Download";
  document.getElementById("active-job-status").textContent = "DOWNLOADING";
  document.getElementById("btn-start").disabled = true;

  // Start timer ticker
  jobStartTime = Date.now();
  if (timerTicker) clearInterval(timerTicker);
  timerTicker = setInterval(() => {
    const elapsedSec = Math.floor((Date.now() - jobStartTime) / 1000);
    const m = Math.floor(elapsedSec / 60);
    const s = elapsedSec % 60;
    document.getElementById("job-time-label").textContent = `Elapsed: ${m > 0 ? `${m}m ` : ""}${s}s`;
  }, 1000);

  // Poll job status every 2 seconds
  if (pollTimer) clearInterval(pollTimer);
  pollTimer = setInterval(pollJobState, 2000);
  pollJobState();
}

async function pollJobState() {
  try {
    const res = await fetch("/api/status");
    const data = await res.json();

    if (!data.active && data.status !== "RUNNING") {
      // Completed, failed, or cancelled
      if (timerTicker) clearInterval(timerTicker);
      if (pollTimer) clearInterval(pollTimer);
      document.getElementById("btn-start").disabled = false;
      document.getElementById("active-job-status").textContent = data.status || "IDLE";
      fetchFilesList();
    }

    renderBatches(data.batches || []);
    renderProgress(data);
  } catch (err) {
    console.error("Poll error", err);
  }
}

function renderProgress(data) {
  const total = data.total_batches || 1;
  const finished = (data.completed_batches || 0) + (data.failed_batches || 0);
  const pct = Math.round((finished / total) * 100);

  document.getElementById("job-progress-fill").style.width = `${pct}%`;
  document.getElementById("job-pct-label").textContent = `${pct}% Completed`;
  document.getElementById("job-batches-label").textContent = `${finished} of ${total} Batches finished`;
}

function renderBatches(batches) {
  const list = document.getElementById("batches-list");
  list.innerHTML = "";

  batches.forEach((b) => {
    const box = document.createElement("div");
    box.className = `batch-box ${b.status}`;

    box.innerHTML = `
      <div class="batch-row-head">
        <span>Batch #${b.batch_num}</span>
        <span class="status-tag ${b.status}">${b.status}</span>
      </div>
      <div class="batch-subtext">Videos ${b.start_idx} – ${b.end_idx}</div>
      <div class="batch-subtext" style="font-family: var(--font-mono);">${b.duration ? `${b.duration.toFixed(1)}s` : (b.status === "RUNNING" ? "Downloading..." : "Queued")}</div>
    `;
    list.appendChild(box);
  });
}

async function cancelDownload() {
  try {
    const res = await fetch("/api/cancel", { method: "POST" });
    const data = await res.json();
    showToast(data.message || "Stopping downloads...");
    // Refresh files list so salvaged partial video shows up immediately
    setTimeout(fetchFilesList, 1200);
  } catch (err) {
    showToast(`Cancel failed: ${err.message}`);
  }
}

// ==============================================================================
// 6. Live SSE Terminal Logging
// ==============================================================================
function initLogStream() {
  if (eventSource) {
    eventSource.close();
  }

  eventSource = new EventSource("/api/logs/stream");
  eventSource.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data);
      appendTerminalLine(data.text, data.level);
    } catch (e) {
      appendTerminalLine(event.data, "info");
    }
  };

  eventSource.onerror = () => {
    // Reconnects automatically
  };
}

function appendTerminalLine(text, level = "info") {
  const terminal = document.getElementById("terminal-box");
  const row = document.createElement("div");
  row.className = `log-row log-${level}`;
  row.textContent = text;
  terminal.appendChild(row);

  terminal.scrollTop = terminal.scrollHeight;

  if (terminal.childElementCount > 250) {
    terminal.removeChild(terminal.firstElementChild);
  }
}

function clearTerminal() {
  document.getElementById("terminal-box").innerHTML = "";
}

function copyTerminal() {
  const text = document.getElementById("terminal-box").innerText;
  navigator.clipboard.writeText(text);
  showToast("Logs copied to clipboard");
}

// ==============================================================================
// 7. Downloaded Files Library
// ==============================================================================
async function fetchFilesList() {
  try {
    const dest = document.getElementById("dest-folder")?.value || "./downloads";
    const res = await fetch(`/api/files?folder=${encodeURIComponent(dest)}`);
    const files = await res.json();

    const tbody = document.getElementById("files-list-tbody");
    tbody.innerHTML = "";

    if (!files || files.length === 0) {
      tbody.innerHTML = `<tr><td colspan="3" class="table-empty-row">No downloaded files in directory yet.</td></tr>`;
      return;
    }

    files.forEach((f) => {
      const tr = document.createElement("tr");
      tr.innerHTML = `
        <td style="font-weight: 500;">${f.name}</td>
        <td style="font-family: var(--font-mono); font-size: 0.8rem;">${f.size_formatted}</td>
        <td style="color: var(--text-muted); font-size: 0.8rem;">${f.modified}</td>
      `;
      tbody.appendChild(tr);
    });
  } catch (err) {
    console.error("Error fetching files list", err);
  }
}
