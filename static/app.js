/**
 * YouTube Downloader - Clean Client Controller
 */

let selectedQuality = "1080p";
let currentMeta = null;
let eventSource = null;
let pollTimer = null;
let jobStartTime = null;
let timerTicker = null;

// Comprehensive metadata dictionary for all 10 containers & audio encodings
const CONTAINER_METADATA = {
  "mp4-h264": {
    title: "MP4 (H.264 / AAC)",
    badge: "Universal",
    category: "video",
    desc: "The global gold standard for maximum device compatibility. Plays natively on iPhones, Android phones, Smart TVs, web browsers, and video editing suites (Premiere Pro, DaVinci Resolve, Final Cut Pro) without transcoding.",
    speed: "⚡ Ultra-Fast GPU & Hardware Accelerated",
    codecs: "Video: H.264 / AVC • Audio: AAC-LC Stereo",
    sizeMultiplier: 1.0,
  },
  "mp4-av1": {
    title: "MP4 (AV1 / AAC)",
    badge: "Next-Gen Efficient",
    category: "video",
    desc: "Modern open royalty-free codec developed by Google, Apple, and Netflix. Yields ~30% smaller files than H.264 at identical visual clarity. Ideal for saving bandwidth and storage on newer devices.",
    speed: "🌱 Maximum Compression Efficiency (~30% smaller)",
    codecs: "Video: AV1 (AOMedia) • Audio: AAC-LC Stereo",
    sizeMultiplier: 0.72,
  },
  "mkv": {
    title: "MKV (Matroska Container)",
    badge: "Power User & Archival",
    category: "video",
    desc: "Flexible open-standard container capable of preserving multi-track audio, original bitstreams, and soft subtitles without lossy conversion. Best for desktop media players like VLC and MPV.",
    speed: "🚀 Zero Transcoding Overhead (Fastest stream merge)",
    codecs: "Video: Source Codec • Audio: Original Bitstream",
    sizeMultiplier: 1.0,
  },
  "webm": {
    title: "WebM (VP9 / Opus)",
    badge: "Web Native",
    category: "video",
    desc: "Google's open web standard optimized for HTML5 playback and Chromium browsers. Features VP9 video paired with high-clarity Opus audio.",
    speed: "⚡ Native YouTube Stream Container (No remuxing)",
    codecs: "Video: VP9 • Audio: Opus Audio",
    sizeMultiplier: 0.88,
  },
  "mov": {
    title: "MOV (Apple QuickTime)",
    badge: "Apple Ecosystem",
    category: "video",
    desc: "Native container for macOS, iOS, Final Cut Pro, and QuickTime Player. Provides immediate scrub performance in Apple video editing workflows.",
    speed: "⚡ Native macOS & QuickTime Optimized",
    codecs: "Video: H.264 / ProRes • Audio: AAC Stereo",
    sizeMultiplier: 1.05,
  },
  "mp3": {
    title: "MP3 (MPEG-1 Audio Layer III)",
    badge: "Universal Audio",
    category: "audio",
    desc: "The universal digital audio format. Plays on every car stereo, MP3 player, smart speaker, and operating system in existence with VBR/CBR up to 320 kbps.",
    speed: "⚡ Fast Audio Extraction & Universal Compatibility",
    codecs: "Audio: MP3 up to 320 kbps (High Fidelity)",
    audioMultiplier: 1.0,
  },
  "m4a": {
    title: "M4A (Apple AAC)",
    badge: "High Fidelity",
    category: "audio",
    desc: "Advanced Audio Coding in MPEG-4 container. Produces noticeably clearer highs and tighter bass than MP3 at similar or smaller file sizes. Native to Apple Music and iPhones.",
    speed: "🚀 Direct Stream Extract (Zero quality loss)",
    codecs: "Audio: AAC Stereo (Native YouTube track)",
    audioMultiplier: 0.85,
  },
  "opus": {
    title: "OPUS (Ogg Opus)",
    badge: "Maximum Efficiency",
    category: "audio",
    desc: "The cutting-edge IETF audio codec used natively by YouTube and Discord. Superior sound quality at low bitrates with extremely low latency. Outstanding clarity for podcasts and music.",
    speed: "⚡ Native Stream Copy (Lossless copy from YouTube)",
    codecs: "Audio: Opus 48 kHz",
    audioMultiplier: 0.75,
  },
  "flac": {
    title: "FLAC (Free Lossless Audio Codec)",
    badge: "Lossless Studio",
    category: "audio",
    desc: "Studio-grade lossless audio compression that preserves 100% of the acoustic data. Perfect for audiophiles, audio engineers, and permanent music archives.",
    speed: "🎧 Bit-Perfect Lossless Conversion via FFmpeg",
    codecs: "Audio: FLAC Lossless 16/24-bit PCM",
    audioMultiplier: 3.5,
  },
  "wav": {
    title: "WAV (Uncompressed PCM)",
    badge: "Raw Audio Master",
    category: "audio",
    desc: "Uncompressed pulse-code modulation (PCM) audio master. Zero compression artifacts, instant loading in Digital Audio Workstations (DAWs) like Ableton, FL Studio, and Pro Tools.",
    speed: "🎛️ DAW & Studio Ready (Zero decompression latency)",
    codecs: "Audio: Linear PCM 1411 kbps Uncompressed",
    audioMultiplier: 5.5,
  },
};

