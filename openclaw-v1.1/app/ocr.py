"""OCR module — Mistral OCR API for Chinese invoice text extraction."""

import logging
from typing import Optional

import httpx

from .config import settings

logger = logging.getLogger(__name__)

MISTRAL_OCR_URL = "https://api.mistral.ai/v1/ocr"


async def extract_text(image_url: str) -> dict:
    """Extract text from a voucher image using Mistral OCR.

    Returns:
        {
            "raw_text": "full extracted text",
            "confidence": 0.0-1.0,
            "pages": [{"text": "...", "confidence": 0.95}]
        }
    """
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(
            MISTRAL_OCR_URL,
            headers={
                "Authorization": f"Bearer {settings.mistral_api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": "mistral-ocr-latest",
                "document": {"type": "image_url", "image_url": image_url},
            },
        )
        resp.raise_for_status()
        data = resp.json()

    # Normalize response
    pages = data.get("pages", [])
    raw_text = "\n".join(p.get("markdown", p.get("text", "")) for p in pages)
    avg_confidence = (
        sum(p.get("confidence", 0.8) for p in pages) / len(pages) if pages else 0.0
    )

    return {
        "raw_text": raw_text,
        "confidence": round(avg_confidence, 2),
        "pages": pages,
    }


async def extract_text_from_base64(image_base64: str, mime_type: str = "image/jpeg") -> dict:
    """Extract text from a base64-encoded image."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(
            MISTRAL_OCR_URL,
            headers={
                "Authorization": f"Bearer {settings.mistral_api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": "mistral-ocr-latest",
                "document": {
                    "type": "base64",
                    "base64": image_base64,
                    "mime_type": mime_type,
                },
            },
        )
        resp.raise_for_status()
        data = resp.json()

    pages = data.get("pages", [])
    raw_text = "\n".join(p.get("markdown", p.get("text", "")) for p in pages)
    avg_confidence = (
        sum(p.get("confidence", 0.8) for p in pages) / len(pages) if pages else 0.0
    )

    return {
        "raw_text": raw_text,
        "confidence": round(avg_confidence, 2),
        "pages": pages,
    }
