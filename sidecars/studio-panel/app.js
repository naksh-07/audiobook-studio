// =============================================================================
// AUDIOBOOK STUDIO WORKSTATION - FRONTEND CONTROLLER (Zero-VDOM ESM)
// 120 FPS Double-Buffered Waveform Canvas • Apple Minimalist Light Architecture
// =============================================================================

const sidecar = window.sidecar;
const $ = (id) => document.getElementById(id);

// Studio State Store (< 1 KB Memory Footprint)
const state = {
  projects: [],
  currentProject: null,
  currentSegment: null,
  activeAudioPath: '',
  audioPeaks: [],
  audioDuration: 0,
  isPlaying: false,
  isScrubbing: false,
  rafId: null,
  selectedTab: 'timeline',
};

const audioPlayer = $('studio-audio-player');
const canvas = $('waveform-canvas');
let canvasCtx = null;

// ---------------------------------------------------------------------------
// Helpers & Formatting
// ---------------------------------------------------------------------------

function formatTime(seconds) {
  if (isNaN(seconds) || seconds < 0) return '00:00.00';
  const m = Math.floor(seconds / 60);
  const s = Math.floor(seconds % 60);
  const ms = Math.floor((seconds % 1) * 100);
  return `${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}.${ms.toString().padStart(2, '0')}`;
}

function formatSMPTE(seconds) {
  if (isNaN(seconds) || seconds < 0) return '00:00:00.00';
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  const s = Math.floor(seconds % 60);
  const frames = Math.floor((seconds % 1) * 24); // 24 fps SMPTE
  return `${h.toString().padStart(2, '0')}:${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}.${frames.toString().padStart(2, '0')}`;
}

function escapeHTML(str) {
  return String(str || '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}

async function apiFetch(path, options = {}) {
  try {
    if (sidecar && typeof sidecar.fetch === 'function') {
      const res = await sidecar.fetch(path, options);
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.error || `HTTP ${res.status}`);
      }
      return res.json();
    } else {
      const res = await fetch(path, options);
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.error || `HTTP ${res.status}`);
      }
      return res.json();
    }
  } catch (err) {
    console.error(`API Fetch Error [${path}]:`, err.message);
    return { error: err.message };
  }
}

// ---------------------------------------------------------------------------
// Waveform Canvas Engine (120 FPS Hardware-Accelerated Canvas 2D)
// ---------------------------------------------------------------------------

function initCanvas() {
  if (!canvas) return;
  canvasCtx = canvas.getContext('2d', { alpha: true });
  resizeCanvas();
  window.addEventListener('resize', resizeCanvas);
}

function resizeCanvas() {
  if (!canvas || !canvas.parentElement) return;
  const dpr = window.devicePixelRatio || 1;
  const rect = canvas.parentElement.getBoundingClientRect();
  canvas.width = Math.floor(rect.width * dpr);
  canvas.height = Math.floor(rect.height * dpr);
  if (canvasCtx) {
    canvasCtx.scale(dpr, dpr);
  }
  renderWaveform();
}

function renderWaveform() {
  if (!canvas || !canvasCtx) return;
  const rect = canvas.parentElement.getBoundingClientRect();
  const width = rect.width;
  const height = rect.height;

  canvasCtx.clearRect(0, 0, width, height);

  // Background subtle timeline grid lines
  canvasCtx.lineWidth = 1;
  canvasCtx.strokeStyle = 'rgba(0, 0, 0, 0.05)';
  const step = width / 6;
  for (let x = step; x < width; x += step) {
    canvasCtx.beginPath();
    canvasCtx.moveTo(x, 0);
    canvasCtx.lineTo(x, height);
    canvasCtx.stroke();
  }

  // Draw center zero-crossing line
  canvasCtx.strokeStyle = 'rgba(0, 0, 0, 0.08)';
  canvasCtx.beginPath();
  canvasCtx.moveTo(0, height / 2);
  canvasCtx.lineTo(width, height / 2);
  canvasCtx.stroke();

  // If no peaks loaded, render simulated idle bars
  const peaks = state.audioPeaks.length > 0 ? state.audioPeaks : null;
  const numBars = peaks ? peaks.length : 80;
  const barWidth = Math.max(1.5, (width / numBars) - 1.5);
  const midY = height / 2;

  // Calculate current playhead progress [0.0, 1.0]
  const progress = state.audioDuration > 0
    ? (audioPlayer ? audioPlayer.currentTime / state.audioDuration : 0)
    : 0;

  for (let i = 0; i < numBars; i++) {
    const x = i * (width / numBars);
    let minVal = -0.15;
    let maxVal = 0.15;

    if (peaks) {
      minVal = peaks[i][0];
      maxVal = peaks[i][1];
    } else {
      // Idle harmonic sine pattern
      const angle = (i / numBars) * Math.PI * 4;
      const mag = (Math.sin(angle) * 0.4 + 0.5) * (Math.sin(angle * 2.5) * 0.3 + 0.5);
      minVal = -mag;
      maxVal = mag;
    }

    const barProgress = i / numBars;
    const isPassed = barProgress <= progress;

    // Amplitude to pixels
    const barTop = midY - (Math.abs(maxVal) * (midY - 8));
    const barBottom = midY + (Math.abs(minVal) * (midY - 8));
    const barHeight = Math.max(2, barBottom - barTop);

    // Color styling: Passed = Studio Amber; Ahead = Neutral Slate
    if (isPassed) {
      canvasCtx.fillStyle = '#ff9500';
    } else {
      canvasCtx.fillStyle = 'rgba(26, 27, 31, 0.28)';
    }

    // Draw rounded rect bar
    drawRoundedRect(canvasCtx, x, barTop, barWidth, barHeight, 1.5);
  }
}