// Initialize on page load
document.addEventListener("DOMContentLoaded", () => {
  initTheme();
  initSystemChecks();
  initContainerInspector();
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

    if (data.detected_browsers && data.detected_browsers.length > 0) {
      const select = document.getElementById("browser-cookies");
      if (select) {
        select.innerHTML = '<option value="">None (Public videos — Default)</option>';
        data.detected_browsers.forEach(b => {
          const opt = document.createElement("option");
          opt.value = b.id;
          opt.textContent = b.name;
          select.appendChild(opt);
        });
      }
    }
  } catch (e) {
    console.error("System check error", e);
  }
}

// ==============================================================================
// 3. Dynamic Resolution & Container Inspector
// ==============================================================================
function formatBytes(bytes) {
  if (!bytes || bytes <= 0) return "0 MB";
  if (bytes >= 1024 * 1024 * 1024) {
    return `${(bytes / (1024 * 1024 * 1024)).toFixed(1)} GB`;
  }
  if (bytes >= 1024 * 1024) {
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  }
  return `${Math.round(bytes / 1024)} KB`;
}

function formatDuration(sec) {
  if (!sec || sec <= 0) return "0s";
  const h = Math.floor(sec / 3600);
  const m = Math.floor((sec % 3600) / 60);
  const s = Math.floor(sec % 60);
  if (h > 0) return `${h}h ${m}m ${s}s`;
  if (m > 0) return `${m}m ${s}s`;
  return `${s}s`;
}

function calculateEstimatedSize(containerVal, qualityVal) {
  const cMeta = CONTAINER_METADATA[containerVal] || CONTAINER_METADATA["mp4-h264"];
  const isAudio = cMeta.category === "audio" || qualityVal === "audio";
  const totalItems = (currentMeta && currentMeta.total_items) ? currentMeta.total_items : 1;

  if (!currentMeta) {
    return {
      singleFormatted: "Awaiting URL inspection",
      totalFormatted: "Awaiting URL inspection",
      totalItems: 1,
      isAudio: isAudio,
    };
  }

  if (isAudio) {
    let singleBytes = 0;
    if (currentMeta.audio_info && currentMeta.audio_info.codec_sizes && currentMeta.audio_info.codec_sizes[containerVal]) {
      singleBytes = currentMeta.audio_info.codec_sizes[containerVal];
    } else if (currentMeta.audio_info && currentMeta.audio_info.size_bytes) {
      singleBytes = Math.round(currentMeta.audio_info.size_bytes * (cMeta.audioMultiplier || 1.0));
    } else if (currentMeta.duration) {
      const rate = containerVal === "wav" ? 1411 : (containerVal === "flac" ? 900 : (containerVal === "mp3" ? 320 : 160));
      singleBytes = Math.round((rate * 1000 / 8) * currentMeta.duration);
    } else {
      singleBytes = 15 * 1024 * 1024;
    }
    const totalBytes = singleBytes * totalItems;
    return {
      singleFormatted: `~${formatBytes(singleBytes)}`,
      totalFormatted: `~${formatBytes(totalBytes)}`,
      totalItems: totalItems,
      isAudio: true,
    };
  }

  // Video calculation using exact stream sizes from inspection
  let singleBytes = 0;
  if (currentMeta.available_resolutions && currentMeta.available_resolutions.length > 0) {
    const numericQ = parseInt(qualityVal) || 1080;
    let found = currentMeta.available_resolutions.find(r => r.height === numericQ);
    if (!found) {
      found = currentMeta.available_resolutions[0];
    }
    if (found.codec_sizes && found.codec_sizes[containerVal]) {
      singleBytes = found.codec_sizes[containerVal];
    } else if (found.size_bytes) {
      singleBytes = Math.round(found.size_bytes * (cMeta.sizeMultiplier || 1.0));
    }
  }

  if (!singleBytes && currentMeta.duration) {
    const numericQ = parseInt(qualityVal) || 1080;
    let rateKbps = 2500;
    if (numericQ >= 2160) rateKbps = containerVal === 'mp4-av1' ? 15000 : 25000;
    else if (numericQ >= 1440) rateKbps = containerVal === 'mp4-av1' ? 5500 : 12000;
    else if (numericQ >= 1080) rateKbps = containerVal === 'mp4-av1' ? 1800 : 3500;
    else if (numericQ >= 720) rateKbps = containerVal === 'mp4-av1' ? 900 : 1800;
    else rateKbps = 600;
    singleBytes = Math.round((rateKbps * 1000 / 8) * currentMeta.duration);
  }

  const totalBytes = (singleBytes || 100 * 1024 * 1024) * totalItems;
  return {
    singleFormatted: `~${formatBytes(singleBytes)}`,
    totalFormatted: `~${formatBytes(totalBytes)}`,
    totalItems: totalItems,
    isAudio: false,
  };
}

