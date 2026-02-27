from __future__ import annotations

from anthropic import Anthropic
from rich.console import Console
from rich.markdown import Markdown

from obsidian_journal.config import Config
from obsidian_journal.journal.prompts import OPENING_QUESTIONS, SYSTEM_PROMPT
from obsidian_journal.models import ConversationMessage, ReflectionType

console = Console()


def run_conversation(
    config: Config, reflection_type: ReflectionType
) -> list[ConversationMessage]:
    client = Anthropic(api_key=config.anthropic_api_key)
    opening = OPENING_QUESTIONS[reflection_type]
    messages: list[ConversationMessage] = []
    api_messages: list[dict[str, str]] = []

    # Show the opening question
    console.print()
    console.print(Markdown(f"**Journal Assistant:** {opening}"))
    console.print()
    messages.append(ConversationMessage(role="assistant", content=opening))

    for round_num in range(config.max_rounds):
        # Get user input
        try:
            user_input = console.input("[bold cyan]You:[/bold cyan] ").strip()
        except (EOFError, KeyboardInterrupt):
            console.print("\n[dim]Session ended.[/dim]")
            break

        if not user_input:
            continue

        if user_input.lower() == "done":
            console.print("[dim]Wrapping up your reflection...[/dim]")
            break

        messages.append(ConversationMessage(role="user", content=user_input))
        api_messages.append({"role": "user", "content": user_input})

        # Last round — don't ask another question
        if round_num == config.max_rounds - 1:
            console.print()
            console.print(
                "[dim]We've had a good conversation. Let me synthesize your reflection...[/dim]"
            )
            break

        # Get Claude's follow-up question
        response = client.messages.create(
            model=config.model,
            max_tokens=300,
            system=SYSTEM_PROMPT,
            messages=api_messages,
        )
        assistant_text = response.content[0].text
        messages.append(ConversationMessage(role="assistant", content=assistant_text))
        api_messages.append({"role": "assistant", "content": assistant_text})

        console.print()
        console.print(Markdown(f"**Journal Assistant:** {assistant_text}"))
        console.print()

    return messages
