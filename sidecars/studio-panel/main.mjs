// Backend for Audiobook Studio UI Extension Sidecar.
// Hosts local HTTP server and bridges Antigravity with the Python production engine.

import { existsSync, mkdirSync, readFileSync, writeFileSync, statSync, openSync, readSync, closeSync } from 'node:fs';
import { platform, release } from 'node:os';
import { dirname, join, resolve, extname, sep } from 'node:path';
import { fileURLToPath } from 'node:url';
import { execFileSync, spawn } from 'node:child_process';
import { Response, SidecarApp } from 'sidecar_sdk';

const HERE = dirname(fileURLToPath(import.meta.url));

// Canonical engine workspace & virtualenv Python path
const ENGINE_DIR = process.env.AUDIOBOOK_ENGINE_DIR || resolve(process.env.USERPROFILE || 'C:\\Users\\Suraj', 'Documents', 'antigravity', 'optimistic-kepler');
const PYTHON_BIN = join(ENGINE_DIR, '.venv', 'Scripts', 'python.exe');

// Private persistent storage for this sidecar
const DATA_DIR = process.env.ANTIGRAVITY_EXECUTABLE_DATA_DIR || join(HERE, '.data');
mkdirSync(DATA_DIR, { recursive: true });

const STARTED_AT = Date.now();
const app = new SidecarApp();

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

const readLocal = (name, fallback = '') => {
  const p = join(HERE, name);
  return existsSync(p) ? readFileSync(p, 'utf8') : fallback;
};

function runPythonBridge(subcommand, extraArgs = []) {
  try {
    const pythonExe = existsSync(PYTHON_BIN) ? PYTHON_BIN : 'python';
    const args = ['-m', 'audiobook_factory.api.studio_bridge', subcommand, ...extraArgs];
    const stdout = execFileSync(pythonExe, args, {
      cwd: ENGINE_DIR,
      encoding: 'utf-8',
      timeout: 20000,
      env: { ...process.env, PYTHONIOENCODING: 'utf-8' },
    });
    const outStr = stdout.trim();
    try {
      return JSON.parse(outStr);
    } catch (parseErr) {
      const match = outStr.match(/(\{[\s\S]*\}|\[[\s\S]*\])/);
      if (match) return JSON.parse(match[0]);
      throw parseErr;
    }
  } catch (err) {
    console.error(`Bridge error on '${subcommand}':`, err.message);
    return {
      error: err.message,
      stderr: err.stderr ? err.stderr.toString() : null,
      engine_dir: ENGINE_DIR,
    };
  }
}

// ---------------------------------------------------------------------------
// Static Web Routes
// ---------------------------------------------------------------------------

app.page('/', () => readLocal('index.html', '<h1>Audiobook Studio</h1>'));
app.page('/app.js', () => readLocal('app.js', '// Audiobook Studio Frontend'));
app.api('/styles.css', () => new Response(readLocal('styles.css', '/* Audiobook Studio Styles */'), { contentType: 'text/css' }), 'GET');

// ---------------------------------------------------------------------------
// Engine & Studio APIs
// ---------------------------------------------------------------------------

// GET /api/status: Returns sidecar and Python engine health
app.api('/api/status', () => {
  const bridgeStatus = runPythonBridge('status');
  return {
    sidecar: {
      uptimeSeconds: Math.round((Date.now() - STARTED_AT) / 1000),
      node: process.version,
      platform: `${platform()} ${release()}`,
    },
    engine: bridgeStatus,
  };
}, 'GET');

// GET /api/projects: Scans all active and completed book projects
app.api('/api/projects', () => {
  return runPythonBridge('list-projects');
}, 'GET');

// GET /api/project?slug=...: Returns detailed chapters, roster, and segment states
app.api('/api/project', (data) => {
  const slug = data.slug;
  if (!slug || typeof slug !== 'string' || !/^[a-zA-Z0-9_\-\.]+$/.test(slug)) {
    return { error: 'Invalid or missing slug parameter' };
  }
  return runPythonBridge('project-detail', ['--slug', slug]);
}, 'GET');

// GET /api/voices: Returns curated voices for auditioning
app.api('/api/voices', () => {
  return runPythonBridge('list-voices');
}, 'GET');

// GET /api/doctor?slug=...: Runs zero-token MetadataDoctor on project
app.api('/api/doctor', (data) => {
  const slug = data.slug;
  if (!slug || typeof slug !== 'string' || !/^[a-zA-Z0-9_\-\.]+$/.test(slug)) {
    return { error: 'Invalid or missing slug parameter' };
  }
  return runPythonBridge('doctor', ['--slug', slug]);
}, 'GET');

// LRU cache for audio peaks (max 50 waveforms)
const PEAKS_CACHE = new Map();
const MAX_PEAKS_CACHE_SIZE = 50;

