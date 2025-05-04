import os
import time
import sys
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

# Import the command processor and handlers
from command_handler import CommandProcessor

# Initialise colorama
colorama.init(autoreset=True)

# Load environment variables
load_dotenv()

# Initialise configuration
config = Config()

# Initialise display manager
display_manager = WeatherDisplayManager()

try:
    # Initialise OpenAI API
    client = OpenAI(api_key=config.api_keys["openai"])
    logger.info("Successfully initialised OpenAI client")

    # Initialise the WeatherService with the config
    weather_service = WeatherService(config=config)
    logger.info("Successfully initialised WeatherService with Config")

    # Initialise the CommandProcessor
    command_processor = CommandProcessor(weather_service, display_manager, config, client)
    logger.info("Successfully initialised CommandProcessor")

    # Create cache directory if it doesn't exist and caching is enabled
    if config.cache_config['enabled'] and not os.path.exists(config.cache_config['directory']):
        os.makedirs(config.cache_config['directory'])
        logger.info(f"Created cache directory: {config.cache_config['directory']}")
except Exception as e:
    logger.error(f"Failed to initialise services: {str(e)}")
    raise

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

    while True:
        # Get user input
        user_input = input(Fore.GREEN + "You: " + Style.RESET_ALL).strip()

        if not user_input:
            continue

        # Process the input using the command processor
        response = command_processor.process_input(user_input)

        # Check if the user wants to exit
        if user_input.lower() in ["exit", "quit", "bye", "q"]:
            print(response)
            break

        # Display the response
        print(Fore.BLUE + "Weather Bot: " + Style.RESET_ALL + response + "\n")

if __name__ == "__main__":
    main()
