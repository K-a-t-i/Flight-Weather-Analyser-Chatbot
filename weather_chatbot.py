import os
import requests
import json
import logging
from datetime import datetime, timedelta
from openai import OpenAI
from dotenv import load_dotenv
import dateparser

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

def get_env_variable(var_name, default=None, required=False):
    """
    Get an environment variable with optional default value and requirement check.

    Args:
        var_name (str): Name of the environment variable
        default (any, optional): Default value if variable is not found
        required (bool): Whether the variable is required

    Returns:
        The environment variable value or default

    Raises:
        ValueError: If the variable is required but not found
    """
    value = os.getenv(var_name, default)
    if value is None and required:
        error_msg = f"Required environment variable {var_name} not set"
        logger.error(error_msg)
        raise ValueError(error_msg)
    return value

# Set up API keys with validation
OPENAI_API_KEY = get_env_variable("OPENAI_API_KEY", required=True)  # chatbot
METEOBLUE_API_KEY = get_env_variable("METEOBLUE_API_KEY", required=True)  # future_weather_data
OPENCAGE_API_KEY = get_env_variable("OPENCAGE_API_KEY", required=True)  # location_coordinates
VISUALCROSSING_API_KEY = get_env_variable("VISUALCROSSING_API_KEY", required=True)  # historical_weather_data

try:
    # Initialise OpenAI API
    client = OpenAI(api_key=OPENAI_API_KEY)
    logger.info("Successfully initialized OpenAI client")
except Exception as e:
    logger.error(f"Failed to initialize OpenAI client: {str(e)}")
    raise

def get_future_weather_data(location, date):
    base_url = "https://my.meteoblue.com/packages/basic-1h"
    params = {
        "apikey": METEOBLUE_API_KEY,
        "lat": location["lat"],
        "lon": location["lon"],
        "asl": "0",
        "format": "json",
        "tz": "UTC"
    }

    response = requests.get(base_url, params=params)
    if response.status_code == 200:
        data = response.json()

        if "data_1h" not in data:
            return "Sorry, I couldn't retrieve detailed weather information at this time."

        forecast = data["data_1h"]

        date_index = (date - datetime.now().date()).days
        if 0 <= date_index <= 6:
            # Get the average values for the day
            temp = sum(forecast.get("temperature", [0] * 24)[date_index*24:(date_index+1)*24]) / 24
            wind_speed = sum(forecast.get("windspeed", [0] * 24)[date_index*24:(date_index+1)*24]) / 24
            wind_direction = sum(forecast.get("winddirection", [0] * 24)[date_index*24:(date_index+1)*24]) / 24
            precip = sum(forecast.get("precipitation", [0] * 24)[date_index*24:(date_index+1)*24])
            snow = sum(forecast.get("snowfall", [0] * 24)[date_index*24:(date_index+1)*24])
            relative_humidity = sum(forecast.get("relativehumidity", [0] * 24)[date_index*24:(date_index+1)*24]) / 24
            pressure = sum(forecast.get("pressure", [0] * 24)[date_index*24:(date_index+1)*24]) / 24
            cloud_cover = sum(forecast.get("cloudcover", [0] * 24)[date_index*24:(date_index+1)*24]) / 24

            return format_weather_info(location, date, temp, wind_speed, wind_direction, precip, snow, relative_humidity, pressure, cloud_cover)
        else:
            return "Sorry, I can only provide weather information for today and the next 6 days."
    else:
        return "Sorry, I couldn't retrieve the weather information at this time."

def get_historical_weather_data(location, date):
    base_url = (f"https://weather.visualcrossing.com/VisualCrossingWebServices/rest/services/timeline/{location['lat']},"
                f"{location['lon']}/{date.strftime('%Y-%m-%d')}")
    params = {
        "unitGroup": "metric",
        "key": VISUALCROSSING_API_KEY,
        "contentType": "json",
    }

    response = requests.get(base_url, params=params)
    if response.status_code == 200:
        data = response.json()
        day_data = data['days'][0]

        temp = day_data['temp']
        wind_speed = day_data['windspeed']
        wind_direction = day_data['winddir']
        precip = day_data['precip']
        snow = day_data['snow']
        relative_humidity = day_data['humidity']
        pressure = day_data['pressure']
        cloud_cover = day_data['cloudcover']

        return format_weather_info(location, date, temp, wind_speed, wind_direction, precip, snow, relative_humidity, pressure, cloud_cover, is_historical=True)
    else:
        return "Sorry, I couldn't retrieve the historical weather information at this time."

