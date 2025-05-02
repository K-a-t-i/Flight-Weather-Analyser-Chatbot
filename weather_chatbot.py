import json
import os
import time
import sys
from datetime import datetime, timedelta
from openai import OpenAI
from dotenv import load_dotenv
import colorama
from colorama import Fore, Back, Style

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

# Import the display manager
from display_manager import WeatherDisplayManager

# Initialise colorama
colorama.init(autoreset=True)

# Load environment variables
load_dotenv()

# Initialise configuration
config = Config()

# Initialise display manager
display_manager = WeatherDisplayManager()

# Available commands for the help menu
COMMANDS = {
    "help": "Display this help message",
    "weather [location] [date]": "Get weather forecast for a location and date",
    "fly [location]": "Find the best day for flying in a location",
    "about": "Show information about this chatbot",
    "exit": "Exit the application"
}

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

def display_loading_indicator(message="Processing"):
    """Display an animated loading indicator whilst waiting."""
    indicators = ['|', '/', '-', '\\']
    i = 0
    message_display = display_manager.format_loading_indicator(message)
    sys.stdout.write(message_display)
    for _ in range(5):  # Shorter animation to avoid long waits
        sys.stdout.write(indicators[i % len(indicators)] + "\r" + message + " ")
        sys.stdout.flush()
        time.sleep(0.2)
        i += 1
    sys.stdout.write("\r" + " " * (len(message) + 2) + "\r")
    sys.stdout.flush()

def format_optimal_flying_day_response(flying_data):
    """
    Formats the suitable flying day data into a readable response with colours.
    """
    # Check if there is an error message instead of data
    if isinstance(flying_data, str):
        return Fore.RED + flying_data

    location = flying_data["location"]
    best_day = flying_data["best_day"]
    all_days = flying_data["all_days"]

    # Base score
    base_score = 100

    # Format the best day information
    response = Fore.CYAN + Style.BRIGHT + f"🛫 OPTIMAL FLYING DAY FOR {location.upper()} 🛫\n\n" + Style.RESET_ALL

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
        response += Fore.GREEN + f"The best day for flying in the next week is " + Style.BRIGHT + f"{best_day['day_name']}, {best_day['date']}" + Style.RESET_ALL
        response += Fore.GREEN + f" with a flying condition score of {best_score} (base:100 + {best_net} bonus).\n\n" + Style.RESET_ALL
    else:
        response += Fore.YELLOW + f"The best day for flying in the next week is " + Style.BRIGHT + f"{best_day['day_name']}, {best_day['date']}" + Style.RESET_ALL
        response += Fore.YELLOW + f" with a flying condition score of {best_score} (base:100 - {abs(best_net)} penalty).\n\n" + Style.RESET_ALL

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
        indicator = Fore.YELLOW + "(default value)" if is_default else Fore.CYAN + "(current value)"
        return f"{formatted} {indicator}"

    response += Fore.BLUE + Style.BRIGHT + "Weather conditions:\n" + Style.RESET_ALL
    weather = best_day["weather"]
    response += f"- Temperature: {format_value(weather['temp'], 'temp', '{:.1f}°C')}\n"
    response += f"- Wind: {format_value(weather['wind_speed'], 'wind_speed', '{:.1f} km/h')} from {format_value(weather['wind_direction'], 'wind_direction', '{:.0f}°')}\n"
    response += f"- Precipitation: {format_value(weather['precipitation'], 'precipitation', '{:.1f} mm')}\n"
    response += f"- Cloud cover: {format_value(weather['cloud_cover'], 'cloud_cover', '{:.0f}%')}\n"
    response += f"- Humidity: {format_value(weather['humidity'], 'humidity', '{:.0f}%')}\n"
    response += f"- Pressure: {format_value(weather['pressure'], 'pressure', '{:.0f} hPa')}\n\n"

    response += Fore.GREEN + Style.BRIGHT + "Analysis factors:\n" + Style.RESET_ALL
    for factor, description in best_day["factors"].items():
        response += f"- {description}\n"

    response += Fore.CYAN + Style.BRIGHT + "\nAll days ranked:\n" + Style.RESET_ALL

    # Sort days by recalculated score
    sorted_days = sorted([d for d in all_days if d is not best_day_data],
                         key=lambda x: x["exact_score"], reverse=True)

    for i, day in enumerate(all_days, 1):
        score = day["display_score"]
        net = day["display_net"]

        # Choose colour based on score
        if score >= 80:
            day_color = Fore.GREEN
        elif score >= 60:
            day_color = Fore.YELLOW
        else:
            day_color = Fore.RED

        if day['date'] == best_day['date']:
            # This is the best day, so include a marker and make it bold
            display_date = Style.BRIGHT + f"{day['day_name']}, {day['date']}" + Style.RESET_ALL
        else:
            display_date = f"{day['day_name']}, {day['date']}"

        if net >= 0:
            response += day_color + f"{i}. {display_date} - Score: {score} (base:100 + {net} bonus)\n"
        else:
            response += day_color + f"{i}. {display_date} - Score: {score} (base:100 - {abs(net)} penalty)\n"

        # Add factors
        if day["bonus_factors"]:
            bonus_str = ", ".join([f"{name}: +{value}" for name, value in day["bonus_factors"]])
            response += Fore.GREEN + f"   Positive factors: {bonus_str}\n" + Style.RESET_ALL
        if day["penalty_factors"]:
            penalty_str = ", ".join([f"{name}: -{value}" for name, value in day["penalty_factors"]])
            response += Fore.YELLOW + f"   Challenging factors: {penalty_str}\n" + Style.RESET_ALL
        response += "\n"

    # Add ASCII art for best day's weather condition if available
    weather_condition = best_day["weather"].get("condition", "")
    if not weather_condition and "cloud_cover" in best_day["weather"]:
        # Determine condition based on weather properties
        cloud_cover = best_day["weather"]["cloud_cover"]
        precipitation = best_day["weather"].get("precipitation", 0)
        snow = best_day["weather"].get("snow", 0)

        if snow > 0:
            weather_condition = "snowy"
        elif precipitation > 5:
            weather_condition = "rainy"
        elif cloud_cover < 30:
            weather_condition = "sunny"
        elif cloud_cover < 70:
            weather_condition = "partly cloudy"
        else:
            weather_condition = "cloudy"

    response += display_manager.format_weather_ascii(weather_condition)

    return response

