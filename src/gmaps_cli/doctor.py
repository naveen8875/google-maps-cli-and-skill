"""Environment diagnostics for the CLI."""

from __future__ import annotations

import os
import platform
from importlib.util import find_spec


def run_diagnostics() -> dict[str, object]:
    proxy_vars = {
        key: os.getenv(key)
        for key in ["HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "NO_PROXY"]
    }
    return {
        "python_version": platform.python_version(),
        "platform": platform.platform(),
        "modules": {
            "click": find_spec("click") is not None,
            "pydantic": find_spec("pydantic") is not None,
            "yaml": find_spec("yaml") is not None,
            "selenium": find_spec("selenium") is not None,
            "webdriver_manager": find_spec("webdriver_manager") is not None,
        },
        "proxy_env": proxy_vars,
        "notes": [
            "The current backend uses selenium plus webdriver-manager.",
            "Chrome must be available locally for real scraping runs.",
            "Unauthenticated http/https/socks proxies can be passed into the Selenium browser session.",
            "Authenticated proxy URLs with embedded credentials are not yet automated in Selenium.",
        ],
    }
