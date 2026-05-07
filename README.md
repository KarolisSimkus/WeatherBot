# WeatherBot

A Discord bot that delivers real-time weather and daily forecasts for Lithuanian cities, powered by the Meteo.lt API.

## Commands

| Command | Description |
|---|---|
| `!Vilnius` | Current weather in Vilnius |
| `!Klaipeda` | Current weather in Klaipėda |
| `!F_Vilnius` | Full-day forecast for Vilnius (morning / day / evening / night) |
| `!F_Klaipeda` | Full-day forecast for Klaipėda |

Each response includes temperature, feels-like, weather condition, precipitation, wind speed/gusts, and humidity.

## Setup

1. Clone the repo and install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Create a `.env` file in the project root:
   ```
   DISCORD_TOKEN=your_bot_token_here
   CHANNEL_ID=your_channel_id_here
   ```

3. Run the bot:
   ```bash
   python main.py
   ```

## Tech Stack

| Layer | Technology |
|---|---|
| Bot framework | [discord.py](https://discordpy.readthedocs.io/) 2.7 |
| Weather data | [Meteo.lt API](https://api.meteo.lt/) (Lithuanian meteorological service) |
| HTTP client | requests |
| Config | python-dotenv |
| Runtime | Python 3.10+ |