def handle_flying_day_request(query):
    """
    Handles a user request to find the optimal flying day.

    Parameters:
    query (str): The user's query

    Returns:
    str: A response about the optimal flying day
    """
    # Show loading indicator
    display_loading_indicator("Analysing flying conditions")

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
            return Fore.YELLOW + "I need a location to check for optimal flying conditions. Please specify a city or area."
    except json.JSONDecodeError as e:
        logger.error(f"JSON decode error in OpenAI response: {str(e)}")
        return Fore.RED + "I encountered an error processing the location information. Please try again with a clearer location."
    except Exception as e:
        # Log the specific error for debugging
        error_type = type(e).__name__
        error_message = str(e)
        logger.error(f"Error in handling flying day request: {error_type} - {error_message}")

        # Provide error message based on error type
        if "RateLimitError" in error_type:
            return Fore.RED + "I'm currently experiencing high demand. Please try again in a moment."
        elif "AuthenticationError" in error_type:
            return Fore.RED + "I'm having trouble with my authentication system. Please report this issue to the administrator."
        elif "APIConnectionError" in error_type or "APITimeoutError" in error_type:
            return Fore.RED + "I'm having trouble connecting to my knowledge system. Please check your internet connection and try again."
        else:
            # Generic message for other errors
            return Fore.RED + "I encountered an unexpected error while processing your request. Please try again."

