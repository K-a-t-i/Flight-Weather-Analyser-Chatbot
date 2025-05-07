import logging
import os
import requests
import json
from datetime import datetime, timedelta
import time
import hashlib
import random
import asyncio

from utils import (
    handle_api_request,
    handle_api_request_async,
    parse_date,
    logger
)
from config import Config

class WeatherServiceException(Exception):
    """Base exception class for WeatherService errors."""
    pass

class LocationNotFoundException(WeatherServiceException):
    """Raised when a location cannot be found."""
    pass

class ApiRequestException(WeatherServiceException):
    """Raised when an API request fails."""
    pass

class WeatherService:
    """Service class for weather-related functionality."""

    def __init__(self, api_keys=None, cache_config=None, config=None):
        """
        Initialise the WeatherService with configuration.

        Args:
            api_keys (dict, optional): Dictionary of API keys. If None, uses Config.
            cache_config (dict, optional): Cache configuration. If None, uses Config.
            config (Config, optional): Configuration instance. If provided, overrides api_keys and cache_config.

        Note:
            At least one of (api_keys, cache_config) or config must be provided.
            If config is provided, it takes precedence over api_keys and cache_config.
        """
        # Determine how to get configuration
        if config is not None:
            # Use provided Config instance
            self.config = config
            self.api_keys = config.api_keys
            self.cache_config = config.cache_config
        elif api_keys is not None and cache_config is not None:
            # Use provided direct parameters (backwards compatibility)
            self.api_keys = api_keys
            self.cache_config = cache_config
            self.config = None
        else:
            # Use singleton Config
            self.config = Config()
            self.api_keys = self.config.api_keys
            self.cache_config = self.config.cache_config

        # Initialise logger
        self.logger = logging.getLogger(__name__)
        self.logger.info("WeatherService initialised")

    def get_location_coordinates(self, location_name):
        """
        Get coordinates for a given location name.

        Args:
            location_name (str): Name of the location

        Returns:
            dict: Location data including latitude, longitude, and formatted name

        Raises:
            LocationNotFoundException: If the location cannot be found
        """
        base_url = "https://api.opencagedata.com/geocode/v1/json"
        params = {
            "q": location_name,
            "key": self.api_keys["opencage"],
            "limit": 1
        }

        success, response_data = handle_api_request(
            base_url,
            params,
            "OpenCage",
            cache_type="coordinates",
            cache_config=self.cache_config
        )

        if not success:
            logger.error(f"Failed to get coordinates for location: {location_name}")
            raise ApiRequestException(f"Failed to get coordinates for location: {location_name}")

        if "results" in response_data and response_data["results"]:
            result = response_data["results"][0]
            return {
                "lat": result["geometry"]["lat"],
                "lon": result["geometry"]["lng"],
                "name": result["formatted"]
            }
        else:
            logger.warning(f"No results found for location: {location_name}")
            raise LocationNotFoundException(f"Location not found: {location_name}")

    def get_future_weather_data(self, location, date):
        """
        Get weather forecast data for a future date.

        Args:
            location (dict): Location data with lat, lon, and name
            date (datetime.date): The date to get weather for

        Returns:
            str: Formatted weather information

        Raises:
            ApiRequestException: If the API request fails
        """
        base_url = "https://my.meteoblue.com/packages/basic-1h"
        params = {
            "apikey": self.api_keys["meteoblue"],
            "lat": location["lat"],
            "lon": location["lon"],
            "asl": "0",
            "format": "json",
            "tz": "UTC"
        }

        success, response_data = handle_api_request(
            base_url,
            params,
            "Meteoblue",
            cache_type="weather",
            cache_config=self.cache_config
        )

        if not success:
            error_msg = f"Failed to retrieve future weather data: {response_data}"
            logger.error(error_msg)
            raise ApiRequestException(error_msg)

        if "data_1h" not in response_data:
            error_msg = "Missing data_1h in Meteoblue API response"
            logger.warning(error_msg)
            raise ApiRequestException(error_msg)

        forecast = response_data["data_1h"]

        date_index = (date - datetime.now().date()).days
        if 0 <= date_index <= 6:
            day_start_idx = date_index * 24
            day_end_idx = (date_index + 1) * 24

            # Calculate daily averages
            temp = sum(forecast.get("temperature", [0] * 24)[day_start_idx:day_end_idx]) / 24
            wind_speed = sum(forecast.get("windspeed", [0] * 24)[day_start_idx:day_end_idx]) / 24
            wind_direction = sum(forecast.get("winddirection", [0] * 24)[day_start_idx:day_end_idx]) / 24
            precip = sum(forecast.get("precipitation", [0] * 24)[day_start_idx:day_end_idx])
            snow = sum(forecast.get("snowfall", [0] * 24)[day_start_idx:day_end_idx])
            relative_humidity = sum(forecast.get("relativehumidity", [0] * 24)[day_start_idx:day_end_idx]) / 24

            # Handle pressure data
            pressure_values = forecast.get("pressure", [0] * 24)[day_start_idx:day_end_idx]
            if all(p == 0 for p in pressure_values):
                # Use a default standard pressure if data is missing
                pressure = 1013  # Standard atmospheric pressure in hPa
            else:
                # Filter out zero values before calculating average
                valid_pressure = [p for p in pressure_values if p > 0]
                pressure = sum(valid_pressure) / len(valid_pressure) if valid_pressure else 1013

            cloud_cover = sum(forecast.get("cloudcover", [0] * 24)[day_start_idx:day_end_idx]) / 24

            return self.format_weather_info(
                location,
                date,
                temp,
                wind_speed,
                wind_direction,
                precip,
                snow,
                relative_humidity,
                pressure,
                cloud_cover
            )
        else:
            error_msg = f"Date out of range: can only provide forecast for today and the next 6 days"
            logger.warning(error_msg)
            raise ValueError(error_msg)

    def get_historical_weather_data(self, location, date):
        """
        Get weather data for a past date.

        Args:
            location (dict): Location data with lat, lon, and name
            date (datetime.date): The date to get weather for

        Returns:
            str: Formatted weather information

        Raises:
            ApiRequestException: If the API request fails
        """
        base_url = (f"https://weather.visualcrossing.com/VisualCrossingWebServices/rest/services/timeline/{location['lat']},"
                    f"{location['lon']}/{date.strftime('%Y-%m-%d')}")
        params = {
            "unitGroup": "metric",
            "key": self.api_keys["visualcrossing"],
            "contentType": "json",
        }

        success, response_data = handle_api_request(
            base_url,
            params,
            "VisualCrossing",
            cache_type="historical",
            cache_config=self.cache_config
        )

        if not success:
            error_msg = f"Failed to retrieve historical weather data: {response_data}"
            logger.error(error_msg)
            raise ApiRequestException(error_msg)

        try:
            day_data = response_data['days'][0]

            temp = day_data['temp']
            wind_speed = day_data['windspeed']
            wind_direction = day_data['winddir']
            precip = day_data['precip']
            snow = day_data['snow']
            relative_humidity = day_data['humidity']
            pressure = day_data['pressure']
            cloud_cover = day_data['cloudcover']

            return self.format_weather_info(
                location,
                date,
                temp,
                wind_speed,
                wind_direction,
                precip,
                snow,
                relative_humidity,
                pressure,
                cloud_cover,
                is_historical=True
            )
        except (KeyError, IndexError) as e:
            error_msg = f"Missing data in VisualCrossing API response: {str(e)}"
            logger.error(error_msg)
            raise ApiRequestException(error_msg)

    def get_weather(self, location_name, date_string):
        """
        Get weather data for a location and date.

        Args:
            location_name (str): Name of the location
            date_string (str): Date as a string (e.g., "today", "tomorrow", "next Monday")

        Returns:
            str: Formatted weather information

        Raises:
            ValueError: If the date cannot be parsed
            LocationNotFoundException: If the location cannot be found
            ApiRequestException: If any API request fails
        """
        # Parse the date
        date = parse_date(date_string)
        today = datetime.now().date()

        # Check if the date is too far in the future
        if (date - today).days > 6:
            latest_date = (today + timedelta(days=6)).strftime('%Y-%m-%d')
            return (f"I'm sorry, but I can only provide weather for the past, today and up to 6 days "
                    f"in the future. The date you asked about ({date.strftime('%Y-%m-%d')}) is too far "
                    f"in the future. The latest date I can provide a forecast for is {latest_date}.")

        try:
            # Get coordinates for the location
            coordinates = self.get_location_coordinates(location_name)

            # Get either historical or future weather data
            if date < today:
                weather_data = self.get_historical_weather_data(coordinates, date)
            else:
                weather_data = self.get_future_weather_data(coordinates, date)

            return weather_data

        except LocationNotFoundException:
            return (f"I'm sorry, but I don't have information for the location '{location_name}'. "
                    f"Could you please check the spelling or try asking about a different city?")
        except ApiRequestException as e:
            return f"Sorry, I couldn't retrieve the weather information at this time. {str(e)}"
        except Exception as e:
            logger.error(f"Unexpected error in get_weather: {str(e)}")
            return f"I'm sorry, I encountered an unexpected error while getting the weather data."

    def format_weather_info(self, location, date, temp, wind_speed, wind_direction, precip, snow, relative_humidity, pressure,
                            cloud_cover, is_historical=False):
        """
        Format weather data into a readable string.

        Args:
            location (dict): Location data
            date (datetime.date): The date for the weather
            temp (float): Temperature in Celsius
            wind_speed (float): Wind speed in km/h
            wind_direction (float): Wind direction in degrees
            precip (float): Precipitation in mm
            snow (float): Snowfall in mm
            relative_humidity (float): Relative humidity percentage
            pressure (float): Barometric pressure in hPa
            cloud_cover (float): Cloud cover percentage
            is_historical (bool): Whether the data is historical

        Returns:
            str: Formatted weather information
        """
        # Define default values
        default_values = {
            "temp": 15.0,           # Default comfortable temperature
            "wind_speed": 0.0,      # Default calm wind
            "wind_direction": 0.0,  # Default north
            "precip": 0.0,          # Default no precipitation
            "snow": 0.0,            # Default no snow
            "relative_humidity": 50.0,  # Default moderate humidity
            "pressure": 1013.0,     # Default standard pressure
            "cloud_cover": 0.0,     # Default clear skies
        }

        # Check for missing values and use defaults
        if temp is None or temp == 0:
            temp = default_values["temp"]
        if wind_speed is None or wind_speed == 0:
            wind_speed = default_values["wind_speed"]
        if wind_direction is None:
            wind_direction = default_values["wind_direction"]
        if precip is None:
            precip = default_values["precip"]
        if snow is None:
            snow = default_values["snow"]
        if relative_humidity is None or relative_humidity == 0:
            relative_humidity = default_values["relative_humidity"]
        if pressure is None or pressure == 0:
            pressure = default_values["pressure"]
        if cloud_cover is None:
            cloud_cover = default_values["cloud_cover"]

        # Convert wind speed to knots (1 km/h ≈ 0.54 knots)
        wind_speed_knots = wind_speed * 0.54

        # Estimating fog/mist
        fog_or_mist = "No fog/mist reported" if relative_humidity < 90 else "Possible fog/mist (FG/BR)"

        # Enhanced weather condition determination
        primary_condition = ""
        condition_details = []

        # Primary condition based on precipitation and clouds
        if snow > 0:
            if snow > 10:
                primary_condition = "heavily snowing"
            else:
                primary_condition = "snowy"
            condition_details.append("snow-covered")
        elif precip > 0:
            if precip > 15:
                primary_condition = "stormy with heavy rain"
            elif precip > 5:
                primary_condition = "rainy"
            else:
                primary_condition = "drizzly"

        elif relative_humidity > 90 and cloud_cover > 80:
            primary_condition = "foggy"
            condition_details.append("misty")
        elif cloud_cover < 10:
            primary_condition = "clear and sunny"
            condition_details.append("bright")
        elif cloud_cover < 30:
            primary_condition = "mostly sunny"
            condition_details.append("pleasant")
        elif cloud_cover < 60:
            primary_condition = "partly cloudy"
        else:
            primary_condition = "overcast"

        # Wind descriptors
        if wind_speed > 40:
            condition_details.append("very windy")
        elif wind_speed > 20:
            condition_details.append("breezy")

        # Temperature descriptors
        if temp < -10:
            condition_details.append("bitterly cold")
        elif temp < 0:
            condition_details.append("frosty")
        elif temp < 10:
            condition_details.append("chilly")
        elif 15 <= temp <= 25:
            condition_details.append("comfortable")
        elif temp > 30:
            condition_details.append("hot")
        elif temp > 35:
            condition_details.append("red-hot")

        # Special combinations
        if primary_condition == "clear and sunny" and temp > 25:
            primary_condition = "brilliantly sunny"
        if primary_condition == "overcast" and temp < 5:
            primary_condition = "gloomy and cold"

        # Pressure-based additions
        if pressure > 1025 and cloud_cover < 30:
            condition_details.append("with excellent visibility")

        # Combine conditions into a rich description
        if condition_details:
            condition = f"{primary_condition}, {' and '.join(condition_details)}"
        else:
            condition = primary_condition

        verb = "was" if is_historical else "is expected to be"

        # Format date with weekday
        formatted_date = f"{date.strftime('%A, %Y-%m-%d')}"

        # Formatting the output
        weather_info = f"""On {formatted_date}, the weather in {location['name']} {verb} {condition}. 
        The average temperature {verb} {temp:.2f}°C, with {precip:.1f}mm of precipitation and average wind speeds 
        of {wind_speed:.2f}km/h.

- Average Temperature: {temp:.2f}°C
- Average Wind Speed: {wind_speed:.2f} km/h
- Total Precipitation: {precip:.1f} mm
- Average Relative Humidity: {relative_humidity:.0f}%
- Average Cloud Cover: {cloud_cover:.0f}%

Weather information for our pilots:
- Average Temperature: {temp:.2f}°C
- Wind: {wind_speed:.2f} km/h ({wind_speed_knots:.1f} knots) from {wind_direction:.0f}° (DD)
- Precipitation (RA): {precip:.1f} mm
- Snow (SN): {snow:.1f} mm
- Average Relative Humidity (RH): {relative_humidity:.0f}%
- Average Barometric Pressure (QNH): {pressure:.0f} hPa
- {fog_or_mist}
- Freezing Level (FZ LVL): Information not available
- Ceiling Height (CIG): Information not available"""

        return weather_info

    def _score_flying_conditions(self, day_data):
        """
        Calculate a flying conditions score based on weather parameters.

        Args:
            day_data (dict): Dictionary containing weather data for a single day

        Returns:
            dict: Dictionary with score, factors affecting the score, and weather data
        """
        # Initialise score
        score = 100
        score_factors = {}

        # Extract weather parameters
        temp = day_data["temp"]
        wind = day_data["wind_speed"]
        precip = day_data["precipitation"]
        snow = day_data["snow"]
        clouds = day_data["cloud_cover"]
        humidity = day_data["humidity"]
        pressure = day_data["pressure"]

        # 1. Temperature scoring
        if temp < 5:
            penalty = (5 - temp) * 3
            score -= penalty
            score_factors["temperature"] = f"Too cold ({temp:.1f}°C, -{penalty:.1f} points)"
        elif temp > 30:
            penalty = (temp - 30) * 2
            score -= penalty
            score_factors["temperature"] = f"Too hot ({temp:.1f}°C, -{penalty:.1f} points)"
        else:
            if 10 <= temp <= 25:
                bonus = 5
                score += bonus
                score_factors["temperature"] = f"Ideal temperature ({temp:.1f}°C, +{bonus} points)"

        # 2. Wind speed scoring
        if wind < 5:
            bonus = 10
            score += bonus
            score_factors["wind"] = f"Calm winds ({wind:.1f} km/h, +{bonus} points)"
        elif wind < 15:
            bonus = 5
            score += bonus
            score_factors["wind"] = f"Light winds ({wind:.1f} km/h, +{bonus} points)"
        elif wind < 25:
            penalty = (wind - 15) * 2
            score -= penalty
            score_factors["wind"] = f"Moderate winds ({wind:.1f} km/h, -{penalty:.1f} points)"
        else:
            penalty = 20 + (wind - 25) * 3
            score -= penalty
            score_factors["wind"] = f"Strong winds ({wind:.1f} km/h, -{penalty:.1f} points)"

        # 3. Precipitation scoring
        if precip == 0:
            bonus = 15
            score += bonus
            score_factors["precipitation"] = f"No rain (0.0 mm, +{bonus} points)"
        elif precip < 2:
            penalty = precip * 10
            score -= penalty
            score_factors["precipitation"] = f"Light rain ({precip:.1f} mm, -{penalty:.1f} points)"
        else:
            penalty = 20 + (precip - 2) * 5
            score -= penalty
            score_factors["precipitation"] = f"Significant rain ({precip:.1f} mm, -{penalty:.1f} points)"

        # 4. Snow scoring
        if snow > 0:
            penalty = 50 + snow * 10
            score -= penalty
            score_factors["snow"] = f"Snowfall detected ({snow:.1f} mm, -{penalty:.1f} points)"

        # 5. Cloud cover scoring
        if clouds < 20:
            bonus = 15
            score += bonus
            score_factors["clouds"] = f"Clear skies ({clouds:.0f}% cloud cover, +{bonus} points)"
        elif clouds < 40:
            bonus = 10
            score += bonus
            score_factors["clouds"] = f"Few clouds ({clouds:.0f}% cloud cover, +{bonus} points)"
        elif clouds < 70:
            penalty = (clouds - 40) / 3
            score -= penalty
            score_factors["clouds"] = f"Partly cloudy ({clouds:.0f}% cloud cover, -{penalty:.1f} points)"
        else:
            penalty = 10 + (clouds - 70) / 3
            score -= penalty
            score_factors["clouds"] = f"Overcast ({clouds:.0f}% cloud cover, -{penalty:.1f} points)"

        # 6. Humidity scoring
        if humidity > 90:
            penalty = (humidity - 90) * 2
            score -= penalty
            score_factors["humidity"] = f"Very humid ({humidity:.0f}%, -{penalty:.1f} points)"
        elif humidity > 70:
            penalty = (humidity - 70) / 2
            score -= penalty
            score_factors["humidity"] = f"Humid ({humidity:.0f}%, -{penalty:.1f} points)"

        # 7. Pressure scoring
        if pressure > 1020:
            bonus = 5
            score += bonus
            score_factors["pressure"] = f"High pressure ({pressure:.0f} hPa, +{bonus} points)"
        elif pressure < 1000:
            penalty = min((1000 - pressure) / 2, 20)
            score -= penalty
            score_factors["pressure"] = f"Low pressure ({pressure:.0f} hPa, -{penalty:.1f} points)"
        else:
            bonus = 2
            score += bonus
            score_factors["pressure"] = f"Stable pressure ({pressure:.0f} hPa, +{bonus} points)"

        # Ensure score doesn't go below 0
        score = max(0, score)

        return {
            "score": score,
            "factors": score_factors
        }

    def get_optimal_flying_day(self, location_name):
        """
        Determines the optimal day for flying in the next 6 days based on weather conditions.

        Args:
            location_name (str): The name of the location to check weather for

        Returns:
            dict: Information about the optimal flying day with weather details

        Raises:
            LocationNotFoundException: If the location cannot be found
            ApiRequestException: If an API request fails
        """
        # Get coordinates for the location
        try:
            coordinates = self.get_location_coordinates(location_name)
        except LocationNotFoundException:
            return f"I'm sorry, but I don't have information for the location '{location_name}'. Could you please check the spelling or try a different city?"
        except ApiRequestException as e:
            return f"I'm sorry, I encountered an error while finding your location: {str(e)}"

        # Get weather data for the next 6 days
        days_data = []
        today = datetime.now().date()

        logger.info(f"Analysing weather for {location_name} over the next 6 days...")

        # Loop through the next 6 days to collect weather data
        for day_offset in range(7):  # 0 = today, 1-6 = next six days
            forecast_date = today + timedelta(days=day_offset)

            # Get the weather data
            base_url = "https://my.meteoblue.com/packages/basic-1h"
            params = {
                "apikey": self.api_keys["meteoblue"],
                "lat": coordinates["lat"],
                "lon": coordinates["lon"],
                "asl": "0",
                "format": "json",
                "tz": "UTC"
            }

            try:
                success, response_data = handle_api_request(
                    base_url,
                    params,
                    "Meteoblue (flying day)",
                    cache_type="weather",
                    cache_config=self.cache_config
                )

                if not success:
                    logger.warning(f"Failed to get weather data for day {day_offset} ({forecast_date})")
                    continue

                if "data_1h" not in response_data:
                    logger.warning(f"Missing data_1h in Meteoblue API response for day {day_offset}")
                    continue

                forecast = response_data["data_1h"]

                # Extract relevant data for the day
                day_start_idx = day_offset * 24
                day_end_idx = (day_offset + 1) * 24

                # Calculate daily averages
                temp = sum(forecast.get("temperature", [0] * 24)[day_start_idx:day_end_idx]) / 24
                wind_speed = sum(forecast.get("windspeed", [0] * 24)[day_start_idx:day_end_idx]) / 24
                wind_direction = sum(forecast.get("winddirection", [0] * 24)[day_start_idx:day_end_idx]) / 24
                precip = sum(forecast.get("precipitation", [0] * 24)[day_start_idx:day_end_idx])
                snow = sum(forecast.get("snowfall", [0] * 24)[day_start_idx:day_end_idx])
                humidity = sum(forecast.get("relativehumidity", [0] * 24)[day_start_idx:day_end_idx]) / 24

                # Handle pressure data
                pressure_values = forecast.get("pressure", [0] * 24)[day_start_idx:day_end_idx]
                if all(p == 0 for p in pressure_values):
                    # Use a default standard pressure if data is missing
                    pressure = 1013  # Standard atmospheric pressure in hPa
                else:
                    # Filter out zero values before calculating average
                    valid_pressure = [p for p in pressure_values if p > 0]
                    pressure = sum(valid_pressure) / len(valid_pressure) if valid_pressure else 1013

                cloud_cover = sum(forecast.get("cloudcover", [0] * 24)[day_start_idx:day_end_idx]) / 24

                # Store the data in an array
                days_data.append({
                    "date": forecast_date,
                    "temp": temp,
                    "wind_speed": wind_speed,
                    "wind_direction": wind_direction,
                    "precipitation": precip,
                    "snow": snow,
                    "humidity": humidity,
                    "pressure": pressure,
                    "cloud_cover": cloud_cover,
                    "day_name": forecast_date.strftime('%A')
                })

                logger.info(f"Collected data for {forecast_date.strftime('%A, %Y-%m-%d')}")

            except Exception as e:
                logger.error(f"Error processing data for day {day_offset}: {str(e)}")

        if not days_data:
            return "I couldn't retrieve enough weather data to make a recommendation."

        # Calculate the flying score for each day
        day_scores = []

        for day_data in days_data:
            # Calculate flying score using the shared helper method
            score_result = self._score_flying_conditions(day_data)

            # Add to array of day scores
            day_scores.append({
                "date": day_data["date"],
                "day_name": day_data["day_name"],
                "score": score_result["score"],
                "factors": score_result["factors"],
                "weather_data": day_data
            })

        # Sort days by score (highest first)
        day_scores.sort(key=lambda x: x["score"], reverse=True)

        # Get the best day
        best_day = day_scores[0]

        # Format the result
        result = {
            "location": coordinates["name"],
            "best_day": {
                "date": best_day["date"].strftime('%Y-%m-%d'),
                "day_name": best_day["day_name"],
                "score": best_day["score"],
                "factors": best_day["factors"],
                "weather": best_day["weather_data"]
            },
            "all_days": day_scores
        }

        return result

    async def _get_day_weather_async(self, coordinates, day_offset):
        """
        Get weather data for a specific day offset asynchronously.

        Args:
            coordinates (dict): Location coordinates
            day_offset (int): Day offset from today (0=today, 1=tomorrow, etc.)

        Returns:
            dict: Weather data for the specified day or None if error occurs
        """
        today = datetime.now().date()
        forecast_date = today + timedelta(days=day_offset)

        # Prepare API request
        base_url = "https://my.meteoblue.com/packages/basic-1h"
        params = {
            "apikey": self.api_keys["meteoblue"],
            "lat": coordinates["lat"],
            "lon": coordinates["lon"],
            "asl": "0",
            "format": "json",
            "tz": "UTC"
        }

        try:
            # Use the async version of the API request handler
            success, response_data = await handle_api_request_async(
                base_url,
                params,
                f"Meteoblue (async day {day_offset})",
                cache_type="weather",
                cache_config=self.cache_config
            )

            if not success:
                logger.warning(f"Failed to get weather data for day {day_offset} ({forecast_date}) [async]")
                return None

            if "data_1h" not in response_data:
                logger.warning(f"Missing data_1h in Meteoblue API response for day {day_offset} [async]")
                return None

            forecast = response_data["data_1h"]

            # Extract relevant data for the day
            day_start_idx = day_offset * 24
            day_end_idx = (day_offset + 1) * 24

            # Calculate daily averages
            temp = sum(forecast.get("temperature", [0] * 24)[day_start_idx:day_end_idx]) / 24
            wind_speed = sum(forecast.get("windspeed", [0] * 24)[day_start_idx:day_end_idx]) / 24
            wind_direction = sum(forecast.get("winddirection", [0] * 24)[day_start_idx:day_end_idx]) / 24
            precip = sum(forecast.get("precipitation", [0] * 24)[day_start_idx:day_end_idx])
            snow = sum(forecast.get("snowfall", [0] * 24)[day_start_idx:day_end_idx])
            humidity = sum(forecast.get("relativehumidity", [0] * 24)[day_start_idx:day_end_idx]) / 24

            # Handle pressure data
            pressure_values = forecast.get("pressure", [0] * 24)[day_start_idx:day_end_idx]
            if all(p == 0 for p in pressure_values):
                pressure = 1013  # Standard atmospheric pressure in hPa
            else:
                valid_pressure = [p for p in pressure_values if p > 0]
                pressure = sum(valid_pressure) / len(valid_pressure) if valid_pressure else 1013

            cloud_cover = sum(forecast.get("cloudcover", [0] * 24)[day_start_idx:day_end_idx]) / 24

            # Return the data as a dictionary
            return {
                "date": forecast_date,
                "temp": temp,
                "wind_speed": wind_speed,
                "wind_direction": wind_direction,
                "precipitation": precip,
                "snow": snow,
                "humidity": humidity,
                "pressure": pressure,
                "cloud_cover": cloud_cover,
                "day_name": forecast_date.strftime('%A')
            }

        except Exception as e:
            logger.error(f"Error processing async data for day {day_offset}: {str(e)}")
            return None

    async def get_optimal_flying_day_async(self, location_name):
        """
        Asynchronous version of get_optimal_flying_day that fetches weather data for all days in parallel.

        Args:
            location_name (str): The name of the location to check weather for

        Returns:
            dict: Information about the optimal flying day with weather details
        """
        # Get coordinates for the location (synchronous for now)
        try:
            coordinates = self.get_location_coordinates(location_name)
        except LocationNotFoundException:
            return f"I'm sorry, but I don't have information for the location '{location_name}'. Could you please check the spelling or try a different city?"
        except ApiRequestException as e:
            return f"I'm sorry, I encountered an error while finding your location: {str(e)}"

        logger.info(f"Analysing weather for {location_name} over the next 6 days using async operations...")

        # Create tasks for all 7 days (0=today through 6=+6 days)
        tasks = []
        for day_offset in range(7):
            task = self._get_day_weather_async(coordinates, day_offset)
            tasks.append(task)

        # Run all tasks concurrently and wait for all results
        days_data_results = await asyncio.gather(*tasks)

        # Filter out any None results (failed requests)
        days_data = [day_data for day_data in days_data_results if day_data is not None]

        if not days_data:
            return "I couldn't retrieve enough weather data to make a recommendation."

        # Calculate flying scores for each day
        day_scores = []

        for day_data in days_data:
            # Calculate flying score using the shared helper method
            score_result = self._score_flying_conditions(day_data)

            # Add to day scores
            day_scores.append({
                "date": day_data["date"],
                "day_name": day_data["day_name"],
                "score": score_result["score"],
                "factors": score_result["factors"],
                "weather_data": day_data
            })

        # Sort days by score (highest first)
        day_scores.sort(key=lambda x: x["score"], reverse=True)

        # Get the best day
        best_day = day_scores[0]

        # Format the result
        result = {
            "location": coordinates["name"],
            "best_day": {
                "date": best_day["date"].strftime('%Y-%m-%d'),
                "day_name": best_day["day_name"],
                "score": best_day["score"],
                "factors": best_day["factors"],
                "weather": best_day["weather_data"]
            },
            "all_days": day_scores
        }

        return result
