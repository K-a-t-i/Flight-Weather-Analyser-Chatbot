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

## 🗂️ Project Structure

- `weather_chatbot.py`: Main script containing the chatbot logic
- `.env`: File containing environment variables (API keys)
- `requirements.txt`: List of required Python packages

## ⚡ Limitations

- The chatbot can only provide weather forecasts for up to 6 days in the future.
- Historical weather data availability may vary depending on the location and date requested.
- Weather prediction accuracy decreases the further into the future the forecast is made.
- The analysis of flight conditions is based on the principles of general aviation but is NOT suitable for real flight activities.
- API rate limits may affect the application's performance during heavy usage.

## 🔍 Troubleshooting

If you encounter any issues:

1. Ensure all API keys in the `.env` file are correctly set and valid.
2. Check your internet connection.
3. Verify that all required packages are installed correctly.
4. Make sure the `.env` file is in the same directory as the `weather_chatbot.py` script.

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