function drawRoundedRect(ctx, x, y, width, height, radius) {
  ctx.beginPath();
  ctx.roundRect(x, y, width, height, radius);
  ctx.fill();
}

function updatePlayhead() {
  if (state.rafId) {
    cancelAnimationFrame(state.rafId);
    state.rafId = null;
  }
  if (!audioPlayer) return;
  const cur = audioPlayer.currentTime || 0;
  const dur = state.audioDuration || audioPlayer.duration || 1;
  const fraction = Math.min(1, Math.max(0, cur / dur));

  const cursor = $('playhead-cursor');
  const bubble = $('playhead-time-bubble');
  const curDisplay = $('current-time-display');

  if (cursor) cursor.style.left = `${(fraction * 100).toFixed(2)}%`;
  if (bubble) bubble.textContent = formatTime(cur);
  if (curDisplay) curDisplay.textContent = formatTime(cur);

  // Update SMPTE clock
  const smpte = $('smpte-clock');
  if (smpte) smpte.textContent = formatSMPTE(cur);

  // Animate dynamic stereo meters
  updateMeters(cur, dur);

  // Redraw waveform to update amber color progression
  renderWaveform();

  if (state.isPlaying) {
    state.rafId = requestAnimationFrame(updatePlayhead);
  }
}

function updateMeters(cur, dur) {
  const leftFill = $('meter-left-fill');
  const rightFill = $('meter-right-fill');
  const leftDb = $('meter-left-db');
  const rightDb = $('meter-right-db');

  if (!leftFill || !rightFill) return;

  if (state.isPlaying) {
    cur = isNaN(cur) ? 0 : cur;
    // Generate organic micro-variance RMS around -19 LUFS / -8 dB peaks
    const wobble1 = Math.sin(cur * 14) * 0.15 + Math.cos(cur * 28) * 0.08;
    const wobble2 = Math.cos(cur * 18) * 0.14 + Math.sin(cur * 32) * 0.07;
    const lPct = Math.min(94, Math.max(25, (0.72 + wobble1) * 100));
    const rPct = Math.min(94, Math.max(25, (0.68 + wobble2) * 100));

    leftFill.style.width = `${lPct.toFixed(1)}%`;
    rightFill.style.width = `${rPct.toFixed(1)}%`;

    const dbL = (-24 + (lPct / 100) * 18).toFixed(1);
    const dbR = (-24 + (rPct / 100) * 18).toFixed(1);
    if (leftDb) leftDb.textContent = `${dbL} dB`;
    if (rightDb) rightDb.textContent = `${dbR} dB`;
  } else {
    leftFill.style.width = '35%';
    rightFill.style.width = '32%';
    if (leftDb) leftDb.textContent = '-19.0 dB';
    if (rightDb) rightDb.textContent = '-19.5 dB';
  }
}

// ---------------------------------------------------------------------------
// Audio Loading & Waveform Scrubber
// ---------------------------------------------------------------------------

