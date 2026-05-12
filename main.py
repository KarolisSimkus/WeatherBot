import discord
from discord.ext import commands
import os
from dotenv import load_dotenv
import logging
import requests
from datetime import datetime, UTC

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')
intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix='!', intents=intents)

LOCATIONS = {
    'vilnius': 'Vilnius',
    'klaipeda': 'Klaipėda',
}

CONDITION_EMOJI = {
    'clear': '☀️',
    'partly-cloudy': '⛅',
    'cloudy': '☁️',
    'light-rain': '🌦',
    'rain': '🌧',
    'heavy-rain': '🌧',
    'sleet': '🌨',
    'light-snow': '❄️',
    'snow': '❄️',
    'heavy-snow': '❄️',
    'fog': '🌫️',
    'thunderstorms': '⛈️',
    'isolated-thunderstorms': '⛈️',
    'hail': '🌨',
}


def fetch_forecasts(city_code: str) -> list:
    url = f"https://api.meteo.lt/v1/places/{city_code}/forecasts/long-term"
    response = requests.get(url, timeout=10)
    response.raise_for_status()
    return response.json()["forecastTimestamps"]


def find_current(forecasts: list) -> dict:
    now = datetime.now(UTC)
    closest = min(
        forecasts,
        key=lambda f: abs(
            (datetime.fromisoformat(f["forecastTimeUtc"]).replace(tzinfo=UTC) - now).total_seconds()
        )
    )
    return closest


def format_current(city_name: str, f: dict) -> str:
    time_utc = datetime.fromisoformat(f["forecastTimeUtc"]).replace(tzinfo=UTC)
    local_time = time_utc.astimezone(LOCAL_TZ)
    condition = f["conditionCode"]
    emoji = CONDITION_EMOJI.get(condition, '🌡')
    label = condition.replace('-', ' ').title()
    rain = f.get("totalPrecipitation", 0)

    return (
        f"{emoji} **Current weather in {city_name}**\n"
        f"🕒 {local_time.strftime('%H:%M')} local\n"
        f"🌡 Temperature: **{f['airTemperature']}°C** (feels like {f['feelsLikeTemperature']}°C)\n"
        f"☁️ Condition: {label}\n"
        f"🌧 Precipitation: {rain} mm\n"
        f"💨 Wind: {f['windSpeed']} m/s (gusts {f['windGust']} m/s)\n"
        f"💧 Humidity: {f['relativeHumidity']}%"
    )


def format_full_day(city_name: str, forecasts: list) -> str:
    first_time = datetime.fromisoformat(forecasts[0]["forecastTimeUtc"]).replace(tzinfo=UTC).astimezone()
    target_date = first_time.date()

    periods = {"Morning (6–11)": None, "Day (12–17)": None, "Evening (18–23)": None, "Night (0–5)": None}
    hour_ranges = {"Morning (6–11)": range(6, 12), "Day (12–17)": range(12, 18), "Evening (18–23)": range(18, 24), "Night (0–5)": range(0, 6)}

    for f in forecasts:
        local = datetime.fromisoformat(f["forecastTimeUtc"]).replace(tzinfo=UTC).astimezone(LOCAL_TZ)
        if local.date() != target_date:
            continue
        for label, hours in hour_ranges.items():
            if local.hour in hours and periods[label] is None:
                periods[label] = f

    period_emojis = {"Morning (6–11)": "🌅", "Day (12–17)": "☀️", "Evening (18–23)": "🌇", "Night (0–5)": "🌙"}

    def fmt(label, data):
        if not data:
            return f"{period_emojis[label]} **{label}**: No data"
        condition = data["conditionCode"]
        emoji = CONDITION_EMOJI.get(condition, '🌡')
        cond_label = condition.replace('-', ' ').title()
        rain = data.get("totalPrecipitation", 0)
        return (
            f"{period_emojis[label]} **{label}**\n"
            f"  {emoji} {cond_label}\n"
            f"  🌡 {data['airTemperature']}°C (feels {data['feelsLikeTemperature']}°C)\n"
            f"  🌧 Precip: {rain} mm  💨 Wind: {data['windSpeed']} m/s\n"
            f"  💧 Humidity: {data['relativeHumidity']}%"
        )

    date_str = target_date.strftime('%Y-%m-%d')
    lines = [f"📅 **Full day forecast for {city_name} — {date_str}**\n"]
    for label in ["Morning (6–11)", "Day (12–17)", "Evening (18–23)", "Night (0–5)"]:
        lines.append(fmt(label, periods[label]))
    return "\n\n".join(lines)


@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")


@bot.command(name='Vilnius')
async def vilnius_current(ctx):
    try:
        forecasts = fetch_forecasts('vilnius')
        current = find_current(forecasts)
        await ctx.send(format_current('Vilnius', current))
    except Exception as e:
        await ctx.send(f"Error fetching weather: {e}")


@bot.command(name='Klaipeda')
async def klaipeda_current(ctx):
    try:
        forecasts = fetch_forecasts('klaipeda')
        current = find_current(forecasts)
        await ctx.send(format_current('Klaipėda', current))
    except Exception as e:
        await ctx.send(f"Error fetching weather: {e}")


@bot.command(name='F_Vilnius')
async def vilnius_full(ctx):
    try:
        forecasts = fetch_forecasts('vilnius')
        await ctx.send(format_full_day('Vilnius', forecasts))
    except Exception as e:
        await ctx.send(f"Error fetching weather: {e}")


@bot.command(name='F_Klaipeda')
async def klaipeda_full(ctx):
    try:
        forecasts = fetch_forecasts('klaipeda')
        await ctx.send(format_full_day('Klaipėda', forecasts))
    except Exception as e:
        await ctx.send(f"Error fetching weather: {e}")


bot.run(TOKEN, log_handler=handler, log_level=logging.DEBUG)
