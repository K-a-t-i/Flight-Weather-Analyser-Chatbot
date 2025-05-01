import json
import os
from datetime import datetime, timedelta
from openai import OpenAI
from dotenv import load_dotenv

# Import utility functions from the utils module
from utils import (
    get_env_variable,
    parse_date,
    logger
)

# Import Config and WeatherService
from config import Config
from weather_service import (
    WeatherService,
    LocationNotFoundException,
    ApiRequestException
)

# Load environment variables
load_dotenv()

# Initialise configuration
config = Config()

try:
    # Initialise OpenAI API
    client = OpenAI(api_key=config.api_keys["openai"])
    logger.info("Successfully initialised OpenAI client")

    # Initialise the WeatherService with the config
    weather_service = WeatherService(config=config)
    logger.info("Successfully initialised WeatherService with Config")

    # Create cache directory if it doesn't exist and caching is enabled
    if config.cache_config['enabled'] and not os.path.exists(config.cache_config['directory']):
        os.makedirs(config.cache_config['directory'])
        logger.info(f"Created cache directory: {config.cache_config['directory']}")
except Exception as e:
    logger.error(f"Failed to initialise services: {str(e)}")
    raise

def format_optimal_flying_day_response(flying_data):
    """
    Formats the suitable flying day data into a readable response.
    """
    # Check if there is an error message instead of data
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

    # Helper function to format value with default indicator
    def format_value(value, property_name, format_str):
        # Check if the value is a default value
        is_default = False

        # Define default values for comparison
        default_values = {
            "temp": 15.0,
            "wind_speed": 0.0,
            "wind_direction": 0.0,
            "precipitation": None,  # 0 is valid measurement
            "snow": None,  # 0 is valid measurement
            "humidity": 50.0,
            "pressure": 1013.0,
            "cloud_cover": None,  # 0 is valid measurement
        }

        # Check common default values based on property
        if property_name in default_values:
            default_value = default_values[property_name]
            if default_value is None:
                # For properties where 0 is valid (precipitation, snow, cloud_cover)
                is_default = value is None
            else:
                # For other properties, check with small tolerance for floating-point comparison
                is_default = value is None or abs(value - default_value) < 0.01

        formatted = format_str.format(value)
        indicator = "(default value)" if is_default else "(current value)"
        return f"{formatted} {indicator}"

    response += "**Weather conditions:**\n"
    weather = best_day["weather"]
    response += f"- Temperature: {format_value(weather['temp'], 'temp', '{:.1f}°C')}\n"
    response += f"- Wind: {format_value(weather['wind_speed'], 'wind_speed', '{:.1f} km/h')} from {format_value(weather['wind_direction'], 'wind_direction', '{:.0f}°')}\n"
    response += f"- Precipitation: {format_value(weather['precipitation'], 'precipitation', '{:.1f} mm')}\n"
    response += f"- Cloud cover: {format_value(weather['cloud_cover'], 'cloud_cover', '{:.0f}%')}\n"
    response += f"- Humidity: {format_value(weather['humidity'], 'humidity', '{:.0f}%')}\n"
    response += f"- Pressure: {format_value(weather['pressure'], 'pressure', '{:.0f} hPa')}\n\n"

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

    try:
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
            # Use the default location from config if none provided
            location = function_args.get("location", config.default_location)
            logger.info(f"Extracted location from query: {location}")

            # Get and format the optimal flying day information
            flying_data = weather_service.get_optimal_flying_day(location)
            return format_optimal_flying_day_response(flying_data)
        else:
            logger.warning("No function call in OpenAI response")
            return "I need a location to check for optimal flying conditions. Please specify a city or area."
    except Exception as e:
        logger.error(f"Error in handling flying day request: {str(e)}")
        return "I'm sorry, I encountered an error while processing your request. Please try again."