def handle_conversation(query):
    """
    Handle a user query by determining if it's a weather question or general conversation.

    Args:
        query (str): The user's input

    Returns:
        str: Response to the user
    """
    # Show loading indicator
    display_loading_indicator("Processing your question")

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

                    # Extract the condition for ASCII art
                    condition = None
                    for line in weather_info.split('\n'):
                        if "Condition:" in line:
                            condition = line.split(': ')[1] if len(line.split(': ')) > 1 else ""
                            break

                    # Add colours to the weather info
                    colorised_info = display_manager.format_title(f"Weather for {location}")
                    for line in weather_info.split('\n'):
                        if "Temperature:" in line:
                            temp_parts = line.split(': ')
                            if len(temp_parts) > 1:
                                temp = float(temp_parts[1].replace('°C', '').strip())
                                if temp < 5:
                                    colorised_info += Fore.BLUE + line + "\n"
                                elif temp > 30:
                                    colorised_info += Fore.RED + line + "\n"
                                else:
                                    colorised_info += Fore.WHITE + line + "\n"
                            else:
                                colorised_info += line + "\n"
                        elif "Condition:" in line:
                            colorised_info += Fore.YELLOW + line + "\n"
                        elif "Wind:" in line:
                            colorised_info += Fore.CYAN + line + "\n"
                        elif "Warning:" in line:
                            colorised_info += display_manager.format_warning(line.split(": ")[1])
                        else:
                            colorised_info += line + "\n"

                    # Add the ASCII art for the weather condition
                    colorised_info += display_manager.format_weather_ascii(condition)

                    return colorised_info
                except ValueError as e:
                    logger.error(f"Date parsing error: {str(e)}")
                    return Fore.YELLOW + f"I am happy to tell you the weather, if you give me a date and location. And I'm sorry, I couldn't understand this date. {str(e)}"
            else:
                logger.warning(f"Unknown function call: {function_name}")
                return Fore.RED + "I'm sorry, I don't know how to handle that request."
        else:
            # If no function was called, it means the query wasn't about weather
            logger.info("No function call - regular conversation")
            return message.content

    except json.JSONDecodeError as e:
        logger.error(f"JSON decode error in OpenAI response: {str(e)}")
        return Fore.RED + "I encountered an error understanding your question. Could you please rephrase it?"
    except Exception as e:
        # Log error type and message for debugging
        error_type = type(e).__name__
        error_message = str(e)
        logger.error(f"Error handling conversation: {error_type} - {error_message}")

        # Provide responses based on error type
        if "RateLimitError" in error_type:
            return Fore.RED + "I'm currently experiencing high demand. Please try again in a moment."
        elif "AuthenticationError" in error_type:
            return Fore.RED + "I'm having trouble with my authentication system. Please report this issue to the administrator."
        elif "APIConnectionError" in error_type or "APITimeoutError" in error_type:
            return Fore.RED + "I'm having trouble connecting to my knowledge system. Please check your internet connection and try again."
        else:
            # Generic message for other errors
            return Fore.RED + "I'm sorry, I encountered an error while processing your request. Please try again."

