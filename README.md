# WeatherBot

A Discord bot that delivers real-time weather and daily forecasts for Lithuanian cities, powered by the Meteo.lt API.

## Commands

| Command | Description |
|---|---|
| `!weather vilnius` | Current weather in Vilnius |
| `!weather klaipeda` | Current weather in Klaipėda |
| `!weather vilnius full` | Full-day forecast for Vilnius (morning / day / evening / night) |
| `!weather klaipeda full` | Full-day forecast for Klaipėda |

Requests are cached for 20 minutes, and each user can request weather once every 10 seconds. Responses include temperature, feels-like, weather condition, precipitation, wind speed/gusts, humidity, and the Meteo LT attribution.

## Data attribution and license

Weather data is provided by [Meteo.lt](https://api.meteo.lt/) and is used under the [Creative Commons Attribution-ShareAlike 4.0 International (CC BY-SA 4.0) license](https://creativecommons.org/licenses/by-sa/4.0/).

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
| HTTP client | httpx (async) |
| Config | python-dotenv |
| Runtime | Python 3.10+ |
