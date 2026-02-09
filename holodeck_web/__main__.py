# -*- coding: utf-8 -*-
"""Run Holodeck Web server."""

import uvicorn
from holodeck_web.app import app

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
