"""Real-time weather tool using Open-Meteo."""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any

from mini_agent.tool_registry import Tool


# Common city coordinates so the LLM can call by name indirectly.
_CITY_COORDINATES: dict[str, tuple[float, float]] = {
    "beijing": (39.9042, 116.4074),
    "shanghai": (31.2304, 121.4737),
    "guangzhou": (23.1291, 113.2644),
    "shenzhen": (22.5431, 114.0579),
    "chengdu": (30.5728, 104.0668),
    "hangzhou": (30.2741, 120.1551),
    "wuhan": (30.5928, 114.3055),
    "xian": (34.3416, 108.9398),
    "nanjing": (32.0603, 118.7969),
    "chongqing": (29.5630, 106.5516),
}


def _resolve_coordinates(latitude: float, longitude: float) -> tuple[float, float]:
    return float(latitude), float(longitude)


def weather(latitude: float, longitude: float) -> str:
    """Fetch current temperature for the given coordinates via Open-Meteo."""
    lat, lon = _resolve_coordinates(latitude, longitude)
    url = (
        "https://api.open-meteo.com/v1/forecast"
        f"?latitude={lat}&longitude={lon}&current_weather=true"
    )
    try:
        with urllib.request.urlopen(url, timeout=10) as response:
            data: dict[str, Any] = json.loads(response.read().decode("utf-8"))
        current = data.get("current_weather", {})
        temperature = current.get("temperature")
        if temperature is None:
            return "Error: weather data did not include temperature"
        return f"Current temperature is {temperature} °C"
    except urllib.error.URLError as exc:
        return f"Error fetching weather: {exc}"
    except json.JSONDecodeError as exc:
        return f"Error parsing weather response: {exc}"


def get_city_coordinates(city: str) -> tuple[float, float] | None:
    """Look up coordinates for a known city name."""
    return _CITY_COORDINATES.get(city.strip().lower())


def get_tool() -> Tool:
    return Tool(
        name="weather",
        description=(
            "Get the current temperature for a location using Open-Meteo. "
            "Requires latitude and longitude. Common cities can be inferred by the agent."
        ),
        parameters={
            "type": "object",
            "properties": {
                "latitude": {
                    "type": "number",
                    "description": "Latitude of the location",
                },
                "longitude": {
                    "type": "number",
                    "description": "Longitude of the location",
                },
            },
            "required": ["latitude", "longitude"],
        },
        func=weather,
    )