def format_weather_info(location, date, temp, wind_speed, wind_direction, precip, snow, relative_humidity, pressure,
                        cloud_cover, is_historical=False):
    # Convert wind speed to knots (1 km/h ≈ 0.54 knots)
    wind_speed_knots = wind_speed * 0.54

    # Estimating fog/mist
    fog_or_mist = "No fog/mist reported" if relative_humidity < 90 else "Possible fog/mist (FG/BR)"

    # Weather condition determination
    if snow > 0:
        condition = "snowy"
    elif precip > 5:
        condition = "rainy"
    elif relative_humidity > 90:
        condition = "foggy"
    elif cloud_cover < 20:
        condition = "sunny"
    elif cloud_cover < 70:
        condition = "partly cloudy"
    else:
        condition = "cloudy"

    if temp < 0:
        condition = "freezing " + condition
    elif temp > 30:
        condition = "hot and " + condition

    verb = "was" if is_historical else "is expected to be"

    # Formatting the output
    weather_info = f"""On {date.strftime('%Y-%m-%d')}, the weather in {location['name']} {verb} {condition}. 
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

def get_location_coordinates(location_name):
    base_url = "https://api.opencagedata.com/geocode/v1/json"
    params = {
        "q": location_name,
        "key": OPENCAGE_API_KEY,
        "limit": 1
    }

    response = requests.get(base_url, params=params)
    if response.status_code == 200:
        data = response.json()
        if data["results"]:
            result = data["results"][0]
            return {
                "lat": result["geometry"]["lat"],
                "lon": result["geometry"]["lng"],
                "name": result["formatted"]
            }
    return None

def parse_date(date_string):
    # Handle day names first
    days = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
    day_name = date_string.lower()
    if day_name in days:
        current_date = datetime.now().date()
        current_day = current_date.weekday()
        target_day = days.index(day_name)
        days_ahead = target_day - current_day
        if days_ahead <= 0:  # Target day is today or in the past week
            days_ahead += 7
        return current_date + timedelta(days=days_ahead)

    # If not a day name, use dateparser
    parsed_date = dateparser.parse(date_string, settings={'RELATIVE_BASE': datetime.now(),
                                                          'PREFER_DATES_FROM': 'future'})
    if parsed_date:
        return parsed_date.date()
    else:
        raise ValueError(f"Unable to parse date: {date_string}")

def get_weather(location, date):
    coordinates = get_location_coordinates(location)
    if coordinates is None:
        return (f"I'm sorry, but I don't have information for the location '{location}'. "
                f"Could you please check the spelling or try asking about a different city?")

    today = datetime.now().date()
    if date < today:
        weather_data = get_historical_weather_data(coordinates, date)
    else:
        weather_data = get_future_weather_data(coordinates, date)
    return weather_data

def get_optimal_flying_day(location):
    """
    Determines the optimal day for flying in the next 6 days based on weather conditions.

    Parameters:
    location (str): The name of the location to check weather for

    Returns:
    dict: Information about the optimal flying day with weather details
    """
    # Get coordinates for the location
    coordinates = get_location_coordinates(location)
    if coordinates is None:
        return (f"I'm sorry, but I don't have information for the location '{location}'. Could you please check the "
                f"spelling or try a different city?")

    # Get weather data for the next 6 days
    days_data = []
    today = datetime.now().date()

    print(f"Analysing weather for {location} over the next 6 days...")

    # Loop through the next 6 days to collect weather data
    for day_offset in range(7):  # 0 = today, 1-6 = next six days
        forecast_date = today + timedelta(days=day_offset)

        # Get the weather data
        base_url = "https://my.meteoblue.com/packages/basic-1h"
        params = {
            "apikey": METEOBLUE_API_KEY,
            "lat": coordinates["lat"],
            "lon": coordinates["lon"],
            "asl": "0",
            "format": "json",
            "tz": "UTC"
        }

        response = requests.get(base_url, params=params)
        if response.status_code != 200:
            continue

        data = response.json()
        if "data_1h" not in data:
            continue

        forecast = data["data_1h"]

        # Extract relevant data for the day
        try:
            day_start_idx = day_offset * 24
            day_end_idx = (day_offset + 1) * 24

            # Calculate daily averages and totals from hourly data
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

            # Store the data in an array
            days_data.append({
                "date": forecast_date,
                "temp": temp,
                "wind_speed": wind_speed,
                "wind_direction": wind_direction,
                "precipitation": precip,
                "snow": snow,
                "humidity": relative_humidity,
                "pressure": pressure,
                "cloud_cover": cloud_cover,
                "day_name": forecast_date.strftime('%A')
            })

            print(f"Collected data for {forecast_date.strftime('%A, %Y-%m-%d')}")

        except Exception as e:
            print(f"Error processing data for day {day_offset}: {str(e)}")

    if not days_data:
        return "I couldn't retrieve enough weather data to make a recommendation."

    # Calculate the flying score for each day based on relevant criteria
    # Using a dictionary to store scores with appropriate weighting
    day_scores = []

    for day_data in days_data:
        # Initialise score
        score = 100

        # Dictionary to store conditions that affected the score
        score_factors = {}

        # Apply conditional scoring based on meteorological factors important for general aviation

        # 1. Temperature - ideal range is 10-25°C
        temp = day_data["temp"]
        if temp < 5:
            penalty = (5 - temp) * 3
            score -= penalty
            score_factors["temperature"] = f"Too cold ({temp:.1f}°C, -{penalty:.1f} points)"
        elif temp > 30:
            penalty = (temp - 30) * 2
            score -= penalty
            score_factors["temperature"] = f"Too hot ({temp:.1f}°C, -{penalty:.1f} points)"
        else:
            # Optimal temperature bonus
            if 10 <= temp <= 25:
                bonus = 5
                score += bonus
                score_factors["temperature"] = f"Ideal temperature ({temp:.1f}°C, +{bonus} points)"

        # 2. Wind speed - ideal is below 15 km/h
        wind = day_data["wind_speed"]
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

        # 3. Precipitation - ideally none
        precip = day_data["precipitation"]
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

        # 4. Snow - any snow is bad for flying
        snow = day_data["snow"]
        if snow > 0:
            penalty = 50 + snow * 10
            score -= penalty
            score_factors["snow"] = f"Snowfall detected ({snow:.1f} mm, -{penalty:.1f} points)"

        # 5. Cloud cover - clearer is better
        clouds = day_data["cloud_cover"]
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

        # 6. Humidity - lower is better for visibility
        humidity = day_data["humidity"]
        if humidity > 90:
            penalty = (humidity - 90) * 2
            score -= penalty
            score_factors["humidity"] = f"Very humid ({humidity:.0f}%, -{penalty:.1f} points)"
        elif humidity > 70:
            penalty = (humidity - 70) / 2
            score -= penalty
            score_factors["humidity"] = f"Humid ({humidity:.0f}%, -{penalty:.1f} points)"

        # 7. Pressure - stable high pressure is best
        pressure = day_data["pressure"]
        if pressure > 1020:
            bonus = 5
            score += bonus
            score_factors["pressure"] = f"High pressure ({pressure:.0f} hPa, +{bonus} points)"
        elif pressure < 1000:
            # Cap the penalty to avoid extreme values
            penalty = min((1000 - pressure) / 2, 20)
            score -= penalty
            score_factors["pressure"] = f"Low pressure ({pressure:.0f} hPa, -{penalty:.1f} points)"
        else:
            # Standard pressure is good for flying
            bonus = 2
            score += bonus
            score_factors["pressure"] = f"Stable pressure ({pressure:.0f} hPa, +{bonus} points)"

        # Ensure score doesn't go below 0
        score = max(0, score)

        # Add to array of day scores
        day_scores.append({
            "date": day_data["date"],
            "day_name": day_data["day_name"],
            "score": score,
            "factors": score_factors,
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

def format_optimal_flying_day_response(flying_data):
    """
    Formats the suitable flying day data into a readable response.
    """
    # Check if we have an error message instead of data
    if isinstance(flying_data, str):
        return flying_data

    location = flying_data["location"]
    best_day = flying_data["best_day"]
    all_days = flying_data["all_days"]

    # Base score
    base_score = 100

    # Format the best day information
    response = f"🛫 **OPTIMAL FLYING DAY FOR {location.upper()}** 🛫\n\n"

    # Process all days
    for day in all_days:
        # Extract and calculate factors
        bonus_sum = 0
        penalty_sum = 0
        bonus_factors = []
        penalty_factors = []

        for factor, description in day["factors"].items():
            if "+" in description:
                parts = description.split(", +")
                if len(parts) == 2 and parts[1].endswith(" points)"):
                    bonus_value = float(parts[1].replace(" points)", ""))
                    factor_name = parts[0].split("(")[0].strip()
                    bonus_factors.append((factor_name, int(round(bonus_value))))
                    bonus_sum += bonus_value
            elif "-" in description and not description.startswith("No"):
                parts = description.split(", -")
                if len(parts) == 2 and parts[1].endswith(" points)"):
                    penalty_value = float(parts[1].replace(" points)", ""))
                    factor_name = parts[0].split("(")[0].strip()
                    penalty_factors.append((factor_name, int(round(penalty_value))))
                    penalty_sum += penalty_value

        # Store the exact calculations
        day["exact_bonus_sum"] = bonus_sum
        day["exact_penalty_sum"] = penalty_sum
        day["net_effect"] = bonus_sum - penalty_sum
        day["exact_score"] = base_score + day["net_effect"]
        day["bonus_factors"] = bonus_factors
        day["penalty_factors"] = penalty_factors

        # Round for display
        day["display_score"] = int(round(day["exact_score"]))
        day["display_net"] = int(round(day["net_effect"]))

    # Process best day for display
    best_day_data = next((d for d in all_days if d["date"] == best_day["date"]), None)
    if best_day_data:
        best_score = best_day_data["display_score"]
        best_net = best_day_data["display_net"]
    else:
        # Fallback if not found
        best_score = int(round(best_day["score"]))
        best_net = best_score - base_score

    if best_net >= 0:
        response += f"The best day for flying in the next week is **{best_day['day_name']}, {best_day['date']}** "
        response += f"with a flying condition score of {best_score} (base:100 + {best_net} bonus).\n\n"
    else:
        response += f"The best day for flying in the next week is **{best_day['day_name']}, {best_day['date']}** "
        response += f"with a flying condition score of {best_score} (base:100 - {abs(best_net)} penalty).\n\n"

    response += "**Weather conditions:**\n"
    weather = best_day["weather"]
    response += f"- Temperature: {weather['temp']:.1f}°C\n"
    response += f"- Wind: {weather['wind_speed']:.1f} km/h from {weather['wind_direction']:.0f}°\n"
    response += f"- Precipitation: {weather['precipitation']:.1f} mm\n"
    response += f"- Cloud cover: {weather['cloud_cover']:.0f}%\n"
    response += f"- Humidity: {weather['humidity']:.0f}%\n"
    response += f"- Pressure: {weather['pressure']:.0f} hPa\n\n"

    response += "**Analysis factors:**\n"
    for factor, description in best_day["factors"].items():
        response += f"- {description}\n"

    response += "\n**All days ranked:**\n"

    # Sort days by recalculated score
    sorted_days = sorted([d for d in all_days if d is not best_day_data],
                         key=lambda x: x["exact_score"], reverse=True)

    for i, day in enumerate(all_days, 1):
        score = day["display_score"]
        net = day["display_net"]

        if day['date'] == best_day['date']:
            # This is the best day, so include a marker
            display_date = f"**{day['day_name']}, {day['date']}**"
        else:
            display_date = f"{day['day_name']}, {day['date'].strftime('%Y-%m-%d')}"

        if net >= 0:
            response += f"{i}. {display_date} - Score: {score} (base:100 + {net} bonus)\n"
        else:
            response += f"{i}. {display_date} - Score: {score} (base:100 - {abs(net)} penalty)\n"

        # Add factors
        if day["bonus_factors"]:
            bonus_str = ", ".join([f"{name}: +{value}" for name, value in day["bonus_factors"]])
            response += f"   Positive factors: {bonus_str}\n"
        if day["penalty_factors"]:
            penalty_str = ", ".join([f"{name}: -{value}" for name, value in day["penalty_factors"]])
            response += f"   Challenging factors: {penalty_str}\n"
        response += "\n"

    return response

def handle_flying_day_request(query):
    """
    Handles a user request to find the optimal flying day.

    Parameters:
    query (str): The user's query

    Returns:
    str: A response about the optimal flying day
    """
    # Extract location from query using OpenAI
    functions = [
        {
            "name": "get_optimal_flying_day",
            "description": "Get the optimal day for flying in a specific location",
            "parameters": {
                "type": "object",
                "properties": {
                    "location": {
                        "type": "string",
                        "description": "The city or location to check for optimal flying conditions"
                    }
                },
                "required": ["location"]
            }
        }
    ]

    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "You analyse queries to determine locations for finding optimal flying days."},
            {"role": "user", "content": query}
        ],
        functions=functions,
        function_call="auto"
    )

    message = response.choices[0].message

    if message.function_call:
        function_args = json.loads(message.function_call.arguments)
        location = function_args.get("location", "Berlin")

        # Get and format the optimal flying day information
        flying_data = get_optimal_flying_day(location)
        return format_optimal_flying_day_response(flying_data)
    else:
        return "I need a location to check for optimal flying conditions. Please specify a city or area."

def handle_conversation(query):
    functions = [
        {
            "name": "get_weather",
            "description": "Get weather information for a specific location and date (past, present, or up to 6 days in the future)",
            "parameters": {
                "type": "object",
                "properties": {
                    "location": {
                        "type": "string",
                        "description": "The city or location for the weather forecast"
                    },
                    "date": {
                        "type": "string",
                        "description": "The date for the weather forecast (e.g., 'today', 'tomorrow', 'next Monday', 'September 26, 2024')"
                    }
                },
                "required": ["location", "date"]
            }
        }
    ]

    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "You are a helpful assistant that can engage in general conversation and "
                                          "provide weather information when asked. You can provide historical weather "
                                          "data for past dates, current weather, and forecasts for up to 6 days in the "
                                          "future. If the user doesn't specify a location or date for weather, assume "
                                          "they're asking about Berlin for today."},
            {"role": "user", "content": query}
        ],
        functions=functions,
        function_call="auto"
    )

    message = response.choices[0].message

    if message.function_call:
        function_name = message.function_call.name
        function_args = json.loads(message.function_call.arguments)

        if function_name == "get_weather":
            location = function_args.get("location", "Berlin")
            date_string = function_args.get("date", "today")

            try:
                date = parse_date(date_string)
                today = datetime.now().date()

                if (date - today).days > 6:
                    return (f"I'm sorry, but I can only provide weather for the past, today and up to 6 days "
                            f"in the future. The date you asked about ({date.strftime('%Y-%m-%d')}) is too far "
                            f"in the future. The latest date I can provide a forecast for is "
                            f"{(today + timedelta(days=6)).strftime('%Y-%m-%d')}. Would you like to know the "
                            f"weather for {location} on that date instead?")

                weather_info = get_weather(location, date)

                return weather_info
            except ValueError as e:
                return f"I am happy to tell you the weather, if you give me a date and location. And I'm sorry, I couldn't understand this date. {str(e)}"
        else:
            return "I'm sorry, I don't know how to handle that request."
    else:
        # If no function was called, it means the query wasn't about weather
        return message.content

def main():
    print("Welcome to our Weather Chatbot with flight weather analyser initialised by Sasha & Fabian & Fabio.")
    print("You can ask about the weather for any location in the world, for past dates, today, and up to 6 days in the future.")
    print("You can also ask for the appropriate day for flying in any location!")
    print("Type 'exit' to quit the chatbot.")

    flying_mode = False  # Track if we're in flying analysis mode
    default_location = "Markt Nordheim"
    flying_keywords = ["fly", "flying", "flight", "optimal", "best day", "pilot"]

    while True:
        user_input = input("\nYou: ").strip()
        if user_input.lower() == 'exit':
            print("Goodbye!")
            break

        try:
            # Check if we're in flying mode waiting for a location
            if flying_mode and not any(keyword in user_input.lower() for keyword in flying_keywords):
                # User is providing just a location after being asked
                response = handle_flying_day_request(f"What is the best day to fly in {user_input}?")
                flying_mode = False
            # Check if this is a new flying day request
            elif any(keyword in user_input.lower() for keyword in flying_keywords):
                # Check if location is specified
                location_specified = False
                # Use a check for common prepositions that might indicate a location
                location_prepositions = ["in", "at", "near", "for"]
                for prep in location_prepositions:
                    if f" {prep} " in f" {user_input.lower()} ":
                        location_specified = True
                        break

                if not location_specified:
                    print(f"Chatbot: I need a location to check for optimal flying conditions. Please specify a city or area.")
                    flying_mode = True
                    continue
                else:
                    response = handle_flying_day_request(user_input)
                    flying_mode = False
            else:
                response = handle_conversation(user_input)
                flying_mode = False

            print(f"Chatbot: {response}")
        except Exception as e:
            print(f"Chatbot: I'm sorry, I encountered an error: {str(e)}")
            flying_mode = False

if __name__ == "__main__":
    main()