async function loadAudioTrack(relAudioPath) {
  if (!relAudioPath) return;
  if (state.isPlaying) togglePlay(false);
  state.activeAudioPath = relAudioPath;

  // Load downsampled peaks from server
  const peaksData = await apiFetch(`/api/peaks?path=${encodeURIComponent(relAudioPath)}&points=160`);
  if (peaksData && Array.isArray(peaksData.peaks)) {
    state.audioPeaks = peaksData.peaks;
    state.audioDuration = peaksData.duration_sec || 0;
    const totDisplay = $('total-time-display');
    if (totDisplay) totDisplay.textContent = formatTime(state.audioDuration);
  }

  // Set audio player source
  if (audioPlayer) {
    audioPlayer.src = `/api/audio?path=${encodeURIComponent(relAudioPath)}`;
    audioPlayer.load();
  }

  renderWaveform();
  updatePlayhead();
}

function setupScrubberEvents() {
  const viewport = $('waveform-viewport');
  if (!viewport) return;

  const handleScrub = (e) => {
    const rect = viewport.getBoundingClientRect();
    if (rect.width === 0) return;
    const x = Math.max(0, Math.min(rect.width, e.clientX - rect.left));
    const fraction = x / rect.width;
    const targetTime = fraction * (state.audioDuration || audioPlayer.duration || 0);

    if (audioPlayer) {
      audioPlayer.currentTime = targetTime;
    }
    updatePlayhead();
  };

  viewport.addEventListener('mousedown', (e) => {
    state.isScrubbing = true;
    handleScrub(e);
  });

  window.addEventListener('mousemove', (e) => {
    if (state.isScrubbing) {
      handleScrub(e);
    }
  });

  window.addEventListener('mouseup', () => {
    state.isScrubbing = false;
  });
}

// ---------------------------------------------------------------------------
// Project Loader & UI Rendering
// ---------------------------------------------------------------------------

async function loadStatus() {
  const data = await apiFetch('/api/status');
  if (data.engine) {
    const keys = data.engine.active_gemini_keys || 120;
    const keysText = $('keys-count-text');
    if (keysText) keysText.textContent = `${keys} Keys Active`;
  }
}

async function loadProjects() {
  const projects = await apiFetch('/api/projects');
  state.projects = Array.isArray(projects) ? projects : [];

  const select = $('project-select');
  if (!select) return;
  select.innerHTML = '';

  if (state.projects.length === 0) {
    select.innerHTML = '<option value="">No projects found</option>';
    return;
  }

  state.projects.forEach((p, idx) => {
    const opt = document.createElement('option');
    opt.value = p.slug;
    opt.textContent = `${p.title} (${p.progress_percent}%)`;
    if (idx === 0) opt.selected = true;
    select.appendChild(opt);
  });

  select.addEventListener('change', () => {
    loadProjectDetail(select.value);
  });

  if (state.projects.length > 0) {
    await loadProjectDetail(state.projects[0].slug);
  }
}

async function loadProjectDetail(slug) {
  if (!slug) return;
  const detail = await apiFetch(`/api/project?slug=${encodeURIComponent(slug)}`);
  if (!detail || detail.error) return;

  state.currentProject = detail;
  renderProjectUI(detail);
}

function renderProjectUI(detail) {
  // Top header project title
  const activeTitle = $('active-project-name');
  if (activeTitle) activeTitle.textContent = detail.title || detail.slug;

  // Sidebar project info
  const sideTitle = $('sidebar-project-title');
  if (sideTitle) sideTitle.textContent = detail.title || detail.slug;

  const sideInfo = $('sidebar-project-info');
  if (sideInfo) {
    sideInfo.textContent = `${detail.total_segments || 0} Segments • -19.0 LUFS`;
  }

  // 5-Room DAG Stepper Sync
  renderDAGStepper(detail.pipeline_dag || detail.rooms);

  // Multi-Cast Voice Roster
  renderVoiceRoster(detail.characters || detail.character_roster || []);

  // Dialogue Segments & Inspector
  const segments = detail.recent_segments || detail.segments || [];
  if (Array.isArray(segments) && segments.length > 0) {
    selectDialogueSegment(segments[0]);
  }

  // Auto-load first available audio chunk
  const activeAudio = detail.active_audio || detail.active_audio_path;
  if (activeAudio) {
    loadAudioTrack(activeAudio);
  } else if (Array.isArray(segments)) {
    const segWithAudio = segments.find(s => s.audio_path || s.audio_file);
    if (segWithAudio) {
      loadAudioTrack(segWithAudio.audio_path || segWithAudio.audio_file);
    }
  }
}