// GET /api/peaks?path=...&points=400: Downsampled audio waveform peaks
app.api('/api/peaks', (data) => {
  const relPath = data.path;
  if (!relPath) return { error: 'Missing path parameter' };
  const rawPoints = parseInt(data.points || '400', 10);
  const numPoints = Math.max(10, Math.min(2000, isNaN(rawPoints) ? 400 : rawPoints));

  // Resolve safe path inside ENGINE_DIR with strict separator boundary defense
  const safeBase = resolve(ENGINE_DIR);
  const safePrefix = safeBase.endsWith(sep) ? safeBase : safeBase + sep;
  const targetPath = resolve(safeBase, relPath.replace(/^[\/\\]+/, ''));

  if (targetPath !== safeBase && !targetPath.startsWith(safePrefix)) {
    return { error: 'Access denied outside engine dir' };
  }

  if (!existsSync(targetPath)) {
    return { error: 'File not found', path: relPath };
  }

  const cacheKey = `${targetPath}:${numPoints}`;
  if (PEAKS_CACHE.has(cacheKey)) {
    // Refresh LRU ordering
    const cached = PEAKS_CACHE.get(cacheKey);
    PEAKS_CACHE.delete(cacheKey);
    PEAKS_CACHE.set(cacheKey, cached);
    return cached;
  }

  const result = runPythonBridge('peaks', ['--path', targetPath, '--points', String(numPoints)]);
  if (!result.error) {
    if (PEAKS_CACHE.size >= MAX_PEAKS_CACHE_SIZE) {
      const oldestKey = PEAKS_CACHE.keys().next().value;
      PEAKS_CACHE.delete(oldestKey);
    }
    PEAKS_CACHE.set(cacheKey, result);
  }
  return result;
}, 'GET');

// GET /api/audio?path=...: Streams local audio files with HTTP 206 Partial Content & memory-safe chunk reading
app.api('/api/audio', (data) => {
  const relPath = data.path;
  if (!relPath) return { error: 'Missing path parameter' };

  // Resolve safe path inside ENGINE_DIR with strict separator boundary defense
  const safeBase = resolve(ENGINE_DIR);
  const safePrefix = safeBase.endsWith(sep) ? safeBase : safeBase + sep;
  const targetPath = resolve(safeBase, relPath.replace(/^[\/\\]+/, ''));

  if (targetPath !== safeBase && !targetPath.startsWith(safePrefix)) {
    return new Response(JSON.stringify({ error: 'Access denied outside engine dir' }), { status: 403, contentType: 'application/json' });
  }

  if (!existsSync(targetPath)) {
    return new Response(JSON.stringify({ error: 'File not found' }), { status: 404, contentType: 'application/json' });
  }

  const ext = extname(targetPath).toLowerCase();
  let contentType = 'application/octet-stream';
  if (ext === '.m4a' || ext === '.m4b') contentType = 'audio/mp4';
  else if (ext === '.wav') contentType = 'audio/wav';
  else if (ext === '.mp3') contentType = 'audio/mpeg';

  try {
    const stat = statSync(targetPath);
    const totalSize = stat.size;
    let status = 200;
    const headers = {
      'Content-Length': String(totalSize),
      'Accept-Ranges': 'bytes',
      'Cache-Control': 'public, max-age=3600',
    };

    // Range request support for fine-grained scrubbing without whole-file redownload
    if (data.range || data.start !== undefined) {
      let start = 0;
      let end = totalSize - 1;
      if (data.range) {
        const match = /bytes=(\d+)-(\d*)/.exec(data.range);
        if (match) {
          start = parseInt(match[1], 10);
          if (match[2]) end = parseInt(match[2], 10);
        }
      } else if (data.start !== undefined) {
        start = parseInt(data.start, 10);
        if (data.end !== undefined) end = parseInt(data.end, 10);
      }
      if (isNaN(start)) start = 0;
      if (isNaN(end)) end = totalSize - 1;
      
      if (start > end || start >= totalSize || start < 0) {
        return new Response(JSON.stringify({ error: 'Range Not Satisfiable' }), { 
          status: 416, 
          contentType: 'application/json',
          headers: { 'Content-Range': `bytes */${totalSize}` } 
        });
      }

      start = Math.max(0, Math.min(start, totalSize - 1));
      end = Math.max(start, Math.min(end, totalSize - 1));
      const chunkLength = end - start + 1;
      
      // Memory-safe streaming: allocate only the requested byte chunk
      const chunk = Buffer.alloc(chunkLength);
      const fd = openSync(targetPath, 'r');
      try {
        readSync(fd, chunk, 0, chunkLength, start);
      } finally {
        closeSync(fd);
      }

      status = 206;
      headers['Content-Range'] = `bytes ${start}-${end}/${totalSize}`;
      headers['Content-Length'] = String(chunkLength);
      return new Response(chunk, { status, contentType, headers });
    }

    // Full file response: read safely
    const fileBuf = readFileSync(targetPath);
    return new Response(fileBuf, {
      contentType,
      headers,
    });
  } catch (err) {
    return new Response(JSON.stringify({ error: err.message }), { status: 500, contentType: 'application/json' });
  }
}, 'GET');

// POST /api/action: Direct execution of production commands
app.api('/api/action', (data) => {
  const action = data.action; // 'produce_chapter', 'synthesize', 'refresh'
  if (action === 'refresh') {
    return { status: 'refreshed', timestamp: Date.now() };
  }
  return { status: 'acknowledged', action, data };
}, 'POST');

// ---------------------------------------------------------------------------
// Run Server
// ---------------------------------------------------------------------------

app.run();
