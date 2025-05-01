# Weather Chatbot with Flight Weather Analyser

A Python-based command-line application that provides weather information and analyses suitable flying conditions.

## ⚠️ Disclaimer

IMPORTANT: This is a proof-of-concept application intended for educational
purposes only. It should not be used for critical decision-making or safety-related
activities. Weather is unpredictable and can change rapidly. Always consult official
weather services and certified meteorological sources for decisions related to flight
planning, outdoor activities, or any situation where weather conditions may impact
safety. The developer and contributors of this application are not liable for any
damages or losses resulting from its use.

## 📋 Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Requirements](#requirements)
- [Installation](#installation)
- [Environment Setup](#environment-setup)
- [Usage](#usage)
- [API Integrations](#api-integrations)
- [Weather Analysis Engine](#weather-analysis-engine)
- [Flying Conditions Analysis](#flying-conditions-analysis)
- [Extended Configuration](#extended-configuration)
- [Caching System](#caching-system)
- [Project Structure](#project-structure)
- [Limitations](#limitations)
- [Troubleshooting](#troubleshooting)
- [Contributing](#contributing)
- [License](#license)
- [Acknowledgments](#acknowledgments)

## 🌦️ Overview

This chatbot application provides weather information for locations
worldwide, including historical data, current conditions, and forecasts for up to 6
days in the future. It also features a rudimentary flight weather analysis system that
can determine an appropriate day for flying activities based on meteorological factors.

## ✨ Features

- **Weather Information**: Retrieve weather data for locations and dates
  - Historical weather data for past dates
  - Current weather conditions
  - Weather forecasts for up to 6 days in the future

- **Flight Weather Analysis**: Analyse and identify suitable flying days
  - Scoring system based on a few weather parameters
  - Breakdown of favorable and challenging conditions
  - Day-by-day comparison of flying conditions

- **Conversational Interface**: Natural language processing for query interpretation
  - Extract location and date information from user queries
  - Defaults for missing information

- **Robust API Handling**: Enhanced reliability and performance
  - Retry mechanism with exponential backoff for API failures
  - Response caching to reduce API calls and improve performance
  - Detailed logging of all operations

## 📋 Requirements

- Python 3.6+
- OpenAI API key
- MeteoblueAPI key
- OpencageAPI key
- VisualCrossing API key
- Internet connection

## 🔧 Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/weather-chatbot.git
   cd weather-chatbot
   ```

2. Install required packages:
   ```bash
   pip install -r requirements.txt
   ```

## 🔑 Environment Setup

Create a `.env` file in the project root directory with the following API keys:

```
OPENAI_API_KEY=your_openai_api_key
METEOBLUE_API_KEY=your_meteoblue_api_key
OPENCAGE_API_KEY=your_opencage_api_key
VISUALCROSSING_API_KEY=your_visualcrossing_api_key
DEFAULT_LOCATION=Berlin
CACHE_ENABLED=True
CACHE_DIRECTORY=cache
MAX_RETRIES=3
```

## 🚀 Usage

Run the application:

```bash
python weather_chatbot.py
```

### Example Commands

- General query:
  ```
  What should I eat for lunch today?
  ```

- General weather query:
  ```
  What's the weather like in Berlin tomorrow?
  ```

- Historical weather query:
  ```
  How was the weather in Paris last Monday?
  ```

- Optimal flying day query:
  ```
  What's the best day to fly in Munich this week?
  ```

## 🔌 API Integrations

The application integrates with the following external APIs:

- **OpenAI**: Used for natural language understanding and query interpretation
- **Meteoblue**: Provides detailed weather forecast data for future dates
- **Opencage**: Converts location names to geographic coordinates
- **VisualCrossing**: Provides historical weather data

## ⚙️ Weather Analysis Engine

The weather analysis engine processes meteorological data from sources to provide information including:

- Temperature (°C)
- Wind speed (km/h, knots) and direction
- Precipitation and snowfall (mm)
- Relative humidity (%)
- Barometric pressure (hPa)
- Cloud cover (%)
- Special conditions (fog, mist)

## ✈️ Flying Conditions Analysis

The application uses a scoring system to evaluate flying conditions:

### Scoring Factors

- **Temperature**: Ideal range is 10-25°C
- **Wind**: Optimal is below 15 km/h
- **Precipitation**: Ideally none
- **Snow**: Any snow is detrimental for flying
- **Cloud Cover**: Clearer skies are better
- **Humidity**: Lower is better for visibility
- **Pressure**: Stable high pressure is optimal

Each factor contributes to a base score of 100, with bonuses for favorable conditions and penalties for challenging ones.

## 🔧 Extended Configuration

The application can be configured using environment variables or by modifying the Config class:

```python
# Default configuration values
DEFAULT_LOCATION = "Berlin"  # Default location when none specified
CACHE_ENABLED = True         # Enable/disable API response caching
CACHE_DIRECTORY = "cache"    # Directory to store cached responses
MAX_RETRIES = 3              # Maximum number of retry attempts for API requests
BASE_RETRY_DELAY = 1.0       # Base delay in seconds for retry backoff
MAX_RETRY_DELAY = 10.0       # Maximum delay in seconds for retry backoff
```

You can override these values in your `.env` file or by passing parameters to the WeatherService constructor.

## 💾 Caching System

The application implements a robust caching system to reduce API calls, improve performance, and handle rate limiting gracefully.

### Cache Configuration

The caching system can be configured through the following parameters:

```python
cache_config = {
    'enabled': True,                    # Enable or disable caching
    'directory': 'cache',               # Directory to store cache files
    'ttl': {                            # Time-to-live in seconds for different cache types
        'coordinates': 60 * 60 * 24 * 30,  # 30 days for location coordinates
        'weather': 60 * 60,                # 1 hour for weather forecasts
        'historical': 60 * 60 * 24 * 365   # 1 year for historical weather
    },
    'max_retries': 3,                   # Maximum number of retry attempts
    'base_retry_delay': 1.0,            # Base delay for exponential backoff
    'max_retry_delay': 10.0             # Maximum delay for any retry attempt
}
```

### Cache Behavior

- **Cache Key Generation**: Unique keys are generated based on the API endpoint URL, parameters, and API type.
- **Cache Invalidation**: Cached responses expire based on the TTL settings above.
- **Cache Storage**: Responses are stored as JSON files in the specified cache directory.

### Managing the Cache

- To clear the cache, delete the files in the cache directory: `rm -rf cache/*`
- To disable caching temporarily, set `CACHE_ENABLED=False` in your `.env` file
- To adjust cache duration, modify the TTL values in the Config class

## 🗂️ Project Structure

- `weather_chatbot.py`: Main script containing the chatbot logic
- `weather_service.py`: Service class for weather-related functionality
- `config.py`: Configuration management and singleton pattern implementation
- `utils.py`: Utility functions for API requests, date parsing, and caching
- `.env`: File containing environment variables (API keys)
- `requirements.txt`: List of required Python packages
- `.gitignore`: Specifies files to exclude from version control

## ⚡ Limitations

- The chatbot can only provide weather forecasts for up to 6 days in the future due to API limitations.
- Historical weather data availability may vary depending on the location and date requested, with some remote locations having limited or no data.
- Weather prediction accuracy decreases the further into the future the forecast is made, with days 5-6 being significantly less reliable.
- The flying conditions analysis is based on general aviation principles but is NOT suitable for real flight activities or flight planning.
- API rate limits may affect the application's performance:
  - OpenAI: Typically limited to 3-20 requests per minute depending on your plan
  - Meteoblue: Limited to 500-2500 calls per day depending on your subscription
  - OpenCage: Typically 2500 requests per day on the free plan
  - VisualCrossing: Usually 1000 records per day on the free plan
- The caching system helps mitigate rate limits but cannot completely prevent them during heavy usage.

## 🔍 Troubleshooting

If you encounter any issues:

1. Ensure all API keys in the `.env` file are correctly set and valid.
2. Check your internet connection.
3. Verify that all required packages are installed correctly.
4. Make sure the `.env` file is in the same directory as the `weather_chatbot.py` script.

### Advanced Troubleshooting

#### API-Related Issues

- **Rate Limiting Errors**: If you see "I'm currently experiencing high demand" messages, you may have exceeded API rate limits:
  - Wait a few minutes before trying again
  - Check your API usage dashboard for the relevant service
  - Consider upgrading your API plan if you regularly hit limits

- **Authentication Errors**: If you see "I'm having trouble with my authentication system":
  - Verify your API keys in the `.env` file
  - Ensure the keys have not expired
  - Check if your subscription is active

- **Connection Issues**: If you see "I'm having trouble connecting to my knowledge system":
  - Check your internet connection
  - Verify that the API services are operational
  - Try again after a few minutes

#### Caching Issues

- **Cache Not Working**: If API calls are not being cached:
  - Verify that `CACHE_ENABLED=True` in your `.env` file
  - Ensure the cache directory exists and is writable
  - Check the application logs for cache-related errors

- **Outdated Cache Results**: If you're getting outdated information:
  - Clear the cache directory manually
  - Adjust the TTL settings in the configuration
  - Disable caching temporarily with `CACHE_ENABLED=False`

#### Location and Date Issues

- **Location Not Found**: If the chatbot cannot find your location:
  - Try using a more well-known location or a larger nearby city
  - Ensure the location name is spelled correctly
  - Check if OpenCage supports geocoding for that region

- **Date Parsing Errors**: If you see date-related error messages:
  - Use standard date formats (YYYY-MM-DD)
  - Try relative dates like "tomorrow" or "next Monday"
  - Avoid ambiguous date references

## 👨‍💻 Contributing

A warm welcome to contributors. Please feel free to submit a Pull Request.

## 📝 License

This project is licensed under the MIT License.

## 🙏 Acknowledgments

- Warm thanks to Sasha and Fabian for providing the original task and Fabio for the inspirations and guidance.
- OpenAI for providing the GPT model
- Meteoblue for weather forecast data
- OpenCage for geocoding services
- Visual Crossing for historical weather data

---

For any questions or support, please open an issue in the GitHub repository. Thank you.
