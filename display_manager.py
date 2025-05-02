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

    def format_loading_indicator(self, message="Processing"):
        """Return a loading message for display while waiting."""
        return Fore.CYAN + message + "..."
