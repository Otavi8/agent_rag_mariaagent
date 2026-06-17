from __future__ import annotations

from typing import Any
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import httpx

from .config import Settings


def normalize_whatsapp_jid(value: str | None) -> str | None:
    if not value:
        return None
    return value.split(":")[0].split("@")[0].strip() or None


def is_group_jid(value: str | None) -> bool:
    return bool(value and "@g.us" in value)


def is_newsletter_jid(value: str | None) -> bool:
    return bool(value and "@newsletter" in value)


def build_whatsapp_conversation_id(instance_id: str, phone_number: str) -> str:
    return f"wa:{instance_id}:{phone_number}"


def extract_text_from_message_data(data: dict[str, Any]) -> str | None:
    message = data.get("Message")
    if not isinstance(message, dict):
        return None

    conversation = message.get("conversation")
    if isinstance(conversation, str) and conversation.strip():
        return conversation.strip()

    extended = message.get("extendedTextMessage")
    if isinstance(extended, dict):
        text = extended.get("text")
        if isinstance(text, str) and text.strip():
            return text.strip()

    for media_key in ("imageMessage", "videoMessage", "documentMessage"):
        media = message.get(media_key)
        if isinstance(media, dict):
            caption = media.get("caption")
            if isinstance(caption, str) and caption.strip():
                return caption.strip()

    return None


def append_webhook_secret(url: str, secret: str | None) -> str:
    if not secret:
        return url

    parts = urlsplit(url)
    query = dict(parse_qsl(parts.query, keep_blank_values=True))
    query.setdefault("token", secret)
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query), parts.fragment))


class EvolutionGoClient:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.base_url = settings.evolution_base_url.rstrip("/")

    def _headers(self, instance_id: str | None = None) -> dict[str, str]:
        if not self.settings.evolution_api_key:
            raise RuntimeError("EVOLUTION_API_KEY is required to call Evolution Go.")

        headers = {
            "apikey": self.settings.evolution_api_key,
            "Content-Type": "application/json",
        }
        if instance_id:
            headers["instanceId"] = instance_id
        return headers

    def health(self) -> dict[str, Any]:
        with httpx.Client(timeout=20.0) as client:
            response = client.get(f"{self.base_url}/")
            response.raise_for_status()
            if response.headers.get("content-type", "").startswith("application/json"):
                return response.json()
            return {"raw": response.text}

    def create_instance(
        self,
        instance_name: str,
        integration: str = "WHATSAPP-BAILEYS",
    ) -> dict[str, Any]:
        payload = {
            "instanceName": instance_name,
            "integration": integration,
        }
        with httpx.Client(timeout=30.0) as client:
            response = client.post(
                f"{self.base_url}/instance/create",
                headers=self._headers(),
                json=payload,
            )
            response.raise_for_status()
            return response.json()

    def connect_instance(
        self,
        instance_id: str,
        subscribe: list[str],
        immediate: bool = True,
        phone: str | None = None,
        webhook_url: str | None = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "subscribe": subscribe,
            "immediate": immediate,
        }
        if phone:
            payload["phone"] = phone
        if webhook_url:
            payload["webhookUrl"] = append_webhook_secret(
                webhook_url, self.settings.evolution_webhook_secret
            )

        with httpx.Client(timeout=30.0) as client:
            response = client.post(
                f"{self.base_url}/instance/connect",
                headers=self._headers(instance_id=instance_id),
                json=payload,
            )
            response.raise_for_status()
            return response.json()

    def send_text(
        self,
        number: str,
        text: str,
        instance_name: str | None = None,
        delay: int = 0,
    ) -> dict[str, Any]:
        resolved_instance_name = instance_name or self.settings.evolution_instance_name
        payload = {
            "number": number,
            "textMessage": {"text": text},
            "delay": delay,
        }
        with httpx.Client(timeout=30.0) as client:
            response = client.post(
                f"{self.base_url}/message/sendText/{resolved_instance_name}",
                headers=self._headers(),
                json=payload,
            )
            response.raise_for_status()
            return response.json()
