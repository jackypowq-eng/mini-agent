"""Tests for the Open-Meteo weather tool."""

from mini_agent.tools.weather import get_city_coordinates, weather


def test_known_city_coordinates():
    coords = get_city_coordinates("Shanghai")
    assert coords is not None
    lat, lon = coords
    assert 30 < lat < 32
    assert 120 < lon < 123


def test_real_weather_temperature():
    # Shanghai coordinates
    result = weather(31.2304, 121.4737)
    assert "Current temperature is" in result
    assert "°C" in result


def test_weather_invalid_coordinates():
    # Very extreme coordinates should still return a result or a graceful error.
    result = weather(999, 999)
    assert "Error" in result or "Current temperature" in result