def handle_help_command():
    """Display help information about available commands and options."""
    help_text = Fore.CYAN + Style.BRIGHT + "=== Weather Chatbot Help ===" + Style.RESET_ALL + "\n\n"

    # Main Commands Section
    help_text += Fore.YELLOW + Style.BRIGHT + "🔍 MAIN COMMANDS:" + Style.RESET_ALL + "\n"

    help_text += Fore.GREEN + "weather [location] [date]" + Fore.WHITE + " - Get weather forecast for a location and date\n"
    help_text += Fore.CYAN + "  Shortcuts: w, forecast" + "\n"
    help_text += Fore.GREEN + "fly [location]" + Fore.WHITE + " - Find the best day for flying in a location\n"
    help_text += Fore.CYAN + "  Shortcuts: f, flight, flying" + "\n"
    help_text += Fore.GREEN + "help" + Fore.WHITE + " - Display this help message\n"
    help_text += Fore.GREEN + "about" + Fore.WHITE + " - Show information about this chatbot\n"
    help_text += Fore.GREEN + "exit" + Fore.WHITE + " - Exit the application\n"
    help_text += Fore.CYAN + "  Shortcuts: quit, bye, q" + "\n\n"

    # Weather Command Examples
    help_text += Fore.YELLOW + Style.BRIGHT + "🌤️ WEATHER COMMAND EXAMPLES:" + Style.RESET_ALL + "\n"
    help_text += Fore.WHITE + "- weather London tomorrow" + Fore.CYAN + " → Weather in London for tomorrow\n"
    help_text += Fore.WHITE + "- weather Berlin" + Fore.CYAN + f" → Weather in Berlin for today (defaults to today)\n"
    help_text += Fore.WHITE + "- weather Tokyo next Monday" + Fore.CYAN + " → Weather in Tokyo for next Monday\n"
    help_text += Fore.WHITE + "- weather Paris last week" + Fore.CYAN + " → Historical weather for Paris one week ago\n\n"

    # Flying Command Examples
    help_text += Fore.YELLOW + Style.BRIGHT + "✈️ FLYING COMMAND EXAMPLES:" + Style.RESET_ALL + "\n"
    help_text += Fore.WHITE + "- fly Berlin" + Fore.CYAN + " → Best day to fly in Berlin in the next week\n"
    help_text += Fore.WHITE + "- flying in Munich" + Fore.CYAN + " → Best day to fly in Munich in the next week\n"
    help_text += Fore.WHITE + "- flight Zurich" + Fore.CYAN + " → Best day to fly in Zurich in the next week\n\n"

    # Natural Language Examples
    help_text += Fore.YELLOW + Style.BRIGHT + "💬 NATURAL LANGUAGE EXAMPLES:" + Style.RESET_ALL + "\n"
    help_text += Fore.WHITE + "- What's the weather like in Paris today?\n"
    help_text += Fore.WHITE + "- Will it rain in Tokyo on Friday?\n"
    help_text += Fore.WHITE + "- How hot will it be in Rome next week?\n"
    help_text += Fore.WHITE + "- What's the best day to fly in Munich this week?\n"
    help_text += Fore.WHITE + "- Is it a good time to go flying in Sydney?\n\n"

    # Tips
    help_text += Fore.YELLOW + Style.BRIGHT + "💡 TIPS:" + Style.RESET_ALL + "\n"
    help_text += Fore.WHITE + "- Default location is set to: " + Fore.CYAN + f"{Config().default_location}\n"
    help_text += Fore.WHITE + "- Weather forecasts are available for up to 6 days in the future\n"
    help_text += Fore.WHITE + "- Historical weather data is available for past dates\n"
    help_text += Fore.WHITE + "- Flying conditions analysis considers wind, precipitation, cloud cover and more\n"

    return help_text

def handle_about_command():
    """Display information about the chatbot."""
    about_text = Fore.CYAN + Style.BRIGHT + "=== About Weather Chatbot ===" + Style.RESET_ALL + "\n\n"
    about_text += Fore.WHITE + "This Weather Chatbot with flight weather analyser was initialised by Sasha & Fabian, with support from Fabio & Sam.\n\n"
    about_text += Fore.YELLOW + "Features:" + Style.RESET_ALL + "\n"
    about_text += Fore.WHITE + "- Current weather information for any location\n"
    about_text += Fore.WHITE + "- Historical weather data for past dates\n"
    about_text += Fore.WHITE + "- Weather forecasts for up to 6 days in the future\n"
    about_text += Fore.WHITE + "- Optimal flying day analysis for aviation enthusiasts\n"
    about_text += Fore.WHITE + "- Visual weather conditions with ASCII art\n\n"

    about_text += Fore.YELLOW + "APIs Used:" + Style.RESET_ALL + "\n"
    about_text += Fore.WHITE + "- OpenAI for natural language processing\n"
    about_text += Fore.WHITE + "- Meteoblue for weather forecasting\n"
    about_text += Fore.WHITE + "- OpenCage for geocoding\n"
    about_text += Fore.WHITE + "- VisualCrossing for historical weather data\n\n"

    about_text += Fore.RED + "DISCLAIMER: This is a proof-of-concept application intended for educational purposes only.\n"
    about_text += "It should NOT be used for critical decision-making or safety-related activities.\n"
    about_text += "Always consult official weather services for important decisions." + Style.RESET_ALL

    return about_text