function updateFormatInspectorCard(containerVal) {
  const containerSelect = document.getElementById("container-select");
  const val = containerVal || (containerSelect ? containerSelect.value : "mp4-h264");
  const cMeta = CONTAINER_METADATA[val] || CONTAINER_METADATA["mp4-h264"];

  const badgeEl = document.getElementById("fmt-badge");
  const titleEl = document.getElementById("fmt-title");
  const sizeEl = document.getElementById("fmt-size-est");
  const descEl = document.getElementById("fmt-desc");
  const speedEl = document.getElementById("fmt-speed");
  const codecsEl = document.getElementById("fmt-codecs");

  if (badgeEl) badgeEl.textContent = cMeta.badge;
  if (titleEl) titleEl.textContent = cMeta.title;
  if (descEl) descEl.textContent = cMeta.desc;
  if (speedEl) speedEl.textContent = cMeta.speed;
  if (codecsEl) codecsEl.textContent = cMeta.codecs;

  if (sizeEl) {
    const est = calculateEstimatedSize(val, selectedQuality);
    if (!currentMeta) {
      sizeEl.textContent = "Estimated Size: Awaiting URL inspection (click Fetch Details)";
    } else if (est.totalItems > 1) {
      sizeEl.textContent = `Estimated Size: ${est.totalFormatted} (${est.totalItems} videos)`;
    } else {
      sizeEl.textContent = `Estimated Size: ${est.singleFormatted}`;
    }
  }

  refreshPillsSizes();
}

function refreshPillsSizes() {
  if (!currentMeta || !currentMeta.available_resolutions) return;
  const containerSelect = document.getElementById("container-select");
  const curCont = containerSelect ? containerSelect.value : "mp4-h264";

  const pills = document.querySelectorAll(".quality-option");
  pills.forEach((p) => {
    const qStr = p.getAttribute("data-quality");
    const sizeSpan = p.querySelector(".q-size");
    if (!sizeSpan) return;

    if (qStr === "audio") {
      const audioSz = currentMeta.audio_info?.codec_sizes_formatted?.[curCont]
        || (currentMeta.is_playlist ? currentMeta.audio_info?.playlist_size_formatted : currentMeta.audio_info?.size_formatted);
      if (audioSz) sizeSpan.textContent = audioSz;
    } else {
      const numH = parseInt(qStr);
      const resItem = currentMeta.available_resolutions.find(r => r.height === numH);
      if (resItem) {
        const sz = resItem.codec_sizes_formatted?.[curCont]
          || (currentMeta.is_playlist ? resItem.playlist_size_formatted : resItem.size_formatted);
        if (sz) sizeSpan.textContent = sz;
      }
    }
  });
}

function initContainerInspector() {
  const containerSelect = document.getElementById("container-select");
  if (containerSelect) {
    containerSelect.addEventListener("change", (e) => {
      handleContainerChange(e.target.value);
    });
    updateFormatInspectorCard(containerSelect.value);
  }
}

