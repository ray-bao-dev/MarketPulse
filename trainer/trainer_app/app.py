from __future__ import annotations

import os
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, HTMLResponse
from pydantic import BaseModel, Field

from trainer_app.config import settings
from trainer_app.jobs import get_status, start_job

app = FastAPI(title="MarketPulse Trainer", version="0.1.0")

ARTIFACTS = Path(settings.artifacts_dir)


HTML_PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>MarketPulse Trainer</title>
  <style>
    * { box-sizing: border-box; }
    body { font-family: system-ui, sans-serif; background: #09090b; color: #fafafa; margin: 0; padding: 24px; }
    h1 { font-size: 1.25rem; margin: 0 0 4px; }
    p.sub { color: #71717a; font-size: 0.875rem; margin: 0 0 20px; }
    form { display: grid; gap: 12px; max-width: 480px; margin-bottom: 20px; }
    label { font-size: 0.75rem; color: #a1a1aa; text-transform: uppercase; letter-spacing: 0.05em; }
    input, select { width: 100%; padding: 8px 10px; background: #18181b; border: 1px solid #27272a; color: #fafafa; border-radius: 4px; }
    button { padding: 10px 16px; background: #f59e0b; color: #09090b; border: none; border-radius: 4px; font-weight: 600; cursor: pointer; }
    button:disabled { opacity: 0.5; cursor: not-allowed; }
    .status { padding: 12px; background: #18181b; border: 1px solid #27272a; border-radius: 4px; margin-bottom: 12px; font-size: 0.875rem; }
    .status.running { border-color: #f59e0b; }
    .status.done { border-color: #34d399; }
    .status.error { border-color: #f87171; }
    pre { background: #18181b; border: 1px solid #27272a; border-radius: 4px; padding: 12px; font-size: 0.75rem; max-height: 320px; overflow: auto; white-space: pre-wrap; }
    .downloads a { color: #f59e0b; margin-right: 16px; }
  </style>
</head>
<body>
  <h1>MarketPulse Trainer</h1>
  <p class="sub">Generate dataset from Railway PostgreSQL, train CNN, export ONNX — one click.</p>

  <form id="form">
    <div>
      <label for="symbols">Symbols (comma-separated)</label>
      <input id="symbols" name="symbols" value="__SYMBOLS__" required />
    </div>
    <div>
      <label for="timeframe">Timeframe</label>
      <select id="timeframe" name="timeframe">
        <option value="5Min" selected>5Min</option>
        <option value="1Hour">1Hour</option>
        <option value="1Day">1Day</option>
      </select>
    </div>
    <div>
      <label for="start">Start date</label>
      <input id="start" name="start" type="date" value="__START__" required />
    </div>
    <div>
      <label for="epochs">Epochs</label>
      <input id="epochs" name="epochs" type="number" value="8" min="1" max="50" />
    </div>
    <div>
      <label for="max_per_class">Max samples per class</label>
      <input id="max_per_class" name="max_per_class" type="number" value="10000" min="100" />
    </div>
    <button type="submit" id="runBtn">Run training pipeline</button>
  </form>

  <div id="statusBox" class="status">Status: idle</div>
  <div id="downloads" class="downloads" style="display:none">
    <a href="/api/download/onnx">Download patterns.onnx</a>
    <a href="/api/download/manifest">Download manifest.json</a>
  </div>
  <pre id="logs">Waiting to start…</pre>

  <script>
    const form = document.getElementById('form');
    const runBtn = document.getElementById('runBtn');
    const statusBox = document.getElementById('statusBox');
    const logsEl = document.getElementById('logs');
    const downloads = document.getElementById('downloads');
    let pollTimer = null;

    form.addEventListener('submit', async (e) => {
      e.preventDefault();
      runBtn.disabled = true;
      const body = {
        symbols: document.getElementById('symbols').value,
        timeframe: document.getElementById('timeframe').value,
        start: document.getElementById('start').value,
        epochs: Number(document.getElementById('epochs').value),
        max_per_class: Number(document.getElementById('max_per_class').value),
      };
      const res = await fetch('/api/run', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        alert(err.detail || 'Failed to start');
        runBtn.disabled = false;
        return;
      }
      if (pollTimer) clearInterval(pollTimer);
      pollTimer = setInterval(refreshStatus, 2000);
      refreshStatus();
    });

    async function refreshStatus() {
      const res = await fetch('/api/status');
      const data = await res.json();
      statusBox.textContent = 'Status: ' + data.state + (data.step ? ' — ' + data.step : '');
      statusBox.className = 'status ' + data.state;
      logsEl.textContent = (data.logs || []).join("\\n") || "No logs yet.";
      if (data.state === 'done') {
        downloads.style.display = 'block';
        runBtn.disabled = false;
        clearInterval(pollTimer);
      }
      if (data.state === 'error') {
        runBtn.disabled = false;
        clearInterval(pollTimer);
      }
      if (data.state === 'idle') runBtn.disabled = false;
    }

    refreshStatus();
    setInterval(refreshStatus, 5000);
  </script>
</body>
</html>
"""


class RunRequest(BaseModel):
    symbols: str = Field(default="SPY,QQQ,AAPL")
    timeframe: str = Field(default="5Min")
    start: str = Field(..., min_length=8)
    epochs: int = Field(default=8, ge=1, le=50)
    max_per_class: int = Field(default=10_000, ge=100, le=100_000)


@app.get("/health")
async def health() -> dict:
    return {
        "status": "ok",
        "database_configured": bool(settings.resolved_database_url),
    }


@app.get("/", response_class=HTMLResponse)
async def index() -> HTMLResponse:
    html = (
        HTML_PAGE.replace("__SYMBOLS__", settings.default_symbols)
        .replace("__START__", settings.default_start)
    )
    return HTMLResponse(html)


@app.get("/api/status")
async def status() -> dict:
    return get_status().to_dict()


@app.post("/api/run")
async def run_pipeline(body: RunRequest) -> dict:
    symbols = [s.strip().upper() for s in body.symbols.split(",") if s.strip()]
    if not symbols:
        raise HTTPException(status_code=400, detail="At least one symbol required")

    started = start_job(
        symbols=symbols,
        timeframe=body.timeframe,
        start=body.start,
        epochs=body.epochs,
        max_per_class=body.max_per_class,
    )
    if not started:
        raise HTTPException(status_code=409, detail="A job is already running")
    return {"ok": True}


@app.get("/api/download/onnx")
async def download_onnx() -> FileResponse:
    path = ARTIFACTS / "patterns.onnx"
    if not path.is_file():
        raise HTTPException(status_code=404, detail="patterns.onnx not found — run training first")
    return FileResponse(path, filename="patterns.onnx", media_type="application/octet-stream")


@app.get("/api/download/manifest")
async def download_manifest() -> FileResponse:
    path = ARTIFACTS / "manifest.json"
    if not path.is_file():
        raise HTTPException(status_code=404, detail="manifest.json not found")
    return FileResponse(path, filename="manifest.json", media_type="application/json")
