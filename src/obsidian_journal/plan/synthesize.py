from __future__ import annotations

from anthropic import Anthropic

from obsidian_journal.config import Config
from obsidian_journal.models import ConversationMessage, WeatherInfo

PLAN_SYNTHESIZE_SYSTEM = """\
You are a daily planning assistant. Given a conversation about someone's day, produce a \
well-structured daily plan in Obsidian markdown format.

Output format:
## Plan

### Weather
(One line summary of today's weather and its impact on scheduling. Omit this section entirely if no weather data is provided.)

### Schedule
A time-blocked schedule for the day. Format each block as:

- **HH:MM - HH:MM** | Task description [priority]
  - Sub-details or notes if relevant

Use these priority markers: [HIGH], [MED], [LOW]
Mark fixed commitments (meetings, appointments) with a clock emoji.
Mark outdoor activities with a sun emoji when weather is favorable.

### Overflow (Tomorrow)
If there are tasks that don't fit today, list them here with brief reasoning. \
If everything fits, omit this section.
- Task — reason it was deferred

Rules:
- Fixed-time commitments (meetings, appointments) anchor the schedule; build around them
- If the user mentioned wanting to work out or be outside, schedule it during the best \
weather window if conditions are good
- If too many tasks for one day, push lower-priority items to the Overflow section
- Include brief transition time between tasks (don't schedule back-to-back unless necessary)
- Respect energy: put deep/creative work in the morning, routine tasks in the afternoon \
(unless the user indicated otherwise)
- Be realistic about time estimates — pad slightly for context switching
- Do NOT include YAML frontmatter
- Do NOT include a top-level # heading

{weather_context}

Respond with ONLY the plan markdown. No preamble or explanation.\
"""


def synthesize_plan(
    config: Config,
    messages: list[ConversationMessage],
    weather: WeatherInfo | None,
    date_str: str,
) -> str:
    client = Anthropic(api_key=config.anthropic_api_key)

    transcript = "\n\n".join(
        f"{'User' if m.role == 'user' else 'Assistant'}: {m.content}"
        for m in messages
    )

    weather_context = ""
    if weather:
        weather_context = (
            f"Weather for today:\n"
            f"- Conditions: {weather.condition}\n"
            f"- High: {weather.temperature_high_f:.0f}F, Low: {weather.temperature_low_f:.0f}F\n"
            f"- Precipitation chance: {weather.precipitation_chance}%\n"
            f"- Wind: {weather.wind_speed_mph:.0f} mph\n"
            f"- Best outdoor window: {weather.best_outdoor_window}\n"
            f"- Sunrise: {weather.sunrise}, Sunset: {weather.sunset}"
        )

    system_prompt = PLAN_SYNTHESIZE_SYSTEM.format(weather_context=weather_context)

    response = client.messages.create(
        model=config.model,
        max_tokens=2000,
        system=system_prompt,
        messages=[
            {
                "role": "user",
                "content": (
                    f"Date: {date_str}\n\n"
                    f"Conversation transcript:\n\n{transcript}"
                ),
            }
        ],
    )
    return response.content[0].text.strip()
