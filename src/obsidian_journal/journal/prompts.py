from __future__ import annotations

from obsidian_journal.models import ReflectionType

SYSTEM_PROMPT = """\
You are a thoughtful journaling assistant helping someone reflect on their day, \
projects, or ideas. Your role is to ask insightful follow-up questions that help \
them think more deeply and articulate what matters most.

Guidelines:
- Ask one focused question at a time
- Build on their previous answers — don't repeat or ask generic questions
- Gently probe for specifics: feelings, decisions, surprises, lessons
- Keep your responses concise (2-3 sentences max before your question)
- When you have enough material (after 2-4 exchanges), let the user know \
they can type "done" to wrap up, but don't push them to stop early
"""

OPENING_QUESTIONS: dict[ReflectionType, str] = {
    ReflectionType.END_OF_DAY: (
        "Let's reflect on your day. "
        "What's one thing that stood out to you today — something that went well, "
        "surprised you, or is still on your mind?"
    ),
    ReflectionType.END_OF_PROJECT: (
        "Let's do a project retrospective. "
        "What project are you wrapping up, and what was the original goal when you started?"
    ),
    ReflectionType.PODCAST: (
        "Let's capture your thoughts on something you listened to or watched. "
        "What was it, and what's the one idea that stuck with you most?"
    ),
    ReflectionType.MEETING: (
        "Let's debrief a meeting you just had. "
        "What was the meeting about, and what was the most important thing "
        "that came out of it?"
    ),
    ReflectionType.READING: (
        "Let's capture your thoughts on something you've been reading. "
        "What article or book is it, and what idea or passage has stuck with "
        "you most so far?"
    ),
    ReflectionType.FREE_FORM: (
        "What's on your mind? Share whatever you'd like to explore or think through, "
        "and I'll help you dig deeper."
    ),
}
