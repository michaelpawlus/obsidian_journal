from __future__ import annotations

from anthropic import Anthropic
from rich.console import Console
from rich.markdown import Markdown

from obsidian_journal.config import Config
from obsidian_journal.models import ConversationMessage, WeatherInfo
from obsidian_journal.plan.prompts import (
    PLAN_SYSTEM_PROMPT,
    PLAN_OPENING_QUESTION,
    PLAN_WEATHER_CONTEXT,
    PLAN_EXISTING_NOTE_CONTEXT,
)

console = Console()


def run_plan_conversation(
    config: Config,
    weather: WeatherInfo | None = None,
    existing_content: str | None = None,
) -> list[ConversationMessage]:
    client = Anthropic(api_key=config.anthropic_api_key)
    messages: list[ConversationMessage] = []
    api_messages: list[dict[str, str]] = []

    # Build system prompt with optional weather and existing note context
    system = PLAN_SYSTEM_PROMPT
    if weather:
        system += "\n\n" + PLAN_WEATHER_CONTEXT.format(
            weather_summary=weather.summary,
            best_outdoor_window=weather.best_outdoor_window,
            sunrise=weather.sunrise,
            sunset=weather.sunset,
        )
    if existing_content:
        system += "\n\n" + PLAN_EXISTING_NOTE_CONTEXT.format(
            existing_content=existing_content[:2000],
        )

    # Show opening question
    console.print()
    console.print(Markdown(f"**Plan Assistant:** {PLAN_OPENING_QUESTION}"))
    console.print()
    messages.append(ConversationMessage(role="assistant", content=PLAN_OPENING_QUESTION))

    for round_num in range(config.max_rounds):
        try:
            user_input = console.input("[bold cyan]You:[/bold cyan] ").strip()
        except (EOFError, KeyboardInterrupt):
            console.print("\n[dim]Session ended.[/dim]")
            break

        if not user_input:
            continue

        if user_input.lower() == "done":
            console.print("[dim]Building your plan...[/dim]")
            break

        messages.append(ConversationMessage(role="user", content=user_input))
        api_messages.append({"role": "user", "content": user_input})

        # Last round — move to synthesis
        if round_num == config.max_rounds - 1:
            console.print()
            console.print("[dim]Got it. Let me put your plan together...[/dim]")
            break

        # Get follow-up question from Claude
        response = client.messages.create(
            model=config.model,
            max_tokens=300,
            system=system,
            messages=api_messages,
        )
        assistant_text = response.content[0].text
        messages.append(ConversationMessage(role="assistant", content=assistant_text))
        api_messages.append({"role": "assistant", "content": assistant_text})

        console.print()
        console.print(Markdown(f"**Plan Assistant:** {assistant_text}"))
        console.print()

    return messages
