from __future__ import annotations

import httpx

from obsidian_journal.models import WeatherInfo

OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"


def fetch_weather(lat: float, lon: float) -> WeatherInfo | None:
    """Fetch today's weather forecast from Open-Meteo.

    Returns None on any error so planning can proceed without weather.
    """
    try:
        params = {
            "latitude": lat,
            "longitude": lon,
            "daily": (
                "temperature_2m_max,temperature_2m_min,"
                "precipitation_probability_max,weathercode,"
                "wind_speed_10m_max,sunrise,sunset"
            ),
            "hourly": "temperature_2m,precipitation_probability,weathercode",
            "temperature_unit": "fahrenheit",
            "wind_speed_unit": "mph",
            "timezone": "auto",
            "forecast_days": 1,
        }
        response = httpx.get(OPEN_METEO_URL, params=params, timeout=10.0)
        response.raise_for_status()
        data = response.json()

        daily = data["daily"]
        hourly = data.get("hourly", {})

        temp_high = daily["temperature_2m_max"][0]
        temp_low = daily["temperature_2m_min"][0]
        precip_chance = daily["precipitation_probability_max"][0]
        wind_speed = daily["wind_speed_10m_max"][0]
        weather_code = daily["weathercode"][0]
        sunrise = daily["sunrise"][0].split("T")[1] if daily["sunrise"][0] else ""
        sunset = daily["sunset"][0].split("T")[1] if daily["sunset"][0] else ""

        condition = _weather_code_to_condition(weather_code)
        best_window = _find_best_outdoor_window(hourly)

        summary = (
            f"{condition}, high {temp_high:.0f}F / low {temp_low:.0f}F, "
            f"{precip_chance}% chance of rain, wind {wind_speed:.0f} mph"
        )

        return WeatherInfo(
            temperature_high_f=temp_high,
            temperature_low_f=temp_low,
            condition=condition,
            precipitation_chance=precip_chance,
            wind_speed_mph=wind_speed,
            sunrise=sunrise,
            sunset=sunset,
            best_outdoor_window=best_window,
            summary=summary,
        )
    except Exception:
        return None


def _weather_code_to_condition(code: int) -> str:
    """Convert WMO weather code to human-readable condition."""
    conditions = {
        0: "clear sky",
        1: "mainly clear",
        2: "partly cloudy",
        3: "overcast",
        45: "foggy",
        48: "depositing rime fog",
        51: "light drizzle",
        53: "moderate drizzle",
        55: "dense drizzle",
        61: "slight rain",
        63: "moderate rain",
        65: "heavy rain",
        71: "slight snow",
        73: "moderate snow",
        75: "heavy snow",
        80: "slight rain showers",
        81: "moderate rain showers",
        82: "violent rain showers",
        95: "thunderstorm",
        96: "thunderstorm with slight hail",
        99: "thunderstorm with heavy hail",
    }
    return conditions.get(code, "unknown")


def _find_best_outdoor_window(hourly: dict) -> str:
    """Analyze hourly data to find the best 1-2 hour window for outdoor activity.

    Prioritizes low precipitation probability and comfortable temperature
    during daylight hours (7am-7pm).
    """
    if not hourly or "time" not in hourly:
        return "midday (no hourly data available)"

    times = hourly.get("time", [])
    temps = hourly.get("temperature_2m", [])
    precip_probs = hourly.get("precipitation_probability", [])

    best_hour = None
    best_score = -1

    for i, time_str in enumerate(times):
        hour = int(time_str.split("T")[1].split(":")[0])
        if hour < 7 or hour > 19:
            continue

        temp = temps[i] if i < len(temps) else 70
        precip = precip_probs[i] if i < len(precip_probs) else 50

        # Score: prefer low precip and comfortable temp (55-80F range)
        precip_score = max(0, 100 - precip)
        temp_score = max(0, 50 - abs(temp - 68))
        score = precip_score * 2 + temp_score

        if score > best_score:
            best_score = score
            best_hour = hour

    if best_hour is not None:
        end_hour = best_hour + 1
        return f"{best_hour:02d}:00-{end_hour:02d}:00"
    return "midday"
