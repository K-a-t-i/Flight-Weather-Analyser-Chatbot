import colorama
from colorama import Fore, Back, Style

class DisplayManager:
    """
    Base class for display managers that format output for the terminal.

    This class demonstrates object-oriented programming by providing a
    base class with common functionality that can be inherited by
    specialised display manager classes.
    """

    def __init__(self):
        """Initialise the display manager."""
        # Ensure colorama is initialised
        colorama.init(autoreset=True)

    def format_title(self, title):
        """Format a title with consistent styling."""
        return Fore.CYAN + Style.BRIGHT + f"=== {title} ===" + Style.RESET_ALL + "\n\n"

    def format_section_header(self, header):
        """Format a section header with consistent styling."""
        return Fore.YELLOW + Style.BRIGHT + f"{header}" + Style.RESET_ALL + "\n"

    def format_key_value(self, key, value, color=Fore.WHITE):
        """Format a key-value pair with consistent styling."""
        return Fore.GREEN + f"{key}: " + color + f"{value}\n"

    def format_warning(self, message):
        """Format a warning message with consistent styling."""
        return Fore.RED + Style.BRIGHT + f"Warning: {message}" + Style.RESET_ALL + "\n"

    def format_success(self, message):
        """Format a success message with consistent styling."""
        return Fore.GREEN + f"{message}" + Style.RESET_ALL + "\n"

    def format_error(self, message):
        """Format an error message with consistent styling."""
        return Fore.RED + f"Error: {message}" + Style.RESET_ALL + "\n"

    def display_loading_animation(self, message="Processing"):
        """
        Display an animated loading indicator with a message.

        Args:
            message (str): The message to display before the animation
        """
        import sys
        import time

        indicators = ['|', '/', '-', '\\']
        formatted_message = self.format_loading_indicator(message)
        sys.stdout.write(formatted_message)

        for i in range(5):  # Short animation to avoid long waits
            sys.stdout.write(indicators[i % len(indicators)] + "\r" + message + " ")
            sys.stdout.flush()
            time.sleep(0.2)

        sys.stdout.write("\r" + " " * (len(message) + 2) + "\r")
        sys.stdout.flush()

    def format_welcome_message(self, app_name, version, authors, default_location):
        """
        Format a welcome message for the application.

        Args:
            app_name (str): Name of the application
            version (str): Version of the application
            authors (str): Authors of the application
            default_location (str): Default location for weather queries

        Returns:
            str: Formatted welcome message
        """
        welcome_text = Fore.CYAN + Style.BRIGHT + "=" * 80 + "\n"
        welcome_text += Fore.YELLOW + Style.BRIGHT + f"""
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
                                           
    """ + "\n"
        welcome_text += Fore.CYAN + Style.BRIGHT + "=" * 80 + "\n"
        welcome_text += Fore.WHITE + f"Welcome to our {app_name} v{version}\n"
        welcome_text += Fore.WHITE + f"initialised by {authors}\n"
        welcome_text += Fore.CYAN + Style.BRIGHT + "=" * 80 + "\n\n"

        # Show disclaimer
        welcome_text += Fore.RED + Style.BRIGHT + "DISCLAIMER:" + Style.RESET_ALL + "\n"
        welcome_text += Fore.YELLOW + "This is a proof-of-concept application intended for educational purposes only.\n"
        welcome_text += "It should NOT be used for critical decision-making or safety-related activities.\n"
        welcome_text += "Always consult official weather services for important decisions." + Style.RESET_ALL + "\n"
        welcome_text += Fore.CYAN + "=" * 80 + "\n\n"

        # Show usage information
        welcome_text += Fore.GREEN + Style.BRIGHT + f"Default location set to: {default_location}" + Style.RESET_ALL + "\n"
        welcome_text += Fore.WHITE + "You can ask about the weather for any location in the world, for past dates, today, and up to 6 days in the future.\n"
        welcome_text += Fore.WHITE + "You can also ask for the appropriate day for flying in any location!\n"

        # Show example queries
        welcome_text += Fore.GREEN + Style.BRIGHT + "\nExample queries:" + Style.RESET_ALL + "\n"
        welcome_text += Fore.WHITE + "- What's the weather like in Berlin tomorrow?\n"
        welcome_text += Fore.WHITE + "- How was the weather in Paris last Monday?\n"
        welcome_text += Fore.WHITE + "- What's the best day to fly in Munich this week?\n"
        welcome_text += Fore.WHITE + "- Type 'help' to see all available commands\n"
        welcome_text += Fore.WHITE + "- Type 'exit' to quit the chatbot.\n"

        return welcome_text

    def format_help_message(self, default_location):
        """
        Format help information about available commands and options.

        Args:
            default_location (str): Default location for weather queries

        Returns:
            str: Formatted help message
        """
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
        help_text += Fore.WHITE + "- Default location is set to: " + Fore.CYAN + f"{default_location}\n"
        help_text += Fore.WHITE + "- Weather forecasts are available for up to 6 days in the future\n"
        help_text += Fore.WHITE + "- Historical weather data is available for past dates\n"
        help_text += Fore.WHITE + "- Flying conditions analysis considers wind, precipitation, cloud cover and more\n"

        return help_text

    def format_about_message(self):
        """
        Format information about the chatbot.

        Returns:
            str: Formatted about message
        """
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

    def format_loading_indicator(self, message="Processing"):
        """Return a loading message for display while waiting."""
        return Fore.CYAN + message + "..."


