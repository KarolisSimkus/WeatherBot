import unittest
from unittest.mock import AsyncMock, Mock, patch

import main


class WeatherCommandTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        main.forecast_cache.clear()

    async def test_fetch_forecasts_reuses_cached_response(self):
        client = AsyncMock()
        response = Mock()
        response.json.return_value = {"forecastTimestamps": [{"airTemperature": 12}]}
        client.get.return_value = response
        client_context = AsyncMock()
        client_context.__aenter__.return_value = client

        with patch("main.httpx.AsyncClient", return_value=client_context) as async_client:
            first = await main.fetch_forecasts("vilnius")
            second = await main.fetch_forecasts("vilnius")

        self.assertEqual(first, [{"airTemperature": 12}])
        self.assertIs(second, first)
        async_client.assert_called_once_with(timeout=10)
        client.get.assert_awaited_once_with(
            "https://api.meteo.lt/v1/places/vilnius/forecasts/long-term"
        )

    async def test_weather_messages_end_with_attribution(self):
        ctx = Mock()
        ctx.send = AsyncMock()

        await main.send_weather_message(ctx, "Forecast")

        ctx.send.assert_awaited_once_with("Forecast\n\n*from Meteo LT*")

    async def test_weather_timeout_returns_friendly_message(self):
        ctx = Mock()
        ctx.send = AsyncMock()
        timeout = main.httpx.TimeoutException("internal timeout detail")

        with patch("main.fetch_forecasts", new=AsyncMock(side_effect=timeout)):
            await main.weather.callback(ctx, "vilnius")

        message = ctx.send.await_args.args[0]
        self.assertIn("took too long to respond", message)
        self.assertNotIn("internal timeout detail", message)
        self.assertTrue(message.endswith("*from Meteo LT*"))

    async def test_weather_404_returns_not_found_message(self):
        ctx = Mock()
        ctx.send = AsyncMock()
        request = main.httpx.Request("GET", "https://api.meteo.lt/forecast")
        response = main.httpx.Response(404, request=request)
        error = main.httpx.HTTPStatusError("internal detail", request=request, response=response)

        with patch("main.fetch_forecasts", new=AsyncMock(side_effect=error)):
            await main.weather.callback(ctx, "vilnius")

        message = ctx.send.await_args.args[0]
        self.assertIn("No forecast was found for Vilnius", message)
        self.assertNotIn("internal detail", message)
        self.assertTrue(message.endswith("*from Meteo LT*"))

    async def test_unknown_location_shows_usage_without_fetching(self):
        ctx = Mock()
        ctx.send = AsyncMock()

        with patch("main.fetch_forecasts", new=AsyncMock()) as fetch:
            await main.weather.callback(ctx, "riga")

        fetch.assert_not_awaited()
        self.assertTrue(ctx.send.await_args.args[0].startswith("Usage:"))
        self.assertTrue(ctx.send.await_args.args[0].endswith("*from Meteo LT*"))

    async def test_missing_city_argument_shows_usage(self):
        ctx = Mock()
        ctx.command = main.weather
        ctx.send = AsyncMock()
        error = main.commands.MissingRequiredArgument(main.weather.clean_params["location"])

        await main.on_command_error(ctx, error)

        self.assertTrue(ctx.send.await_args.args[0].startswith("Usage:"))
        self.assertTrue(ctx.send.await_args.args[0].endswith("*from Meteo LT*"))


if __name__ == "__main__":
    unittest.main()
