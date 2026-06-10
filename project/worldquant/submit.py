import time
import requests
from project.config import API_BASE, SUBMISSION_SETTINGS
from project.auth import AuthManager, AuthenticationError


class WorldQuantClient:
    def __init__(self, auth_manager: AuthManager = None):
        self.auth_manager = auth_manager or AuthManager()
        self.session = requests.Session()
        self._refresh_auth()

    def _refresh_auth(self):
        self.auth_manager.validate()
        cookie = self.auth_manager.get_cookie()
        self.session.headers.update({
            "Cookie": f"t={cookie}",
            "Accept": "application/json;version=2.0",
            "Content-Type": "application/json",
        })

    def _request(self, method: str, url: str, allowed_statuses=None, **kwargs):
        allowed_statuses = allowed_statuses or {200, 201, 202}
        response = self.session.request(method, url, timeout=kwargs.pop("timeout", 60), **kwargs)
        if response.status_code in {401, 403}:
            self.auth_manager.request_cookie()
            self._refresh_auth()
            response = self.session.request(method, url, timeout=kwargs.pop("timeout", 60), **kwargs)
        if response.status_code in allowed_statuses:
            return response
        if response.status_code in {401, 403}:
            raise AuthenticationError(
                "WorldQuant authentication failed after refresh. Please update the cookie."
            )
        raise RuntimeError(
            f"Request failed {response.status_code}: {response.text[:500]}"
        )

    def submit_alpha(self, alpha: str, settings: dict = None) -> str:
        payload = {
            "type": "REGULAR",
            "settings": settings or SUBMISSION_SETTINGS,
            "regular": alpha,
        }
        while True:
            response = self._request(
                "POST",
                f"{API_BASE}/simulations",
                allowed_statuses={200, 201, 202, 429},
                json=payload,
                timeout=60,
            )
            if response.status_code == 429:
                retry_after = int(float(response.headers.get("Retry-After", 10)))
                time.sleep(retry_after + 1)
                continue
            location = response.headers.get("Location")
            if not location:
                raise RuntimeError("Submit returned no Location header")
            return location.split("/")[-1]

    def fetch_simulation(self, sim_id: str) -> dict:
        response = self._request("GET", f"{API_BASE}/simulations/{sim_id}", timeout=30)
        return response.json()

    def fetch_alpha(self, alpha_id: str) -> dict:
        response = self._request("GET", f"{API_BASE}/alphas/{alpha_id}", timeout=30)
        return response.json()