function handleContainerChange(val) {
  const cMeta = CONTAINER_METADATA[val] || CONTAINER_METADATA["mp4-h264"];
  if (cMeta.category === "audio") {
    selectedQuality = "audio";
    const pills = document.querySelectorAll(".quality-option");
    pills.forEach((p) => {
      if (p.getAttribute("data-quality") === "audio") {
        p.classList.add("active");
      } else {
        p.classList.remove("active");
      }
    });
  } else {
    // If audio was selected, switch back to highest resolution or 1080p
    if (selectedQuality === "audio") {
      let target = "1080p";
      if (currentMeta && currentMeta.available_resolutions && currentMeta.available_resolutions.length > 0) {
        const found = currentMeta.available_resolutions.find(r => r.height === 1080) || currentMeta.available_resolutions[0];
        target = `${found.height}p`;
      }
      selectedQuality = target;
      const pills = document.querySelectorAll(".quality-option");
      pills.forEach((p) => {
        if (p.getAttribute("data-quality") === target) {
          p.classList.add("active");
        } else {
          p.classList.remove("active");
        }
      });
    }
  }

  updateFormatInspectorCard(val);
}

function selectQuality(qualityStr) {
  selectedQuality = qualityStr;
  const containerSelect = document.getElementById("container-select");
  const currentContainer = containerSelect ? containerSelect.value : "mp4-h264";
  const cMeta = CONTAINER_METADATA[currentContainer] || CONTAINER_METADATA["mp4-h264"];

  if (qualityStr === "audio") {
    if (cMeta.category === "video" && containerSelect) {
      containerSelect.value = "mp3";
    }
  } else {
    if (cMeta.category === "audio" && containerSelect) {
      containerSelect.value = "mp4-h264";
    }
  }

  const pills = document.querySelectorAll(".quality-option");
  pills.forEach((p) => {
    if (p.getAttribute("data-quality") === qualityStr) {
      p.classList.add("active");
    } else {
      p.classList.remove("active");
    }
  });

  updateFormatInspectorCard(containerSelect ? containerSelect.value : null);
}

function renderAvailableResolutions(meta) {
  const container = document.getElementById("quality-selector");
  const hintEl = document.getElementById("res-status-hint");
  if (!container) return;

  container.innerHTML = "";

  const resolutions = meta.available_resolutions || [];
  if (resolutions.length === 0) {
    renderFallbackResolutions(meta);
    return;
  }

  const maxRes = resolutions.find(r => r.is_max) || resolutions[0];
  if (hintEl) {
    hintEl.textContent = `${resolutions.length} resolutions detected • Max: ${maxRes.label}`;
  }

  // Choose default resolution: 1080p if available, else highest
  const defaultRes = resolutions.find(r => r.height === 1080) || resolutions[0];
  selectedQuality = `${defaultRes.height}p`;

  const containerSelect = document.getElementById("container-select");
  const curCont = containerSelect ? containerSelect.value : "mp4-h264";

  resolutions.forEach((res) => {
    const box = document.createElement("div");
    box.className = `quality-option ${res.height === defaultRes.height ? "active" : ""}`;
    box.setAttribute("data-quality", `${res.height}p`);
    box.onclick = () => selectQuality(`${res.height}p`);

    const sizeDisplay = (res.codec_sizes_formatted && res.codec_sizes_formatted[curCont])
      ? res.codec_sizes_formatted[curCont]
      : (meta.is_playlist ? res.playlist_size_formatted : res.size_formatted);

    box.innerHTML = `
      ${res.is_max ? '<span class="q-max-badge">MAX</span>' : ''}
      <strong>${res.label}</strong>
      <span class="q-size">${sizeDisplay}</span>
      <span class="q-codec">${res.fps}fps • ${res.vcodec}</span>
    `;
    container.appendChild(box);
  });

  // Render Audio Only option
  const audioInfo = meta.audio_info || {};
  const audioSizeDisplay = (audioInfo.codec_sizes_formatted && audioInfo.codec_sizes_formatted[curCont])
    || (meta.is_playlist ? (audioInfo.playlist_size_formatted || "~15 MB") : (audioInfo.size_formatted || "~8 MB"));

  const audioBox = document.createElement("div");
  audioBox.className = "quality-option";
  audioBox.setAttribute("data-quality", "audio");
  audioBox.onclick = () => selectQuality("audio");

  audioBox.innerHTML = `
    <strong>🎵 Audio Only</strong>
    <span class="q-size">${audioSizeDisplay}</span>
    <span class="q-codec">MP3 / AAC / FLAC</span>
  `;
  container.appendChild(audioBox);

  updateFormatInspectorCard(curCont);
}

