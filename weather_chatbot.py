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
    display_manager.display_loading_animation(message)

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
            return display_manager.format_optimal_flying_day_response(flying_data)
        else:
            logger.warning("No function call in OpenAI response")
            return display_manager.format_error_message("I need a location to check for optimal flying conditions. Please specify a city or area.")
    except json.JSONDecodeError as e:
        logger.error(f"JSON decode error in OpenAI response: {str(e)}")
        return display_manager.format_error_message("I encountered an error processing the location information. Please try again with a clearer location.")
    except Exception as e:
        # Log the specific error for debugging
        error_type = type(e).__name__
        error_message = str(e)
        logger.error(f"Error in handling flying day request: {error_type} - {error_message}")

        # Provide error message based on error type
        if "RateLimitError" in error_type:
            return display_manager.format_error_message("I'm currently experiencing high demand. Please try again in a moment.")
        elif "AuthenticationError" in error_type:
            return display_manager.format_error_message("I'm having trouble with my authentication system. Please report this issue to the administrator.")
        elif "APIConnectionError" in error_type or "APITimeoutError" in error_type:
            return display_manager.format_error_message("I'm having trouble connecting to my knowledge system. Please check your internet connection and try again.")
        else:
            # Generic message for other errors
            return display_manager.format_error_message("I encountered an unexpected error while processing your request. Please try again.")

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
    return display_manager.format_help_message(config.default_location)

def handle_about_command():
    """Display information about the chatbot."""
    return display_manager.format_about_message()

def display_welcome_message():
    """Display a styled welcome message."""
    welcome_message = display_manager.format_welcome_message(
        "Weather Chatbot with flight weather analyser",
        "1.0",
        "Sasha & Fabian, with support from Fabio & Sam",
        config.default_location
    )
    print(welcome_message)

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

if __name__ == "__main__":
    main()