def parse_command(user_input):
    """
    Parse user input to determine if it's a command and extract arguments.

    Args:
        user_input (str): The user's input string

    Returns:
        tuple: (command, args) where command is the identified command and args are additional arguments
    """
    input_lower = user_input.lower().strip()

    # Check for exit commands
    if input_lower in ["exit", "quit", "bye", "q"]:
        return "exit", []

    # Check for exact command matches
    if input_lower == "help":
        return "help", []
    elif input_lower == "about":
        return "about", []

    # Check for command prefixes
    words = input_lower.split()
    if len(words) >= 1:
        # Weather command and shortcuts
        if words[0] in ["weather", "w", "forecast"] and len(words) > 1:
            return "weather", words[1:]
        # Fly command and shortcuts
        elif words[0] in ["fly", "flying", "flight", "f"] and len(words) > 1:
            return "fly", words[1:]

    # Not a recognised command
    return None, []

def display_welcome_message():
    """Display a styled welcome message."""
    print(Fore.CYAN + Style.BRIGHT + "=" * 80)
    print(Fore.YELLOW + Style.BRIGHT + """
    __          __        _   _               
    \\ \\        / /       | | | |              
     \\ \\  /\\  / /__  __ _| |_| |__   ___ _ __ 
      \\ \\/  \\/ / _ \\/ _` | __| '_ \\ / _ \\ '__|
       \\  /\\  /  __/ (_| | |_| | | |  __/ |   
        \\/  \\/ \\___|\\__,_|\\__|_| |_|\\___|_|   
                                               
     ____ _           _   _           _   
    / ___| |__   __ _| |_| |__   ___ | |_ 
   | |   | '_ \\ / _` | __| '_ \\ / _ \\| __|
   | |___| | | | (_| | |_| |_) | (_) | |_ 
    \\____|_| |_|\\__,_|\\__|_.__/ \\___/ \\__|
                                           
    """)
    print(Fore.CYAN + Style.BRIGHT + "=" * 80)
    print(Fore.WHITE + "Welcome to our Weather Chatbot with flight weather analyser")
    print(Fore.WHITE + "initialised by Sasha & Fabian. Supported by Fabio & Sam.")
    print(Fore.CYAN + Style.BRIGHT + "=" * 80 + "\n")

    # Show disclaimer
    print(Fore.RED + Style.BRIGHT + "DISCLAIMER:" + Style.RESET_ALL)
    print(Fore.YELLOW + "This is a proof-of-concept application intended for educational purposes only.")
    print("It should NOT be used for critical decision-making or safety-related activities.")
    print("Always consult official weather services for important decisions." + Style.RESET_ALL)
    print(Fore.CYAN + "=" * 80 + "\n")

    # Show usage information
    print(Fore.GREEN + Style.BRIGHT + f"Default location set to: {config.default_location}" + Style.RESET_ALL)
    print(Fore.WHITE + "You can ask about the weather for any location in the world, for past dates, today, and up to 6 days in the future.")
    print(Fore.WHITE + "You can also ask for the appropriate day for flying in any location!")

    # Show example queries
    print(Fore.GREEN + Style.BRIGHT + "\nExample queries:" + Style.RESET_ALL)
    print(Fore.WHITE + "- What's the weather like in Berlin tomorrow?")
    print(Fore.WHITE + "- How was the weather in Paris last Monday?")
    print(Fore.WHITE + "- What's the best day to fly in Munich this week?")
    print(Fore.WHITE + "- Type 'help' to see all available commands")
    print(Fore.WHITE + "- Type 'exit' to quit the chatbot.\n")