function renderFallbackResolutions(meta) {
  const container = document.getElementById("quality-selector");
  if (!container) return;
  container.innerHTML = "";

  const fallbacks = [
    { res: "1080p", label: "1080p Full HD", size: "~95 MB", codec: "60fps • H.264", active: true },
    { res: "720p", label: "720p HD", size: "~45 MB", codec: "60fps • H.264" },
    { res: "480p", label: "480p SD", size: "~25 MB", codec: "30fps • H.264" },
    { res: "audio", label: "🎵 Audio Only", size: "~8 MB", codec: "HQ Stereo" }
  ];

  selectedQuality = "1080p";
  fallbacks.forEach(fb => {
    const box = document.createElement("div");
    box.className = `quality-option ${fb.active ? "active" : ""}`;
    box.setAttribute("data-quality", fb.res);
    box.onclick = () => selectQuality(fb.res);
    box.innerHTML = `
      <strong>${fb.label}</strong>
      <span class="q-size">${fb.size}</span>
      <span class="q-codec">${fb.codec}</span>
    `;
    container.appendChild(box);
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

  const cookieChoice = document.getElementById("browser-cookies")?.value || null;

  try {
    const res = await fetch("/api/inspect", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url: url, cookies_browser: cookieChoice }),
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

  const durEl = document.getElementById("preview-duration");
  if (durEl) {
    if (meta.duration && meta.duration > 0) {
      durEl.textContent = `⏱️ ${formatDuration(meta.duration)}`;
      durEl.classList.remove("hidden");
    } else {
      durEl.classList.add("hidden");
    }
  }

  const chaptEl = document.getElementById("preview-chapters");
  if (chaptEl) {
    if (meta.chapters_count && meta.chapters_count > 0) {
      chaptEl.textContent = `📑 ${meta.chapters_count} Chapters / Timestamps`;
      chaptEl.classList.remove("hidden");
    } else {
      chaptEl.classList.add("hidden");
    }
  }

  const thumbImg = document.getElementById("preview-thumb");
  if (meta.thumbnail) {
    thumbImg.src = meta.thumbnail;
  } else {
    thumbImg.src = "https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?w=500&auto=format&fit=crop&q=60";
  }

  // Populate preview list with selectable checkboxes
  const listEl = document.getElementById("playlist-items-ol");
  listEl.innerHTML = "";
  const items = (meta.preview_items && meta.preview_items.length > 0)
    ? meta.preview_items
    : (meta.entries && meta.entries.length > 0
        ? meta.entries.map((e, idx) => ({ index: idx + 1, title: e.title || `Video ${idx + 1}` }))
        : []);

  if (items.length > 0) {
    items.forEach((item) => {
      const idx = item.index || 1;
      const li = document.createElement("li");
      li.className = "playlist-item-row";
      li.innerHTML = `
        <input type="checkbox" class="playlist-item-chk" data-index="${idx}" checked onchange="updatePlaylistSelectionSummary()" />
        <span class="playlist-item-idx">#${idx}</span>
        <span class="playlist-item-title" title="${escapeHtml(item.title)}">${escapeHtml(item.title)}</span>
      `;
      listEl.appendChild(li);
    });
    updatePlaylistSelectionSummary();
  } else {
    const li = document.createElement("li");
    li.className = "playlist-item-row";
    li.innerHTML = `<span class="playlist-item-title">${escapeHtml(meta.title)}</span>`;
    listEl.appendChild(li);
  }

  // Render the dynamic resolutions detected from stream
  renderAvailableResolutions(meta);
}

function updatePlaylistSelectionSummary() {
  const checkboxes = document.querySelectorAll(".playlist-item-chk");
  const summaryEl = document.getElementById("selected-items-summary");
  if (!checkboxes.length || !summaryEl) return;

  const total = checkboxes.length;
  let checkedCount = 0;
  checkboxes.forEach((cb) => {
    if (cb.checked) checkedCount++;
  });

  if (checkedCount === total) {
    summaryEl.textContent = `All ${total} videos selected`;
  } else if (checkedCount === 0) {
    summaryEl.textContent = `0 videos selected (Select at least 1)`;
  } else {
    summaryEl.textContent = `${checkedCount} of ${total} videos selected`;
  }
}

function toggleAllPlaylistCheckboxes(selectState) {
  const checkboxes = document.querySelectorAll(".playlist-item-chk");
  checkboxes.forEach((cb) => {
    cb.checked = selectState;
  });
  updatePlaylistSelectionSummary();
}

function getSelectedPlaylistIndices() {
  const checkboxes = document.querySelectorAll(".playlist-item-chk");
  if (!checkboxes.length) return null;

  const total = checkboxes.length;
  const selected = [];
  checkboxes.forEach((cb) => {
    if (cb.checked) {
      selected.push(parseInt(cb.getAttribute("data-index")));
    }
  });

  if (selected.length === total) return null;
  return selected;
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
  const containerSelect = document.getElementById("container-select");
  const chosenContainer = containerSelect ? containerSelect.value : "mp4-h264";
  const cMeta = CONTAINER_METADATA[chosenContainer] || CONTAINER_METADATA["mp4-h264"];
  const isAudio = cMeta.category === "audio" || selectedQuality === "audio";

  const workers = parseInt(document.getElementById("workers-slider").value) || 3;
  const chunkSize = parseInt(document.getElementById("chunk-slider").value) || 20;
  const startIdx = parseInt(document.getElementById("item-start").value) || 1;
  const endVal = document.getElementById("item-end").value.trim();
  const endIdx = endVal ? parseInt(endVal) : null;
  const browserCookies = document.getElementById("browser-cookies").value || null;
  const embedSubs = document.getElementById("chk-subs").checked;
  const embedThumb = document.getElementById("chk-thumb").checked;
  const embedChapters = document.getElementById("chk-chapters") ? document.getElementById("chk-chapters").checked : true;
  const autoResume = document.getElementById("chk-resume").checked;
  const sponsorblock = document.getElementById("chk-sponsorblock") ? document.getElementById("chk-sponsorblock").checked : false;

  const selectedItems = getSelectedPlaylistIndices();
  if (selectedItems && selectedItems.length === 0) {
    showToast("Please select at least 1 video from the playlist");
    return;
  }

  const payload = {
    url: url,
    output_dir: destFolder,
    quality: selectedQuality,
    container: chosenContainer,
    audio_only: isAudio,
    audio_format: isAudio ? (cMeta.category === "audio" ? chosenContainer : "m4a") : "m4a",
    workers: workers,
    chunk_size: chunkSize,
    start: startIdx,
    end: endIdx,
    cookies_from_browser: browserCookies,
    embed_subs: embedSubs,
    embed_thumbnail: embedThumb,
    embed_chapters: embedChapters,
    embed_metadata: true,
    no_archive: !autoResume,
    sponsorblock: sponsorblock,
    selected_items: selectedItems,
    title: currentMeta ? currentMeta.title : null,
    is_playlist: currentMeta ? currentMeta.is_playlist : null,
    total_items: currentMeta ? currentMeta.total_items : null,
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

    if (data.status === "QUEUED") {
      showToast(data.message || "Added to download queue!");
      displayDashboard(data);
    } else {
      showToast("Download started!");
      displayDashboard(data);
    }
  } catch (err) {
    showToast(`Download error: ${err.message}`);
  }
}

function displayDashboard(jobData) {
  const panel = document.getElementById("dashboard-panel");
  panel.classList.remove("hidden");
  panel.scrollIntoView({ behavior: "smooth" });

  document.getElementById("active-job-title").textContent = jobData.title || "YouTube Download";
  document.getElementById("active-job-status").textContent = jobData.status || "DOWNLOADING";
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

  // Poll job status every 1.5 seconds
  if (pollTimer) clearInterval(pollTimer);
  pollTimer = setInterval(pollJobState, 1500);
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
    } else {
      document.getElementById("btn-start").disabled = true;
      document.getElementById("active-job-status").textContent = "DOWNLOADING";
    }

    renderBatches(data.batches || []);
    renderProgress(data);
    renderQueue(data.queue || []);
  } catch (err) {
    console.error("Poll error", err);
  }
}

