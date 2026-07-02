#!/usr/bin/env python3
import os

import uvicorn

from classifier.app import app

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", "8080")))