def main():
    """Main function to run the weather chatbot."""
    logger.info("Starting Weather Chatbot with flight weather analyser")

    # Display welcome message with colours
    display_welcome_message()

    flying_mode = False  # Track if in flying analysis mode
    flying_keywords = ["fly", "flying", "flight", "optimal", "best day", "pilot"]

    while True:
        user_input = input(Fore.GREEN + "You: " + Style.RESET_ALL).strip()

        # Parse for commands first
        command, args = parse_command(user_input)

        if command == "exit":
            logger.info("User exited the application")
            print(Fore.CYAN + "Goodbye!" + Style.RESET_ALL)
            break
        elif command == "help":
            logger.info("User requested help")
            print(Fore.BLUE + "Weather Bot: " + Style.RESET_ALL + handle_help_command() + "\n")
            continue
        elif command == "about":
            logger.info("User requested about information")
            print(Fore.BLUE + "Weather Bot: " + Style.RESET_ALL + handle_about_command() + "\n")
            continue
        elif command == "weather":
            # Handle weather command with arguments
            if len(args) >= 2:
                location = args[0]
                date = " ".join(args[1:])
                logger.info(f"Weather command with location={location}, date={date}")
                weather_query = f"What's the weather in {location} on {date}?"
                response = handle_conversation(weather_query)
                print(Fore.BLUE + "Weather Bot: " + Style.RESET_ALL + response + "\n")
            else:
                print(Fore.YELLOW + "Weather Bot: Please specify a location and date. For example: 'weather London tomorrow'" + Style.RESET_ALL)
            continue
        elif command == "fly":
            # Handle fly command with arguments
            if len(args) >= 1:
                location = " ".join(args)
                logger.info(f"Fly command with location={location}")
                response = handle_flying_day_request(f"What is the best day to fly in {location}?")
                print(Fore.BLUE + "Weather Bot: " + Style.RESET_ALL + response + "\n")
            else:
                print(Fore.YELLOW + "Weather Bot: Please specify a location for flying conditions. For example: 'fly Berlin'" + Style.RESET_ALL)
                flying_mode = True
            continue

        # If no command recognised, proceed with regular conversation flow
        try:
            # Check if in flying mode waiting for a location
            if flying_mode and not any(keyword in user_input.lower() for keyword in flying_keywords):
                # User is providing just a location after being asked
                logger.info(f"Processing location for flying day: {user_input}")
                try:
                    response = handle_flying_day_request(f"What is the best day to fly in {user_input}?")
                    flying_mode = False  # Reset flying mode after handling
                    print(Fore.BLUE + "Weather Bot: " + Style.RESET_ALL + response + "\n")
                except Exception as e:
                    flying_mode = False  # Reset flying mode on error
                    logger.error(f"Error processing flying location '{user_input}': {str(e)}")
                    print(Fore.RED + f"Weather Bot: I'm sorry, I couldn't process that location. Please try a different city name.")
                continue  # Skip the rest of the loop to avoid double processing

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
                    print(Fore.YELLOW + f"Weather Bot: I need a location to check for optimal flying conditions. Please specify a city or area.")
                    flying_mode = True
                    continue
                else:
                    try:
                        response = handle_flying_day_request(user_input)
                        flying_mode = False  # Ensure app is not in flying mode
                    except Exception as e:
                        flying_mode = False  # Reset flying mode on error
                        logger.error(f"Error processing flying request: {str(e)}")
                        response = Fore.RED + "I'm sorry, I couldn't process your flying request. Is the location you provided a valid city name?"
            else:
                logger.info("Processing general conversation query")
                response = handle_conversation(user_input)
                flying_mode = False  # Ensure app is not in flying mode

            print(Fore.BLUE + "Weather Bot: " + Style.RESET_ALL + response + "\n")
        except Exception as e:
            # Catch-all error handler - always reset flying mode
            flying_mode = False
            logger.error(f"Error in main loop: {str(e)}")
            print(Fore.RED + f"Weather Bot: I'm sorry, I encountered an error: {str(e)}")

if __name__ == "__main__":
    main()