function renderProgress(data) {
  const total = data.total_batches || 1;
  const finished = (data.completed_batches || 0) + (data.failed_batches || 0);
  const batchPct = Math.round((finished / total) * 100);
  const effectivePct = (data.progress_pct !== null && data.progress_pct !== undefined && data.active)
    ? Math.round(data.progress_pct)
    : batchPct;

  const fillEl = document.getElementById("job-progress-fill");
  if (fillEl) fillEl.style.width = `${effectivePct}%`;

  const pctLabel = document.getElementById("job-pct-label");
  if (pctLabel) {
    pctLabel.textContent = `${effectivePct}% Completed`;
  }

  const batchLabel = document.getElementById("job-batches-label");
  if (batchLabel) {
    batchLabel.textContent = `${finished} of ${total} Batches finished`;
  }

  // Live Granular Metrics
  const speedEl = document.getElementById("metric-speed");
  if (speedEl) speedEl.textContent = data.speed || "-- MiB/s";

  const etaEl = document.getElementById("metric-eta");
  if (etaEl) etaEl.textContent = data.eta ? `ETA ${data.eta}` : "--:--";

  const sizeEl = document.getElementById("metric-size");
  if (sizeEl) sizeEl.textContent = data.size || "-- / --";

  const queueEl = document.getElementById("metric-queue");
  if (queueEl) {
    if (data.queue_count && data.queue_count > 0) {
      queueEl.textContent = `${data.queue_count} Queued`;
    } else {
      queueEl.textContent = data.active ? "Active Job" : "Idle";
    }
  }
}

