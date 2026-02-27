from __future__ import annotations

from anthropic import Anthropic

from obsidian_journal.config import Config


def analyze_content(config: Config, prompt: str, content: str) -> str:
    client = Anthropic(api_key=config.anthropic_api_key)
    response = client.messages.create(
        model=config.model,
        max_tokens=1500,
        system=prompt,
        messages=[{"role": "user", "content": content}],
    )
    return response.content[0].text.strip()
