import asyncio

import discord
from discord.ext import commands
import os
from dotenv import load_dotenv
import logging
import requests
from datetime import datetime, UTC

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
CHANNEL_ID = int(os.getenv('CHANNEL_ID'))
CITY = "vilnius"

handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')
intents = discord.Intents.default()
intents.message_content = True

client = discord.Client(intents=intents)

'''
def get_weather():
    url = f"https://api.meteo.lt/v1/places/{CITY}/forecasts/long-term"
    response = requests.get(url)
    data = response.json()

    # Print all data from meteo.lt
    print("[meteo.lt full payload]", data)

    # Find closest forecast to now
    now = datetime.now(timezone.utc).isoformat()
    forecast = data["forecastTimestamps"][0]

    temp = forecast["airTemperature"]
    condition = forecast["conditionCode"]

    return f"🌦 Weather in {CITY.title()}:\nTemperature: {temp}°C\nCondition: {condition}"
'''

def get_weather():
    url = f"https://api.meteo.lt/v1/places/{CITY}/forecasts/long-term"
    response = requests.get(url)
    data = response.json()

    forecasts = data["forecastTimestamps"]
    # today = datetime.now().astimezone().date()
    # print("[meteo.lt full payload]", data)
    first_time = datetime.fromisoformat(forecasts[0]["forecastTimeUtc"]).replace(tzinfo=UTC).astimezone()

    target_date = first_time.date()

    periods = {
        "morning": None,
        "day": None,
        "evening": None,
        "night": None
    }

    for f in forecasts:
        time = datetime.fromisoformat(f["forecastTimeUtc"]).replace(tzinfo=UTC).astimezone()
        if time.date() != target_date:
            continue

        hour = time.hour

        if 6 <= hour <= 11 and periods["morning"] is None:
            periods["morning"] = f
        elif 12 <= hour <= 17 and periods["day"] is None:
            periods["day"] = f
        elif 18 <= hour <= 23 and periods["evening"] is None:
            periods["evening"] = f
        elif 0 <= hour <= 5 and periods["night"] is None:
            periods["night"] = f

    def format_period(label, data):
        if not data:
            return f"{label}: No data"

        temp = data["airTemperature"]
        feels = data["feelsLikeTemperature"]
        wind = data["windSpeed"]
        rain = data.get("precipitation", 0)
        condition = data["conditionCode"].replace("-", " ").title()

        return (
            f"{label}\n"
            f"  🌡 Temp: {temp}°C (feels {feels}°C)\n"
            f"  🌧 Rain: {rain} mm\n"
            f"  💨 Wind: {wind} m/s\n"
            f"  ☁️ {condition}"
        )

    timestamp = datetime.now(UTC).astimezone().isoformat()

    message = (
        f"🌦 **Weather in {CITY.title()} today**\n"
        f"🕒 _Reported at: {timestamp}_\n\n"
        f"🌅 {format_period('Morning', periods['morning'])}\n\n"
        f"☀️ {format_period('Day', periods['day'])}\n\n"
        f"🌇 {format_period('Evening', periods['evening'])}\n\n"
        f"🌙 {format_period('Night', periods['night'])}"
    )

    # print(time, time.date(), today)
    
    return message


async def send_daily_weather():
    await client.wait_until_ready()
    channel = client.get_channel(CHANNEL_ID)

    while not client.is_closed():
        try:
            message = get_weather()
            await channel.send(message)
        except Exception as e:
            print(f"Error sending message: {e}")

        await asyncio.sleep(86400)  # Sleep for 24 hours

@client.event
async def on_ready():
    print(f"Logged in as {client.user}")
    client.loop.create_task(send_daily_weather())

client.run(TOKEN, log_handler=handler, log_level=logging.DEBUG)