function renderQueue(queue) {
  const sec = document.getElementById("queue-section");
  const list = document.getElementById("queue-list");
  const countNum = document.getElementById("queue-count-num");
  if (!sec || !list) return;

  if (!queue || queue.length === 0) {
    sec.classList.add("hidden");
    return;
  }

  sec.classList.remove("hidden");
  if (countNum) countNum.textContent = queue.length;
  list.innerHTML = "";

  queue.forEach((item, idx) => {
    const card = document.createElement("div");
    card.className = "queue-card";
    const itemTitle = item.title || item.url || `Job #${idx + 1}`;
    card.innerHTML = `
      <div class="queue-card-left">
        <span class="queue-badge">#${idx + 1} In Queue</span>
        <span class="queue-title" title="${escapeHtml(itemTitle)}">${escapeHtml(itemTitle)}</span>
      </div>
      <button type="button" class="queue-del-btn" onclick="deleteQueueItem(${idx})" title="Cancel this queued job">✕ Remove</button>
    `;
    list.appendChild(card);
  });
}

async function deleteQueueItem(index) {
  try {
    const res = await fetch(`/api/queue/${index}`, { method: "DELETE" });
    const data = await res.json();
    showToast(data.message || "Removed from queue");
    pollJobState();
  } catch (err) {
    showToast(`Error: ${err.message}`);
  }
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
// 7. Downloaded Files Library & Management
// ==============================================================================
async function fetchFilesList() {
  try {
    const dest = document.getElementById("dest-folder")?.value || "./downloads";
    const res = await fetch(`/api/files?folder=${encodeURIComponent(dest)}`);
    const files = await res.json();

    const tbody = document.getElementById("files-list-tbody");
    tbody.innerHTML = "";

    if (!files || files.length === 0) {
      tbody.innerHTML = `<tr><td colspan="4" class="table-empty-row">No downloaded files in directory yet.</td></tr>`;
      return;
    }

    files.forEach((f) => {
      const tr = document.createElement("tr");
      const safeName = escapeHtml(f.name);
      tr.innerHTML = `
        <td style="font-weight: 500;">${safeName}</td>
        <td style="font-family: var(--font-mono); font-size: 0.8rem;">${f.size_formatted}</td>
        <td style="color: var(--text-muted); font-size: 0.8rem;">${f.modified}</td>
        <td style="text-align: right; white-space: nowrap;">
          <button type="button" class="btn-table-play" onclick="openMediaModal('${safeName}')">▶ Play</button>
          <button type="button" class="btn-table-delete" onclick="deleteDownloadedFile('${safeName}')" title="Delete file">🗑️</button>
        </td>
      `;
      tbody.appendChild(tr);
    });
  } catch (err) {
    console.error("Error fetching files list", err);
  }
}

async function openContainingFolder() {
  const dest = document.getElementById("dest-folder")?.value || "./downloads";
  try {
    const res = await fetch("/api/files/open", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ folder: dest }),
    });
    const data = await res.json();
    if (res.ok) {
      showToast("Opened destination folder in file explorer");
    } else {
      showToast(`Cannot open folder: ${data.detail}`);
    }
  } catch (err) {
    showToast(`Folder error: ${err.message}`);
  }
}