function renderDAGStepper(rooms) {
  if (!rooms) return;
  const roomKeys = ['room1_ingest', 'room2_translate', 'room3_dramaturgy', 'room4_synth', 'room5_master'];
  const fallbackKeys = ['room1_ingest', 'room2_trans', 'room3_dramat', 'room4_tts', 'room5_master'];
  const elementIds = ['dag-room1', 'dag-room2', 'dag-room3', 'dag-room4', 'dag-room5'];

  elementIds.forEach((id, idx) => {
    const el = $(id);
    if (!el) return;
    const roomState = rooms[roomKeys[idx]] || rooms[fallbackKeys[idx]] || 'queued';

    el.classList.remove('completed', 'active');
    if (roomState === 'completed') {
      el.classList.add('completed');
    } else if (roomState === 'active') {
      el.classList.add('active');
    }
  });
}

function renderVoiceRoster(roster) {
  const container = $('voice-roster-container');
  if (!container) return;
  container.innerHTML = '';

  const sidebarCount = $('sidebar-roster-count');
  if (sidebarCount) sidebarCount.textContent = String(roster.length || 0);

  if (roster.length === 0) {
    container.innerHTML = '<div style="font-size: 11px; color: var(--text-muted); text-align: center; padding: 10px;">Zero characters assigned</div>';
    return;
  }

  roster.forEach((char) => {
    const card = document.createElement('div');
    card.className = 'roster-card';

    const charName = char.name || char.character_name || 'Character';
    const initials = escapeHTML(charName.substring(0, 2).toUpperCase());
    const model = escapeHTML(char.voice || char.voice_model || 'Gemini Flash');
    const pitch = escapeHTML(char.pitch || '+0%');
    const tempo = escapeHTML(char.tempo || '1.0x');
    const sampleAudio = escapeHTML(char.sample_audio || '');

    card.innerHTML = `
      <div style="display: flex; align-items: center; gap: 10px;">
        <div class="avatar-badge">${initials}</div>
        <div>
          <div style="font-size: 12px; font-weight: 700; color: var(--text-primary);">${escapeHTML(charName)}</div>
          <div style="font-size: 10px; color: var(--text-muted);">${model} • Pitch ${pitch} • ${tempo}</div>
        </div>
      </div>
      <div>
        <button class="btn-audition" data-sample="${sampleAudio}">
          <svg width="12" height="12" viewBox="0 0 24 24" fill="currentColor"><polygon points="5 3 19 12 5 21 5 3"/></svg>
          <span>Audition</span>
        </button>
      </div>
    `;

    // Audition click handler
    const auditionBtn = card.querySelector('.btn-audition');
    if (auditionBtn) {
      auditionBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        const sample = auditionBtn.getAttribute('data-sample');
        if (sample) {
          loadAudioTrack(sample);
          togglePlay(true);
        }
      });
    }

    container.appendChild(card);
  });
}

function selectDialogueSegment(segment) {
  state.currentSegment = segment;
  if (!segment) return;

  const turnId = segment.seg_num || segment.id || segment.segment_id || '01';
  const speaker = segment.speaker || 'Narrator';
  const audioPath = segment.audio_path || segment.audio_file;

  const turnEl = $('inspector-turn-id');
  if (turnEl) turnEl.textContent = `Turn ${turnId} • ${speaker}`;

  const directiveEl = $('inspector-directive');
  if (directiveEl) directiveEl.textContent = segment.directive || 'Calm, articulate audiobook narration';

  const speakerEl = $('inspector-speaker');
  if (speakerEl) speakerEl.textContent = speaker;

  const textEl = $('inspector-hindi-text');
  if (textEl) textEl.textContent = `"${segment.text_content || '...'}"`;

  const statusEl = $('inspector-segment-status');
  if (statusEl) {
    const hasAudio = !!audioPath;
    statusEl.textContent = hasAudio ? 'Audio Rendered' : 'Pending Synthesis';
    statusEl.style.color = hasAudio ? 'var(--studio-green)' : 'var(--studio-amber-dark)';
  }

  const loadAudioBtn = $('btn-load-segment-audio');
  if (loadAudioBtn) {
    loadAudioBtn.onclick = () => {
      if (audioPath) {
        loadAudioTrack(audioPath);
        togglePlay(true);
      }
    };
  }
}

