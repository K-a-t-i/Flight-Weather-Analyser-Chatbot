import json
from colorama import Fore, Style
import logging
import asyncio

logger = logging.getLogger(__name__)

class CommandHandler:
    """
    Base class for command handlers, using the Command Pattern.

    The Command Pattern encapsulates a request as an object, thereby allowing
    for parameterisation of clients with queues, requests, and operations.
    It also allows for the support of undoable operations.
    """

    def __init__(self, weather_service, display_manager, config):
        """
        Initialise the command handler.

        Args:
            weather_service: WeatherService instance for accessing weather data
            display_manager: DisplayManager instance for formatting output
            config: Config instance for accessing application configuration
        """
        self.weather_service = weather_service
        self.display_manager = display_manager
        self.config = config

    def can_handle(self, command, args):
        """
        Check if this handler can process the given command.

        Args:
            command (str): The command to check
            args (list): Command arguments

        Returns:
            bool: True if this handler can handle the command, False otherwise
        """
        return False

    def handle(self, command, args):
        """
        Process the command and return a response.

        Args:
            command (str): The command to process
            args (list): Command arguments

        Returns:
            str: Formatted response to the command
        """
        raise NotImplementedError("Subclasses must implement handle()")


class ExitCommandHandler(CommandHandler):
    """Handler for exit/quit commands."""

    def can_handle(self, command, args):
        """Check if this is an exit command."""
        return command in ["exit", "quit", "bye", "q"]

    def handle(self, command, args):
        """Handle the exit command."""
        logger.info("User exited the application")
        return Fore.CYAN + "Goodbye!" + Style.RESET_ALL


class HelpCommandHandler(CommandHandler):
    """Handler for help command."""

    def can_handle(self, command, args):
        """Check if this is a help command."""
        return command == "help"

    def handle(self, command, args):
        """Display help information."""
        logger.info("User requested help")
        return self.display_manager.format_help_message(self.config.default_location)


class AboutCommandHandler(CommandHandler):
    """Handler for about command."""

    def can_handle(self, command, args):
        """Check if this is an about command."""
        return command == "about"

    def handle(self, command, args):
        """Display information about the chatbot."""
        logger.info("User requested about information")
        return self.display_manager.format_about_message()


class WeatherCommandHandler(CommandHandler):
    """Handler for weather command."""

    def can_handle(self, command, args):
        """Check if this is a weather command with sufficient arguments."""
        return command in ["weather", "w", "forecast"]

    def handle(self, command, args):
        """Process the weather command."""
        if len(args) >= 2:
            location = args[0]
            date = " ".join(args[1:])
            logger.info(f"Weather command with location={location}, date={date}")

            try:
                # Use the WeatherService to get weather data
                self.display_manager.display_loading_animation("Getting weather data")
                # Use get_weather
                weather_response = self.weather_service.get_weather(location, date)
                return weather_response
            except ValueError as e:
                logger.error(f"Date parsing error: {str(e)}")
                return self.display_manager.format_error_message(
                    f"I couldn't understand this date format. {str(e)}"
                )
            except Exception as e:
                logger.error(f"Error processing weather request: {str(e)}")
                return self.display_manager.format_error_message(
                    f"Error getting weather information: {str(e)}"
                )
        else:
            return Fore.YELLOW + "Please specify a location and date. For example: 'weather London tomorrow'" + Style.RESET_ALL


class FlyCommandHandler(CommandHandler):
    """Handler for fly command."""

    def can_handle(self, command, args):
        """Check if this is a fly command."""
        return command in ["fly", "flying", "flight", "f"]

    def handle(self, command, args):
        """Process the fly command."""
        if len(args) >= 1:
            location = " ".join(args)
            logger.info(f"Fly command with location={location}")

            try:
                # Use the WeatherService to get optimal flying day
                self.display_manager.display_loading_animation("Analysing flying conditions in parallel")

                # Try the async version with asyncio.run
                try:
                    # Check if asyncio is available and properly configured
                    logger.info("Attempting to use asynchronous API for flying conditions analysis")
                    flying_data = asyncio.run(self.weather_service.get_optimal_flying_day_async(location))
                    logger.info("Successfully used asynchronous API for flying conditions")
                except (ImportError, AttributeError, RuntimeError) as e:
                    # Handle case where asyncio is not available or properly configured
                    logger.warning(f"Async API failed, falling back to synchronous mode: {str(e)}")
                    self.display_manager.display_loading_animation("Async API unavailable, using standard analysis")
                    flying_data = self.weather_service.get_optimal_flying_day(location)
                    logger.info("Successfully used synchronous API as fallback")

                # Format the flying data using the display manager
                return self.display_manager.format_optimal_flying_day_response(flying_data)
            except Exception as e:
                logger.error(f"Error processing flying request: {str(e)}")
                return self.display_manager.format_error_message(
                    f"Error finding optimal flying day: {str(e)}"
                )
        else:
            return Fore.YELLOW + "Please specify a location for flying conditions. For example: 'fly Berlin'" + Style.RESET_ALL


