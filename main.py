import discord
from discord.ext import commands
import os
from dotenv import load_dotenv
import logging
from logging.handlers import RotatingFileHandler
import time
from datetime import datetime, UTC
from zoneinfo import ZoneInfo

import httpx

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

handler = RotatingFileHandler(
    filename='discord.log',
    maxBytes=5 * 1024 * 1024,
    backupCount=3,
    encoding='utf-8',
)
handler.setLevel(logging.INFO)
intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix='!', intents=intents, help_command=None)

LOCATIONS = {
    'vilnius': 'Vilnius',
    'klaipeda': 'Klaipėda',
}
FORECAST_CACHE_TTL = 20 * 60
forecast_cache = {}
logger = logging.getLogger(__name__)

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


async def fetch_forecasts(city_code: str) -> list:
    cached = forecast_cache.get(city_code)
    if cached and time.monotonic() - cached[0] < FORECAST_CACHE_TTL:
        return cached[1]

    url = f"https://api.meteo.lt/v1/places/{city_code}/forecasts/long-term"
    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.get(url)
        response.raise_for_status()
        forecasts = response.json()["forecastTimestamps"]

    forecast_cache[city_code] = (time.monotonic(), forecasts)
    return forecasts


async def send_weather_message(ctx, message: str) -> None:
    await ctx.send(f"{message}\n\n*from Meteo LT*")


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
    local_time = time_utc.astimezone(ZoneInfo("Europe/Vilnius"))
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
    first_time = datetime.fromisoformat(forecasts[0]["forecastTimeUtc"]).replace(tzinfo=UTC).astimezone(ZoneInfo("Europe/Vilnius"))
    target_date = first_time.date()

    periods = {"Morning (6–11)": None, "Day (12–17)": None, "Evening (18–23)": None, "Night (0–5)": None}
    hour_ranges = {"Morning (6–11)": range(6, 12), "Day (12–17)": range(12, 18), "Evening (18–23)": range(18, 24), "Night (0–5)": range(0, 6)}

    for f in forecasts:
        local = datetime.fromisoformat(f["forecastTimeUtc"]).replace(tzinfo=UTC).astimezone(ZoneInfo("Europe/Vilnius"))
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
    logger.info("Logged in as %s", bot.user)


@bot.command(name='weather')
@commands.cooldown(1, 10, commands.BucketType.user)
async def weather(ctx, location: str, forecast_type: str = 'current'):
    city_code = location.casefold()
    city_name = LOCATIONS.get(city_code)
    if city_name is None or forecast_type not in ('current', 'full'):
        await send_weather_message(
            ctx,
            "Usage: `!weather <vilnius|klaipeda> [current|full]`",
        )
        return

    try:
        forecasts = await fetch_forecasts(city_code)
        if not forecasts:
            await send_weather_message(ctx, f"No forecast is currently available for {city_name}.")
            return

        if forecast_type == 'full':
            message = format_full_day(city_name, forecasts)
        else:
            message = format_current(city_name, find_current(forecasts))
        await send_weather_message(ctx, message)
    except httpx.TimeoutException:
        logger.warning("Weather API timed out for %s", city_code)
        await send_weather_message(ctx, "The weather service took too long to respond. Please try again shortly.")
    except httpx.HTTPStatusError as error:
        if error.response.status_code == 404:
            logger.warning("Weather API returned 404 for %s", city_code)
            await send_weather_message(ctx, f"No forecast was found for {city_name}.")
        else:
            logger.exception("Weather API returned HTTP %s for %s", error.response.status_code, city_code)
            await send_weather_message(ctx, "The weather service is temporarily unavailable. Please try again later.")
    except httpx.RequestError:
        logger.exception("Could not reach the weather API for %s", city_code)
        await send_weather_message(ctx, "Could not connect to the weather service. Please try again later.")
    except Exception:
        logger.exception("Failed to fetch or format the forecast for %s", city_code)
        await send_weather_message(ctx, "Sorry, something went wrong while getting the forecast.")


@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandOnCooldown):
        await send_weather_message(
            ctx,
            f"Please wait {error.retry_after:.1f} seconds before requesting weather again.",
        )
        return

    if (
        isinstance(error, commands.MissingRequiredArgument)
        and ctx.command is not None
        and ctx.command.name == 'weather'
    ):
        await send_weather_message(ctx, "Usage: `!weather <vilnius|klaipeda> [current|full]`")
        return

    logger.error(
        "Command failed",
        exc_info=(type(error), error, error.__traceback__),
    )
    await send_weather_message(ctx, "Sorry, I couldn't process that command.")


def main() -> None:
    if not TOKEN:
        raise RuntimeError("DISCORD_TOKEN is not set.")
    bot.run(TOKEN, log_handler=handler, log_level=logging.INFO)


if __name__ == "__main__":
    main()