async function deleteDownloadedFile(filename) {
  if (!confirm(`Are you sure you want to permanently delete "${filename}"?`)) return;
  const dest = document.getElementById("dest-folder")?.value || "./downloads";
  try {
    const res = await fetch(`/api/files/delete?filename=${encodeURIComponent(filename)}&folder=${encodeURIComponent(dest)}`, {
      method: "DELETE",
    });
    const data = await res.json();
    if (res.ok) {
      showToast(`Deleted "${filename}"`);
      fetchFilesList();
    } else {
      showToast(`Delete failed: ${data.detail}`);
    }
  } catch (err) {
    showToast(`Delete failed: ${err.message}`);
  }
}

// ==============================================================================
// 8. One-Click yt-dlp Core Updater
// ==============================================================================
async function updateYtDlpEngine() {
  const btn = document.getElementById("btn-update-ytdlp");
  if (btn) btn.disabled = true;
  showToast("Updating yt-dlp engine to latest version...");
  try {
    const res = await fetch("/api/system/update-ytdlp", { method: "POST" });
    const data = await res.json();
    if (res.ok) {
      showToast(`yt-dlp updated: ${data.version || "Latest release installed"}`);
    } else {
      showToast(`Update info: ${data.detail || data.output}`);
    }
  } catch (err) {
    showToast(`Update error: ${err.message}`);
  } finally {
    if (btn) btn.disabled = false;
  }
}

// ==============================================================================
// 9. In-Browser HTML5 Video & Audio Player Modal
// ==============================================================================
function isVideoFile(filename) {
  const ext = (filename.split(".").pop() || "").toLowerCase();
  return ["mp4", "mkv", "webm", "mov", "avi", "flv", "m4v"].includes(ext);
}

function openMediaModal(filename) {
  const modal = document.getElementById("media-modal");
  const titleEl = document.getElementById("modal-media-title");
  const badgeEl = document.getElementById("modal-media-badge");
  const videoPlayer = document.getElementById("modal-video-player");
  const audioPlayer = document.getElementById("modal-audio-player");
  const directLink = document.getElementById("modal-download-direct");

  const streamUrl = `/api/stream/${encodeURIComponent(filename)}`;
  const isVideo = isVideoFile(filename);

  titleEl.textContent = filename;
  badgeEl.textContent = isVideo ? "VIDEO" : "AUDIO";
  directLink.href = streamUrl;
  directLink.setAttribute("download", filename);

  setPlaybackSpeed(1.0);

  if (isVideo) {
    if (audioPlayer) {
      audioPlayer.pause();
      audioPlayer.classList.add("hidden");
      audioPlayer.src = "";
    }
    if (videoPlayer) {
      videoPlayer.classList.remove("hidden");
      videoPlayer.src = streamUrl;
      videoPlayer.load();
      videoPlayer.play().catch(() => {});
    }
  } else {
    if (videoPlayer) {
      videoPlayer.pause();
      videoPlayer.classList.add("hidden");
      videoPlayer.src = "";
    }
    if (audioPlayer) {
      audioPlayer.classList.remove("hidden");
      audioPlayer.src = streamUrl;
      audioPlayer.load();
      audioPlayer.play().catch(() => {});
    }
  }

  modal.classList.remove("hidden");
}

function closeMediaModal() {
  const modal = document.getElementById("media-modal");
  const videoPlayer = document.getElementById("modal-video-player");
  const audioPlayer = document.getElementById("modal-audio-player");

  if (videoPlayer) {
    videoPlayer.pause();
    videoPlayer.src = "";
  }
  if (audioPlayer) {
    audioPlayer.pause();
    audioPlayer.src = "";
  }
  if (modal) {
    modal.classList.add("hidden");
  }
}

function handleBackdropClick(event) {
  if (event.target.id === "media-modal") {
    closeMediaModal();
  }
}

function setPlaybackSpeed(speed) {
  const videoPlayer = document.getElementById("modal-video-player");
  const audioPlayer = document.getElementById("modal-audio-player");
  if (videoPlayer) videoPlayer.playbackRate = speed;
  if (audioPlayer) audioPlayer.playbackRate = speed;

  document.querySelectorAll(".speed-btn").forEach((btn) => {
    if (parseFloat(btn.getAttribute("data-speed")) === speed) {
      btn.classList.add("active");
    } else {
      btn.classList.remove("active");
    }
  });
}

function escapeHtml(text) {
  if (!text) return "";
  return String(text)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

document.addEventListener("keydown", (e) => {
  if (e.key === "Escape") {
    closeMediaModal();
  }
});

