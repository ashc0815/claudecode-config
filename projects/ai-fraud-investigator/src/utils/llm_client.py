"""Claude API client wrapper."""

from __future__ import annotations

import os

import anthropic
import yaml


def load_config() -> dict:
    config_path = os.path.join(
        os.path.dirname(__file__), "..", "..", "config", "settings.yaml"
    )
    with open(config_path) as f:
        return yaml.safe_load(f)


class LLMClient:
    """Wrapper around Claude API for agent interactions."""

    def __init__(self):
        self.config = load_config()["llm"]
        self.client = anthropic.Anthropic()

    def query(
        self,
        system_prompt: str,
        user_message: str,
        temperature: float | None = None,
    ) -> str:
        """Send a query to Claude and return the text response."""
        message = self.client.messages.create(
            model=self.config["model"],
            max_tokens=self.config["max_tokens"],
            temperature=temperature or self.config["temperature"],
            system=system_prompt,
            messages=[{"role": "user", "content": user_message}],
        )
        return message.content[0].text

    def query_structured(
        self,
        system_prompt: str,
        user_message: str,
        output_schema: dict,
    ) -> str:
        """Query Claude with instructions to return structured JSON."""
        structured_prompt = (
            f"{system_prompt}\n\n"
            "You MUST respond with valid JSON matching this schema:\n"
            f"{output_schema}\n"
            "Respond ONLY with the JSON object, no other text."
        )
        return self.query(structured_prompt, user_message, temperature=0.1)
