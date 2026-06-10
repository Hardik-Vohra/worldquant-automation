import json
import os
from pathlib import Path
from typing import Optional

import requests

from project.config import API_BASE, CONFIG_JSON, COOKIE_FILE


class AuthenticationError(Exception):
    pass


class AuthManager:
    def __init__(self, config_path: Optional[Path] = None, api_base: Optional[str] = None):
        self.config_path = Path(config_path) if config_path else CONFIG_JSON
        self.api_base = api_base or API_BASE
        self._data = self._load_config()

    def _load_config(self) -> dict:
        if self.config_path.exists():
            try:
                with self.config_path.open("r", encoding="utf-8") as handle:
                    data = json.load(handle)
                    if isinstance(data, dict):
                        self.api_base = data.get("api_base", self.api_base)
                        return data
            except Exception:
                pass
        return {"cookie": "", "api_base": self.api_base}

    def _save_config(self) -> None:
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        with self.config_path.open("w", encoding="utf-8") as handle:
            json.dump({"cookie": self._data.get("cookie", ""), "api_base": self.api_base}, handle, indent=2)

    def get_cookie(self) -> str:
        cookie = self._data.get("cookie") or os.getenv("WQB_COOKIE")
        if cookie:
            return self._normalize_cookie(cookie)

        if COOKIE_FILE.exists():
            return self._normalize_cookie(COOKIE_FILE.read_text().strip())

        raise AuthenticationError(
            "No WorldQuant cookie found. Please set WQB_COOKIE or add cookie to config.json."
        )

    def _normalize_cookie(self, cookie: str) -> str:
        cookie = cookie.strip()
        if cookie.startswith("t="):
            return cookie[2:]
        return cookie

    def _headers(self) -> dict:
        return {
            "Cookie": f"t={self.get_cookie()}",
            "Accept": "application/json;version=2.0",
            "Content-Type": "application/json",
        }

    def validate(self) -> None:
        cookie = self.get_cookie()
        if not cookie:
            self.request_cookie()
            return

        response = requests.get(f"{self.api_base}/authentication", headers=self._headers(), timeout=30)
        if response.status_code == 200:
            try:
                data = response.json()
                if isinstance(data, dict) and data.get("authenticated") is False:
                    self.request_cookie()
                    return
            except ValueError:
                pass
            return

        self.request_cookie()

    def request_cookie(self) -> str:
        prompt = (
            "WorldQuant authentication is missing or expired. "
            "Paste the cookie value (raw token or 't=...'): "
        )
        try:
            cookie = input(prompt).strip()
        except Exception as exc:
            raise AuthenticationError(
                "Unable to read cookie input. Please set WQB_COOKIE or write config.json manually."
            ) from exc

        if not cookie:
            raise AuthenticationError("Authentication cookie input was empty.")

        cookie = self._normalize_cookie(cookie)
        self._data["cookie"] = cookie
        self._save_config()
        return cookie
