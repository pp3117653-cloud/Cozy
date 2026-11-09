"""Small, dependency-free connectors used by Cozy's GitHub Actions worker."""
from __future__ import annotations

import json
import os
import pathlib
import time
import urllib.error
import urllib.request
from typing import Any


class ConnectorError(RuntimeError):
    pass


def _post_json(url: str, payload: dict[str, Any], headers: dict[str, str] | None = None, timeout: int = 15) -> dict[str, Any]:
    body = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(url, data=body, method="POST", headers={"Content-Type": "application/json", **(headers or {})})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read().decode("utf-8", errors="replace")
            return {"status": response.status, "body": raw[:2000]}
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:1000]
        raise ConnectorError(f"HTTP {exc.code}: {detail}") from exc
    except (urllib.error.URLError, TimeoutError) as exc:
        raise ConnectorError(str(exc)) from exc


class WhatsAppConnector:
    name = "whatsapp"

    def send(self, message: str) -> dict[str, Any]:
        token = os.getenv("WHATSAPP_ACCESS_TOKEN")
        phone_id = os.getenv("WHATSAPP_PHONE_NUMBER_ID")
        recipient = os.getenv("WHATSAPP_TO_NUMBER")
        if not all((token, phone_id, recipient)):
            return {"skipped": True, "reason": "WhatsApp secrets are not configured"}
        url = f"https://graph.facebook.com/v20.0/{phone_id}/messages"
        payload = {"messaging_product": "whatsapp", "to": recipient, "type": "text", "text": {"body": message[:4096]}}
        return _post_json(url, payload, {"Authorization": f"Bearer {token}"})


class SheetsConnector:
    name = "sheets"

    def send(self, record: dict[str, Any]) -> dict[str, Any]:
        url = os.getenv("GOOGLE_SHEETS_WEBHOOK_URL")
        if not url:
            return {"skipped": True, "reason": "GOOGLE_SHEETS_WEBHOOK_URL is not configured"}
        return _post_json(url, record)


class DiscordConnector:
    name = "discord"

    def send(self, message: str, task_id: str, status: str) -> dict[str, Any]:
        url = os.getenv("DISCORD_WEBHOOK_URL")
        if not url:
            return {"skipped": True, "reason": "DISCORD_WEBHOOK_URL is not configured"}
        payload = {"embeds": [{"title": f"Cozy task {status}", "description": message[:4000], "color": 5763719 if status == "completed" else 15548997, "fields": [{"name": "Task ID", "value": task_id, "inline": True}, {"name": "Status", "value": status, "inline": True}]}]}
        return _post_json(url, payload)


class FileConnector:
    name = "files"

    def __init__(self, root: str | pathlib.Path = ".") -> None:
        self.root = pathlib.Path(root).resolve()

    def write_report(self, task_id: str, markdown: str) -> str:
        logs = self.root / "logs"
        logs.mkdir(parents=True, exist_ok=True)
        path = logs / f"{task_id}.md"
        path.write_text(markdown.rstrip() + "\n", encoding="utf-8")
        return str(path.relative_to(self.root))

    def read_text(self, relative_path: str) -> str:
        path = (self.root / relative_path).resolve()
        if self.root not in path.parents and path != self.root:
            raise ConnectorError("Path escapes the workspace")
        return path.read_text(encoding="utf-8")

    def write_text(self, relative_path: str, content: str) -> str:
        path = (self.root / relative_path).resolve()
        if self.root not in path.parents:
            raise ConnectorError("Path escapes the workspace")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return str(path.relative_to(self.root))


def retry(operation, attempts: int = 3, delay: float = 1.5):
    last_error = None
    for index in range(attempts):
        try:
            return operation()
        except ConnectorError as exc:
            last_error = exc
            if index + 1 < attempts:
                time.sleep(delay * (index + 1))
    raise last_error or ConnectorError("operation failed")
