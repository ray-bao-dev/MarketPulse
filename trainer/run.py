#!/usr/bin/env python3
import os
import sys
from pathlib import Path

# Repo layout: /app/classifier + /app/trainer
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "classifier"))

import uvicorn

from trainer_app.app import app

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", "8090")))
