"""OpenWeather helpers with predictable, user-friendly failures."""

import requests

from app.config import OPENWEATHER_API_KEY

_FORECAST_URL = "https://api.openweathermap.org/data/2.5/forecast"
_CURRENT_URL = "https://api.openweathermap.org/data/2.5/weather"


def _request(url: str, city: str):
    city = city.strip()
    if not city:
        return None, "Please provide a city name."
    if not OPENWEATHER_API_KEY:
        return None, "Weather is not configured on this deployment yet."

    try:
        response = requests.get(
            url,
            params={"q": city, "appid": OPENWEATHER_API_KEY, "units": "metric"},
            timeout=10,
        )
        data = response.json()
    except (requests.RequestException, ValueError):
        return None, "Unable to connect to the weather service right now."

    if response.status_code != 200:
        return None, f"Could not find weather for {city}."
    return data, None


def get_weather(city: str):
    data, error = _request(_CURRENT_URL, city)
    if error:
        return error
    condition = data.get("weather", [{}])[0].get("description", "Unknown")
    main = data.get("main", {})
    return (
        f"Weather in {city.title()}:\n"
        f"Temperature: {main.get('temp', 'N/A')}°C\n"
        f"Humidity: {main.get('humidity', 'N/A')}%\n"
        f"Condition: {condition.title()}"
    )


def _forecast(city: str):
    return _request(_FORECAST_URL, city)


def get_weather_forecast(city: str):
    data, error = _forecast(city)
    if error:
        return error

    result = [f"5-Day Forecast for {city.title()}:"]
    for item in data.get("list", [])[::8]:
        condition = item.get("weather", [{}])[0].get("description", "Unknown")
        main = item.get("main", {})
        result.append(
            f"{item.get('dt_txt', 'Unknown date').split(' ')[0]} — "
            f"{main.get('temp', 'N/A')}°C, "
            f"{condition.title()}, humidity {main.get('humidity', 'N/A')}%"
        )
    return "\n".join(result)


def get_tomorrow_weather(city: str):
    data, error = _forecast(city)
    if error:
        return error
    forecasts = data.get("list", [])
    if not forecasts:
        return f"No forecast is available for {city}."
    item = forecasts[min(8, len(forecasts) - 1)]
    condition = item.get("weather", [{}])[0].get("description", "Unknown")
    main = item.get("main", {})
    return (
        f"Tomorrow's weather in {city.title()}:\n"
        f"Temperature: {main.get('temp', 'N/A')}°C\n"
        f"Humidity: {main.get('humidity', 'N/A')}%\n"
        f"Condition: {condition.title()}"
    )


def get_rain_prediction(city: str, tomorrow: bool = False):
    data, error = _forecast(city)
    if error:
        return error
    forecasts = data.get("list", [])
    selected = forecasts[8:16] if tomorrow else forecasts[:8]
    rain_found = any(
        any(word in item.get("weather", [{}])[0].get("description", "").lower()
            for word in ("rain", "drizzle", "thunderstorm"))
        for item in selected
    )
    period = "tomorrow" if tomorrow else "today"
    answer = "Yes" if rain_found else "No"
    return f"{answer}, rain is {'expected' if rain_found else 'not expected'} in {city.title()} {period}."