class ConversationHandler(CommandHandler):
    """Handler for general conversation queries."""

    def __init__(self, weather_service, display_manager, config, openai_client):
        """
        Initialise the conversation handler.

        Args:
            weather_service: WeatherService instance
            display_manager: DisplayManager instance
            config: Config instance
            openai_client: OpenAI client
        """
        super().__init__(weather_service, display_manager, config)
        self.openai_client = openai_client

    def can_handle(self, command, args):
        """This handler processes general conversation that isn't a specific command."""
        return True  # Fallback handler for all other queries

    def handle(self, command, args):
        """Process the conversation query."""
        # Reconstruct the full query from command and args
        query = command
        if args:
            query = command + " " + " ".join(args)

        self.display_manager.display_loading_animation("Processing your question")

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
            response = self.openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": f"You are a helpful assistant that can engage in general conversation and "
                                                  f"provide weather information when asked. You can provide historical weather "
                                                  f"data for past dates, current weather, and forecasts for up to 6 days in the "
                                                  f"future. If the user doesn't specify a location or date for weather, assume "
                                                  f"they're asking about {self.config.default_location} for today."},
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
                    location = function_args.get("location", self.config.default_location)
                    date_string = function_args.get("date", "today")

                    try:
                        # Use get_weather
                        weather_response = self.weather_service.get_weather(location, date_string)
                        return weather_response
                    except ValueError as e:
                        logger.error(f"Date parsing error: {str(e)}")
                        return self.display_manager.format_error_message(
                            f"I couldn't understand this date format. {str(e)}"
                        )
                else:
                    logger.warning(f"Unknown function call: {function_name}")
                    return self.display_manager.format_error_message("I don't know how to handle that request.")
            else:
                # If no function was called, it means the query wasn't about weather
                logger.info("No function call - regular conversation")
                return message.content

        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error in OpenAI response: {str(e)}")
            return self.display_manager.format_error_message("I encountered an error understanding your question. Could you please rephrase it?")
        except Exception as e:
            # Log error type and message for debugging
            error_type = type(e).__name__
            error_message = str(e)
            logger.error(f"Error handling conversation: {error_type} - {error_message}")

            # Provide responses based on error type
            if "RateLimitError" in error_type:
                return self.display_manager.format_error_message("I'm currently experiencing high demand. Please try again in a moment.")
            elif "AuthenticationError" in error_type:
                return self.display_manager.format_error_message("I'm having trouble with my authentication system. Please report this issue to the administrator.")
            elif "APIConnectionError" in error_type or "APITimeoutError" in error_type:
                return self.display_manager.format_error_message("I'm having trouble connecting to my knowledge system. Please check your internet connection and try again.")
            else:
                # Generic message for other errors
                return self.display_manager.format_error_message("I encountered an unexpected error while processing your request. Please try again.")


class CommandProcessor:
    """
    Main processor for commands using the Command Pattern.

    This class maintains a chain of command handlers and delegates
    user input to the appropriate handler.
    """

    def __init__(self, weather_service, display_manager, config, openai_client):
        """
        Initialise the command processor with required services.

        Args:
            weather_service: WeatherService instance
            display_manager: DisplayManager instance
            config: Config instance
            openai_client: OpenAI client
        """
        self.handlers = []
        self._register_handlers(weather_service, display_manager, config, openai_client)

    def _register_handlers(self, weather_service, display_manager, config, openai_client):
        """
        Register all command handlers in order of precedence.

        Args:
            weather_service: WeatherService instance
            display_manager: DisplayManager instance
            config: Config instance
            openai_client: OpenAI client
        """
        # Order - more specific handlers first
        self.handlers.append(ExitCommandHandler(weather_service, display_manager, config))
        self.handlers.append(HelpCommandHandler(weather_service, display_manager, config))
        self.handlers.append(AboutCommandHandler(weather_service, display_manager, config))
        self.handlers.append(WeatherCommandHandler(weather_service, display_manager, config))
        self.handlers.append(FlyCommandHandler(weather_service, display_manager, config))
        # Conversation handler is the fallback
        self.handlers.append(ConversationHandler(weather_service, display_manager, config, openai_client))

    def parse_input(self, user_input):
        """
        Parse user input to determine command and arguments.

        Args:
            user_input (str): The user's input string

        Returns:
            tuple: (command, args) where command is the identified command and args are additional arguments
        """
        input_lower = user_input.lower().strip()

        # Check for exact command matches
        if input_lower in ["exit", "quit", "bye", "q"]:
            return "exit", []
        elif input_lower == "help":
            return "help", []
        elif input_lower == "about":
            return "about", []

        # Check for command prefixes
        words = input_lower.split()
        if len(words) >= 1:
            # Weather command and shortcuts
            if words[0] in ["weather", "w", "forecast"]:
                return words[0], words[1:]
            # Fly command and shortcuts
            elif words[0] in ["fly", "flying", "flight", "f"]:
                return words[0], words[1:]

        # Not a recognised command format, treat as general input
        return user_input, []

    def process_input(self, user_input):
        """
        Process user input and return an appropriate response.

        Args:
            user_input (str): The user's input

        Returns:
            str: Formatted response to the user's input
        """
        command, args = self.parse_input(user_input)

        # Find the first handler that can process this command
        for handler in self.handlers:
            if handler.can_handle(command, args):
                return handler.handle(command, args)

        # This should never happen since there is a fallback handler
        return "I'm not sure how to handle that request."
