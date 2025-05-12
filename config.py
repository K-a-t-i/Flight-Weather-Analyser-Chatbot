import os
import json
import logging
from typing import Any, Dict, Optional, Union, Type, cast
from functools import lru_cache
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

    # Type definitions for configuration value types
    _type_mapping = {
        'str': str,
        'int': int,
        'float': float,
        'bool': bool,
        'dict': dict,
        'list': list
    }

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

        # Cache settings
        cache_enabled = self.get("CACHE_ENABLED", "True", value_type="bool")
        cache_directory = self.get("CACHE_DIRECTORY", "cache")

        # Retry settings
        max_retries = self.get("MAX_RETRIES", "3", value_type="int")
        base_retry_delay = self.get("BASE_RETRY_DELAY", "1.0", value_type="float")
        max_retry_delay = self.get("MAX_RETRY_DELAY", "10.0", value_type="float")

        # Add default location
        self._config_values["DEFAULT_LOCATION"] = self.get("DEFAULT_LOCATION", "Berlin")

        # Cache TTL settings
        self._cache_config = {
            'enabled': cache_enabled,
            'directory': cache_directory,
            'ttl': {
                "coordinates": self.get("CACHE_TTL_COORDINATES", str(60 * 60 * 24 * 30), value_type="int"),  # 30 days
                "weather": self.get("CACHE_TTL_WEATHER", str(60 * 60), value_type="int"),  # 1 hour
                "historical": self.get("CACHE_TTL_HISTORICAL", str(60 * 60 * 24 * 365), value_type="int")  # 1 year
            },
            'max_retries': max_retries,
            'base_retry_delay': base_retry_delay,
            'max_retry_delay': max_retry_delay
        }

        # Create cache directory if it doesn't exist and caching is enabled
        if cache_enabled and not os.path.exists(cache_directory):
            try:
                os.makedirs(cache_directory)
                logger.info(f"Created cache directory: {cache_directory}")
            except Exception as e:
                logger.warning(f"Failed to create cache directory: {str(e)}")

    @lru_cache(maxsize=32)
    def get(self, key: str, default: Optional[str] = None, value_type: str = "str",
            required: bool = False) -> Any:
        """
        Get a configuration value with type conversion.

        Args:
            key: The configuration key to retrieve
            default: Default value if not found
            value_type: Type to convert the value to ('str', 'int', 'float', 'bool', 'dict', 'list')
            required: Whether the configuration is required

        Returns:
            The configuration value converted to the specified type

        Raises:
            ConfigurationError: If a required configuration is missing or type conversion fails
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

        # Return None for non-required missing values
        if value is None:
            return None

        # Convert to required type
        try:
            if value_type == "str":
                converted_value = str(value)
            elif value_type == "int":
                converted_value = int(value)
            elif value_type == "float":
                converted_value = float(value)
            elif value_type == "bool":
                # Handle various boolean string representations
                if isinstance(value, bool):
                    converted_value = value
                else:
                    value_lower = str(value).lower()
                    converted_value = value_lower in ("yes", "true", "t", "1", "on")
            elif value_type == "dict":
                if isinstance(value, dict):
                    converted_value = value
                else:
                    # Attempt to parse JSON string to dict
                    converted_value = json.loads(value)
            elif value_type == "list":
                if isinstance(value, list):
                    converted_value = value
                elif isinstance(value, str):
                    if value.startswith("[") and value.endswith("]"):
                        # Looks like a JSON array, try to parse it
                        converted_value = json.loads(value)
                    else:
                        # Treat as comma-separated list
                        converted_value = [item.strip() for item in value.split(",")]
                else:
                    converted_value = list(value)
            else:
                error_message = f"Unsupported value_type '{value_type}' for configuration '{key}'"
                logger.error(error_message)
                raise ConfigurationError(error_message)

        except Exception as e:
            error_message = f"Failed to convert configuration '{key}' to type '{value_type}': {str(e)}"
            logger.error(error_message)
            if required:
                raise ConfigurationError(error_message) from e
            # Fall back to original value if conversion fails for non-required config
            converted_value = value

        # Cache the value for future lookups
        self._config_values[key] = converted_value
        return converted_value

    @lru_cache(maxsize=32)
    def get_api_key(self, service_name: str) -> str:
        """
        Get an API key for a specific service with caching optimisation.

        Args:
            service_name: Name of the service

        Returns:
            API key or empty string if not found
        """
        return self._api_keys.get(service_name, "")

    def set(self, key: str, value: Any) -> None:
        """
        Set a configuration value at runtime.

        Args:
            key: The configuration key to set
            value: The value to set
        """
        self._config_values[key] = value
        # Clear cache for this key to ensure the new value is used
        self.get.cache_clear()
        logger.debug(f"Configuration '{key}' set at runtime")

    @property
    def api_keys(self) -> Dict[str, str]:
        """Get API keys configuration dictionary."""
        return self._api_keys

    @property
    def cache_config(self) -> Dict[str, Any]:
        """Get cache configuration dictionary."""
        return self._cache_config

    @property
    def default_location(self) -> str:
        """Get the default location for weather queries."""
        return self._config_values.get("DEFAULT_LOCATION", "Berlin")

    @property
    def is_caching_enabled(self) -> bool:
        """Check if caching is enabled."""
        return self._cache_config.get("enabled", False)

    def reload(self) -> None:
        """Reload configuration from environment and defaults."""
        # Clear lru_cache to ensure fresh values
        self.get.cache_clear()
        self.get_api_key.cache_clear()

        # Reset configuration
        self._config_values = {}
        self._cache_config = {}
        self._api_keys = {}

        # Reload from environment
        load_dotenv(override=True)
        self._load_defaults()
        logger.info("Configuration reloaded")

    def __str__(self) -> str:
        """String representation with sensitive information masked."""
        # Create a copy of the configuration with API keys masked
        safe_config = {**self._config_values}

        # Mask sensitive information
        for key in safe_config:
            if "key" in key.lower() or "secret" in key.lower() or "password" in key.lower():
                if isinstance(safe_config[key], str) and len(safe_config[key]) > 4:
                    # Show only the first and last 2 characters
                    safe_config[key] = safe_config[key][:2] + "***" + safe_config[key][-2:]

        return f"Config({safe_config})"