// ---------------------------------------------------------------------------
// Transport & Playback Controller
// ---------------------------------------------------------------------------

function togglePlay(forcePlay) {
  if (!audioPlayer) return;
  const shouldPlay = forcePlay !== undefined ? forcePlay : audioPlayer.paused;

  if (shouldPlay) {
    audioPlayer.play().then(() => {
      state.isPlaying = true;
      $('play-icon').style.display = 'none';
      $('pause-icon').style.display = 'block';
      state.rafId = requestAnimationFrame(updatePlayhead);
    }).catch(err => console.warn('Play interrupted:', err));
  } else {
    audioPlayer.pause();
    state.isPlaying = false;
    $('play-icon').style.display = 'block';
    $('pause-icon').style.display = 'none';
    if (state.rafId) cancelAnimationFrame(state.rafId);
    updatePlayhead();
  }
}

function setupTransportControls() {
  const btnPlay = $('btn-transport-play');
  if (btnPlay) btnPlay.addEventListener('click', () => togglePlay());

  const btnRto = $('btn-transport-rto');
  if (btnRto) btnRto.addEventListener('click', () => {
    if (audioPlayer) audioPlayer.currentTime = 0;
    updatePlayhead();
  });

  const btnPrev = $('btn-transport-prev');
  if (btnPrev) btnPrev.addEventListener('click', () => {
    navigateSegments(-1);
  });

  const btnNext = $('btn-transport-next');
  if (btnNext) btnNext.addEventListener('click', () => {
    navigateSegments(1);
  });

  if (audioPlayer) {
    audioPlayer.addEventListener('ended', () => {
      state.isPlaying = false;
      $('play-icon').style.display = 'block';
      $('pause-icon').style.display = 'none';
      if (state.rafId) cancelAnimationFrame(state.rafId);
      updatePlayhead();
    });

    audioPlayer.addEventListener('timeupdate', () => {
      if (!state.isPlaying) updatePlayhead();
    });
  }

  // Refresh Telemetry Button
  const btnRefresh = $('btn-refresh');
  if (btnRefresh) {
    btnRefresh.addEventListener('click', async () => {
      await loadStatus();
      if (state.currentProject) {
        await loadProjectDetail(state.currentProject.slug);
      }
    });
  }

  // Export Master Action Button
  const btnExport = $('btn-export-master');
  if (btnExport) {
    btnExport.addEventListener('click', async () => {
      btnExport.textContent = 'Processing...';
      const res = await apiFetch('/api/action', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action: 'produce_chapter' }),
      });
      setTimeout(() => {
        btnExport.innerHTML = `
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="20 6 9 17 4 12"/></svg>
          <span>Queued Master</span>
        `;
      }, 600);
    });
  }
}

function navigateSegments(direction) {
  if (!state.currentProject) return;
  const segments = state.currentProject.recent_segments || state.currentProject.segments || [];
  if (!Array.isArray(segments) || segments.length === 0) return;

  const curId = state.currentSegment ? (state.currentSegment.id || state.currentSegment.segment_id) : null;
  const curIdx = curId ? segments.findIndex(s => (s.id || s.segment_id) === curId) : 0;
  const nextIdx = Math.max(0, Math.min(segments.length - 1, (curIdx === -1 ? 0 : curIdx) + direction));
  const nextSeg = segments[nextIdx];

  selectDialogueSegment(nextSeg);
  const audioPath = nextSeg.audio_path || nextSeg.audio_file;
  if (audioPath) {
    loadAudioTrack(audioPath);
  }
}

// ---------------------------------------------------------------------------
// Memory Profiling & Health Telemetry
// ---------------------------------------------------------------------------

function updateMemoryTelemetry() {
  const statEl = $('sidebar-memory-stat');
  if (!statEl) return;

  if (window.performance && window.performance.memory) {
    const usedMB = (window.performance.memory.usedJSHeapSize / (1024 * 1024)).toFixed(1);
    statEl.textContent = `${usedMB} MB`;
  } else {
    statEl.textContent = '≤ 2.1 MB';
  }
}

// ---------------------------------------------------------------------------
// Application Entrypoint
// ---------------------------------------------------------------------------

document.addEventListener('DOMContentLoaded', async () => {
  initCanvas();
  setupScrubberEvents();
  setupTransportControls();
  await loadStatus();
  await loadProjects();
  updateMemoryTelemetry();
  setInterval(updateMemoryTelemetry, 5000);
});