class WeatherDisplayManager(DisplayManager):
    """
    Specialised display manager for weather-related information.

    This class demonstrates inheritance in object-oriented programming
    by extending the base DisplayManager class with weather-specific
    formatting functionality.
    """

    # ASCII art for weather conditions
    WEATHER_ASCII = {
        "sunny": [
            "    \\   /    ",
            "     .-.     ",
            "  ― (   ) ―  ",
            "     `-'     ",
            "    /   \\    "
        ],
        "cloudy": [
            "             ",
            "     .--.    ",
            "  .-(    ).  ",
            " (___.__)__) ",
            "             "
        ],
        "rainy": [
            "     .-.     ",
            "    (   ).   ",
            "   (___(__)  ",
            "  ʻ‚ʻ‚ʻ‚ʻ‚   ",
            "  ‚ʻ‚ʻ‚ʻ‚    "
        ],
        "snowy": [
            "     .-.     ",
            "    (   ).   ",
            "   (___(__)  ",
            "   * * * *   ",
            "  * * * *    "
        ],
        "windy": [
            "    _,,,_    ",
            "   /     \\   ",
            "  (  ~~~~ )  ",
            "   \\     /   ",
            "    ~~~~~    "
        ],
        "stormy": [
            "     .-.     ",
            "    (   ).   ",
            "   (___(__)  ",
            "  ⚡⚡⚡⚡    ",
            "  ⚡⚡⚡     "
        ],
        "foggy": [
            "             ",
            " --- --- --- ",
            " --- --- --- ",
            " --- --- --- ",
            "             "
        ],
        "default": [
            "             ",
            "     ?       ",
            "    ???      ",
            "     ?       ",
            "             "
        ]
    }

    def get_weather_ascii(self, condition):
        """
        Get ASCII art representing weather conditions.

        Args:
            condition (str): Weather condition description

        Returns:
            list: ASCII art lines for the condition
        """
        condition = condition.lower() if condition else ""

        if "sun" in condition or "clear" in condition:
            return self.WEATHER_ASCII["sunny"]
        elif "cloud" in condition:
            return self.WEATHER_ASCII["cloudy"]
        elif "rain" in condition or "shower" in condition:
            return self.WEATHER_ASCII["rainy"]
        elif "snow" in condition:
            return self.WEATHER_ASCII["snowy"]
        elif "wind" in condition:
            return self.WEATHER_ASCII["windy"]
        elif "storm" in condition or "thunder" in condition:
            return self.WEATHER_ASCII["stormy"]
        elif "fog" in condition or "mist" in condition:
            return self.WEATHER_ASCII["foggy"]
        else:
            # Default to cloudy if condition not recognised
            return self.WEATHER_ASCII["cloudy"]

    def format_weather_ascii(self, condition, color=Fore.YELLOW):
        """
        Format ASCII art for a weather condition.

        Args:
            condition (str): Weather condition description
            color (colorama.Fore): Colour to use for the ASCII art

        Returns:
            str: Formatted ASCII art string
        """
        art = self.get_weather_ascii(condition)
        result = color + "\nWeather condition:\n"
        for line in art:
            result += color + line + "\n"
        return result

    def format_temperature(self, temp):
        """
        Format a temperature value with appropriate colouring.

        Args:
            temp (float): Temperature in Celsius

        Returns:
            str: Formatted and coloured temperature string
        """
        if temp < 5:
            return Fore.BLUE + f"{temp:.1f}°C"
        elif temp > 30:
            return Fore.RED + f"{temp:.1f}°C"
        else:
            return Fore.WHITE + f"{temp:.1f}°C"

    def format_weather_info(self, location, date, weather_data, is_historical=False):
        """
        Format complete weather information.

        Args:
            location (str): Location name
            date (datetime.date): Weather date
            weather_data (dict): Weather data
            is_historical (bool): Whether this is historical data

        Returns:
            str: Formatted weather information
        """
        verb = "was" if is_historical else "is expected to be"

        # Format date with weekday
        formatted_date = f"{date.strftime('%A, %Y-%m-%d')}"

        # Extract weather data
        temp = weather_data.get("temp", 15.0)
        condition = weather_data.get("condition", "")
        wind_speed = weather_data.get("wind_speed", 0.0)
        wind_direction = weather_data.get("wind_direction", 0.0)
        precip = weather_data.get("precipitation", 0.0)
        cloud_cover = weather_data.get("cloud_cover", 0.0)
        humidity = weather_data.get("humidity", 50.0)
        pressure = weather_data.get("pressure", 1013.0)

        # Create the formatted output
        output = self.format_title(f"Weather for {location}")

        # Summary line
        output += f"On {formatted_date}, the weather {verb} {condition}.\n"
        output += f"The average temperature {verb} {self.format_temperature(temp)}, "
        output += f"with {Fore.CYAN}{precip:.1f}mm{Style.RESET_ALL} of precipitation and average wind speeds "
        output += f"of {Fore.CYAN}{wind_speed:.2f}km/h{Style.RESET_ALL}.\n\n"

        # Detailed information
        output += self.format_section_header("Detailed Weather Information")
        output += self.format_key_value("Average Temperature", f"{temp:.2f}°C",
                                        self.format_temperature(temp))
        output += self.format_key_value("Average Wind Speed", f"{wind_speed:.2f} km/h")
        output += self.format_key_value("Wind Direction", f"{wind_direction:.0f}°")
        output += self.format_key_value("Total Precipitation", f"{precip:.1f} mm")
        output += self.format_key_value("Average Relative Humidity", f"{humidity:.0f}%")
        output += self.format_key_value("Average Cloud Cover", f"{cloud_cover:.0f}%")
        output += self.format_key_value("Average Barometric Pressure", f"{pressure:.0f} hPa")

        # Add ASCII art for the weather condition
        output += self.format_weather_ascii(condition)

        return output

    def format_error_message(self, message):
        """Format an error message with consistent styling."""
        return Fore.RED + f"{message}" + Style.RESET_ALL

    def format_optimal_flying_day_response(self, flying_data):
        """
        Format the optimal flying day data into a readable response.

        Args:
            flying_data (dict or str): Flying data or error message

        Returns:
            str: Formatted flying day response
        """
        # Check if there is an error message instead of data
        if isinstance(flying_data, str):
            return self.format_error_message(flying_data)

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

        response += self.format_weather_ascii(weather_condition)

        return response
