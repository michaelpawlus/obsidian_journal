from __future__ import annotations

from datetime import date

from anthropic import Anthropic

from obsidian_journal.config import Config
from obsidian_journal.models import ConversationMessage, Frontmatter, Note, ReflectionType

SYNTHESIZE_SYSTEM = """\
You are a note synthesizer. Given a journaling conversation, produce a well-structured \
Obsidian markdown note that captures the key reflections, insights, and action items.

Rules:
- Write in first person from the journaler's perspective
- Use clear headings (##) to organize themes
- Include [[wikilinks]] to any related notes from the provided list of existing note titles \
(only link titles that are genuinely relevant)
- Keep the tone authentic — match the journaler's voice, don't over-polish
- End with a "## Takeaways" section with 2-4 bullet points
- Do NOT include YAML frontmatter — that will be added separately
- Do NOT include a top-level title (# Title) — the filename serves as the title

Respond with ONLY the note body (markdown content). No preamble or explanation.\
"""

TITLE_SYSTEM = """\
Generate a short, descriptive title (3-7 words) for a journal entry based on the conversation. \
The title should capture the main theme. Respond with ONLY the title, no quotes or punctuation.\
"""


def synthesize_note(
    config: Config,
    messages: list[ConversationMessage],
    reflection_type: ReflectionType,
    existing_titles: list[str],
) -> Note:
    client = Anthropic(api_key=config.anthropic_api_key)
    today = date.today().isoformat()

    # Build conversation transcript
    transcript = "\n\n".join(
        f"{'User' if m.role == 'user' else 'Assistant'}: {m.content}"
        for m in messages
    )

    titles_str = ", ".join(existing_titles[:200])

    # Generate note body
    body_response = client.messages.create(
        model=config.model,
        max_tokens=2000,
        system=SYNTHESIZE_SYSTEM,
        messages=[
            {
                "role": "user",
                "content": (
                    f"Conversation transcript:\n\n{transcript}\n\n"
                    f"Existing note titles in vault: {titles_str}\n\n"
                    f"Reflection type: {reflection_type.value}"
                ),
            }
        ],
    )
    body = body_response.content[0].text.strip()

    # Generate title
    title_response = client.messages.create(
        model=config.model,
        max_tokens=50,
        system=TITLE_SYSTEM,
        messages=[
            {"role": "user", "content": f"Conversation:\n\n{transcript}"}
        ],
    )
    title = title_response.content[0].text.strip()

    # Extract wikilinks as related notes
    related = []
    for t in existing_titles:
        if f"[[{t}]]" in body:
            related.append(t)

    # Build tags from reflection type
    tags = [f"journal/{reflection_type.value}"]

    front = Frontmatter(
        date=today,
        type=reflection_type.value,
        tags=tags,
        related=related,
    )

    return Note(
        title=f"{today} {title}",
        body=body,
        frontmatter=front,
        folder="Journal",
    )
