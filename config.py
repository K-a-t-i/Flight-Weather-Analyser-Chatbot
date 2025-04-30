import os
import logging
from dotenv import load_dotenv

# Configure logger
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ConfigurationError(Exception):
    """Exception raised for configuration errors."""
    pass

class Config:
    """
    Singleton class for application configuration management.

    This class provides centralised access to application configuration settings
    loaded from environment variables and default values.
    """
    _instance = None

    def __new__(cls):
        """Implement singleton pattern."""
        if cls._instance is None:
            cls._instance = super(Config, cls).__new__(cls)
            cls._instance._initialised = False
        return cls._instance

    def __init__(self):
        """Initialise configuration if not already initialised."""
        if self._initialised:
            return

        # Load environment variables from .env file
        load_dotenv()

        # Initialise configurations
        self._config_values = {}
        self._cache_config = {}
        self._api_keys = {}

        # Set initialised flag
        self._initialised = True

        # Load default configurations
        self._load_defaults()

    def _load_defaults(self):
        """Load default configuration values."""
        # API Keys with validation
        self._api_keys = {
            "openai": self.get("OPENAI_API_KEY", required=True),
            "meteoblue": self.get("METEOBLUE_API_KEY", required=True),
            "opencage": self.get("OPENCAGE_API_KEY", required=True),
            "visualcrossing": self.get("VISUALCROSSING_API_KEY", required=True)
        }

        # Cache settings - simple version
        cache_enabled = os.getenv("CACHE_ENABLED", "True").lower() == "true"
        cache_directory = os.getenv("CACHE_DIRECTORY", "cache")

        # Add default location
        self._config_values["DEFAULT_LOCATION"] = os.getenv("DEFAULT_LOCATION", "Markt Nordheim")

        # Basic cache configuration
        self._cache_config = {
            'enabled': cache_enabled,
            'directory': cache_directory,
            'ttl': {
                "coordinates": 60 * 60 * 24 * 30,  # 30 days for coordinates
                "weather": 60 * 60,                # 1 hour for weather data
                "historical": 60 * 60 * 24 * 365   # 1 year for historical data
            },
            'max_retries': int(os.getenv("MAX_RETRIES", "3")),
            'base_retry_delay': float(os.getenv("BASE_RETRY_DELAY", "1.0")),
            'max_retry_delay': float(os.getenv("MAX_RETRY_DELAY", "10.0"))
        }

        # Create cache directory if it doesn't exist and caching is enabled
        if cache_enabled and not os.path.exists(cache_directory):
            try:
                os.makedirs(cache_directory)
                logger.info(f"Created cache directory: {cache_directory}")
            except Exception as e:
                logger.warning(f"Failed to create cache directory: {str(e)}")

    def get(self, key, default=None, required=False):
        """
        Get a configuration value.

        Args:
            key: The configuration key to retrieve
            default: Default value if not found
            required: Whether the configuration is required

        Returns:
            The configuration value

        Raises:
            ConfigurationError: If a required configuration is missing
        """
        # Check if we already have this value cached
        if key in self._config_values:
            return self._config_values[key]

        # Get value from environment
        value = os.getenv(key, default)

        # Check if required value is missing
        if value is None and required:
            error_message = f"Required configuration '{key}' is missing"
            logger.error(error_message)
            raise ConfigurationError(error_message)

        # Cache the value for future lookups
        self._config_values[key] = value
        return value

    def set(self, key, value):
        """
        Set a configuration value at runtime.

        Args:
            key: The configuration key to set
            value: The value to set
        """
        self._config_values[key] = value
        logger.debug(f"Configuration '{key}' set at runtime")

    @property
    def api_keys(self):
        """Get API keys configuration dictionary."""
        return self._api_keys

    @property
    def cache_config(self):
        """Get cache configuration dictionary."""
        return self._cache_config

    def reload(self):
        """Reload configuration from environment and defaults."""
        self._config_values = {}
        self._cache_config = {}
        self._api_keys = {}
        load_dotenv(override=True)
        self._load_defaults()
        logger.info("Configuration reloaded")