def handle_conversation(query):
    """
    Handle a user query by determining if it's a weather question or general conversation.

    Args:
        query (str): The user's input

    Returns:
        str: Response to the user
    """
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

    try:
        logger.info(f"Processing query: {query}")
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": f"You are a helpful assistant that can engage in general conversation and "
                                              f"provide weather information when asked. You can provide historical weather "
                                              f"data for past dates, current weather, and forecasts for up to 6 days in the "
                                              f"future. If the user doesn't specify a location or date for weather, assume "
                                              f"they're asking about {config.default_location} for today."},
                {"role": "user", "content": query}
            ],
            functions=functions,
            function_call="auto"
        )

        message = response.choices[0].message

        if message.function_call:
            function_name = message.function_call.name
            function_args = json.loads(message.function_call.arguments)
            logger.info(f"Function call: {function_name} with args: {function_args}")

            if function_name == "get_weather":
                # Use the default location from config if none provided
                location = function_args.get("location", config.default_location)
                date_string = function_args.get("date", "today")

                try:
                    # Use the WeatherService to get weather data
                    weather_info = weather_service.get_weather(location, date_string)
                    return weather_info
                except ValueError as e:
                    logger.error(f"Date parsing error: {str(e)}")
                    return f"I am happy to tell you the weather, if you give me a date and location. And I'm sorry, I couldn't understand this date. {str(e)}"
            else:
                logger.warning(f"Unknown function call: {function_name}")
                return "I'm sorry, I don't know how to handle that request."
        else:
            # If no function was called, it means the query wasn't about weather
            logger.info("No function call - regular conversation")
            return message.content

    except Exception as e:
        logger.error(f"Error handling conversation: {str(e)}")
        return "I'm sorry, I encountered an error while processing your request. Please try again."

def main():
    """Main function to run the weather chatbot."""
    logger.info("Starting Weather Chatbot with flight weather analyser")
    print("Welcome to our Weather Chatbot with flight weather analyser initialised by Sasha & Fabian & Fabio.")
    print(f"Default location set to: {config.default_location}")
    print("You can ask about the weather for any location in the world, for past dates, today, and up to 6 days in the future.")
    print("You can also ask for the appropriate day for flying in any location!")
    print("Type 'exit' to quit the chatbot.")

    flying_mode = False  # Track if we're in flying analysis mode
    flying_keywords = ["fly", "flying", "flight", "optimal", "best day", "pilot"]

    while True:
        user_input = input("\nYou: ").strip()
        if user_input.lower() == 'exit':
            logger.info("User exited the application")
            print("Goodbye!")
            break

        try:
            # Check if we're in flying mode waiting for a location
            if flying_mode and not any(keyword in user_input.lower() for keyword in flying_keywords):
                # User is providing just a location after being asked
                logger.info(f"Processing location for flying day: {user_input}")
                response = handle_flying_day_request(f"What is the best day to fly in {user_input}?")
                flying_mode = False
            # Check if this is a new flying day request
            elif any(keyword in user_input.lower() for keyword in flying_keywords):
                logger.info("Detected flying day request")
                # Check if location is specified
                location_specified = False
                # Use a check for common prepositions that might indicate a location
                location_prepositions = ["in", "at", "near", "for"]
                for prep in location_prepositions:
                    if f" {prep} " in f" {user_input.lower()} ":
                        location_specified = True
                        break

                if not location_specified:
                    logger.info("No location specified for flying day request")
                    print(f"Chatbot: I need a location to check for optimal flying conditions. Please specify a city or area.")
                    flying_mode = True
                    continue
                else:
                    response = handle_flying_day_request(user_input)
                    flying_mode = False
            else:
                logger.info("Processing general conversation query")
                response = handle_conversation(user_input)
                flying_mode = False

            print(f"Chatbot: {response}")
        except Exception as e:
            logger.error(f"Error in main loop: {str(e)}")
            print(f"Chatbot: I'm sorry, I encountered an error: {str(e)}")
            flying_mode = False

if __name__ == "__main__":
    main()
