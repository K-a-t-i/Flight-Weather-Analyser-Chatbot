import hashlib
import json
import logging
import os
import random
import re
import time
import functools
from datetime import datetime, timedelta

import dateparser
import aiohttp  # async HTTP
import asyncio  # async operations

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Decorator for timing function execution
def timing_decorator(func):
    """
    Decorator to measure and log execution time of a function.

    Args:
        func: The function to be timed

    Returns:
        Wrapped function that logs execution time
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        execution_time = end_time - start_time
        logger.info(f"Function {func.__name__} executed in {execution_time:.4f} seconds")
        return result
    return wrapper

# Decorator for async timing
def async_timing_decorator(func):
    """
    Decorator to measure and log execution time of an async function.

    Args:
        func: The async function to be timed

    Returns:
        Wrapped async function that logs execution time
    """
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        start_time = time.time()
        result = await func(*args, **kwargs)
        end_time = time.time()
        execution_time = end_time - start_time
        logger.info(f"Async function {func.__name__} executed in {execution_time:.4f} seconds")
        return result
    return wrapper

# Decorator for logging function calls
def log_function_call(func):
    """
    Decorator to log function calls with arguments and return values.

    Args:
        func: The function to log

    Returns:
        Wrapped function that logs calls
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        args_repr = [repr(a) for a in args]
        kwargs_repr = [f"{k}={v!r}" for k, v in kwargs.items()]
        signature = ", ".join(args_repr + kwargs_repr)
        logger.debug(f"Calling {func.__name__}({signature})")
        try:
            result = func(*args, **kwargs)
            logger.debug(f"{func.__name__} returned {result!r}")
            return result
        except Exception as e:
            logger.error(f"{func.__name__} raised {type(e).__name__}: {str(e)}")
            raise
    return wrapper

def get_env_variable(var_name, default=None, required=False):
    """
    Get an environment variable with optional default value and requirement check.

    Args:
        var_name (str): Name of the environment variable
        default (any, optional): Default value if variable is not found
        required (bool): Whether the variable is required

    Returns:
        The environment variable value or default

    Raises:
        ValueError: If the variable is required but not found
    """
    value = os.getenv(var_name, default)
    if value is None and required:
        error_msg = f"Required environment variable {var_name} not set"
        logger.error(error_msg)
        raise ValueError(error_msg)
    return value

def generate_cache_key(url, params, api_type):
    """
    Generate a unique cache key based on the request parameters.

    Args:
        url (str): API endpoint URL
        params (dict): Parameters for the API request
        api_type (str): Type of API ('coordinates', 'weather', or 'historical')

    Returns:
        str: A unique hash for the request
    """
    # Create a sorted parameter string to ensure consistent keys
    param_str = json.dumps(params, sort_keys=True)
    key_data = f"{url}:{param_str}"

    # Create a hash of the key data
    hash_obj = hashlib.md5(key_data.encode())
    cache_key = hash_obj.hexdigest()

    return f"{api_type}_{cache_key}"

def get_cache_path(cache_directory, cache_key):
    """Get the full path to a cache file."""
    return os.path.join(cache_directory, f"{cache_key}.json")

@log_function_call
def save_to_cache(cache_directory, cache_key, data, cache_enabled=True):
    """
    Save data to the cache.

    Args:
        cache_directory (str): Directory to store cache files
        cache_key (str): The cache key
        data (dict): The data to cache
        cache_enabled (bool): Whether caching is enabled
    """
    if not cache_enabled:
        return

    cache_data = {
        "timestamp": time.time(),
        "data": data
    }

    cache_path = get_cache_path(cache_directory, cache_key)

    try:
        with open(cache_path, 'w') as f:
            json.dump(cache_data, f)
        logger.debug(f"Saved data to cache: {cache_key}")
    except Exception as e:
        logger.warning(f"Failed to save data to cache: {str(e)}")

@log_function_call
def get_from_cache(cache_directory, cache_key, ttl, cache_enabled=True):
    """
    Retrieve data from the cache if it exists and is not expired.

    Args:
        cache_directory (str): Directory to store cache files
        cache_key (str): The cache key
        ttl (int): Time-to-live in seconds
        cache_enabled (bool): Whether caching is enabled

    Returns:
        tuple: (cache_hit, data) where cache_hit is a boolean and data is the cached data or None
    """
    if not cache_enabled:
        return False, None

    cache_path = get_cache_path(cache_directory, cache_key)

    if not os.path.exists(cache_path):
        return False, None

    try:
        with open(cache_path, 'r') as f:
            cache_data = json.load(f)

        timestamp = cache_data.get("timestamp", 0)
        data = cache_data.get("data")

        # Check if the cache is still valid
        if time.time() - timestamp <= ttl:
            logger.debug(f"Cache hit for: {cache_key}")
            return True, data
        else:
            logger.debug(f"Cache expired for: {cache_key}")
            return False, None
    except Exception as e:
        logger.warning(f"Failed to read from cache: {str(e)}")
        return False, None

def parse_date(date_string):
    """
    Parse a date string into a datetime.date object with improved handling
    for relative dates and ambiguous inputs.

    Args:
        date_string (str): String representation of a date

    Returns:
        datetime.date: The parsed date

    Raises:
        ValueError: If the date cannot be parsed
    """
    # Normalise input
    date_string = date_string.lower().strip()

    # Handle common "next week" case
    if date_string == "next week":
        current_date = datetime.now().date()
        return current_date + timedelta(days=7)

    # Handle day names first
    days = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
    day_name = date_string.lower()

    for day in days:
        if day in day_name:
            current_date = datetime.now().date()
            current_day = current_date.weekday()
            target_day = days.index(day)

            # If query contains "next" (e.g., "next monday"), always go to next week
            if "next" in day_name:
                days_ahead = 7 - current_day + target_day
                if days_ahead >= 7:
                    days_ahead -= 7
                days_ahead += 7  # Add another week
                return current_date + timedelta(days=days_ahead)

            # Standard calculation for current week, wrapping to next week if needed
            days_ahead = target_day - current_day
            if days_ahead <= 0:  # Target day is today or in the past week
                days_ahead += 7
            return current_date + timedelta(days=days_ahead)

    # Handle "in X days" pattern
    days_pattern = re.compile(r'in\s+(\d+)\s+days?')
    match = days_pattern.search(date_string)
    if match:
        days = int(match.group(1))
        return datetime.now().date() + timedelta(days=days)

    # If not a day name or special pattern, use dateparser
    parsed_date = dateparser.parse(
        date_string,
        settings={
            'RELATIVE_BASE': datetime.now(),
            'PREFER_DATES_FROM': 'future',
            'STRICT_PARSING': False
        }
    )

    if parsed_date:
        return parsed_date.date()
    else:
        raise ValueError(f"Unable to parse date: {date_string}")

@timing_decorator
def handle_api_request(url, params, api_name, cache_type=None, cache_config=None):
    """
    Handle API requests with error handling, logging, caching, and retry mechanism.

    Args:
        url (str): API endpoint URL
        params (dict): Parameters for the API request
        api_name (str): Name of the API for logging purposes
        cache_type (str, optional): Type of cache to use ('coordinates', 'weather', 'historical')
        cache_config (dict, optional): Configuration for caching

    Returns:
        tuple: (success, data) where success is a boolean and data is the JSON response or error message
    """
    import requests  # Import here to not create global dependency

    # Set default cache configuration if not provided
    if cache_config is None:
        cache_config = {
            'enabled': False,
            'directory': 'cache',
            'ttl': {
                'coordinates': 60 * 60 * 24 * 30,  # 30 days
                'weather': 60 * 60,  # 1 hour
                'historical': 60 * 60 * 24 * 365  # 1 year
            },
            'max_retries': 3,
            'base_retry_delay': 1.0,
            'max_retry_delay': 10.0
        }

    # Check cache if enabled and cache_type is provided
    if cache_type and cache_config['enabled']:
        cache_key = generate_cache_key(url, params, cache_type)
        cache_ttl = cache_config['ttl'].get(cache_type, 3600)  # Default to 1 hour if type not found

        cache_hit, cached_data = get_from_cache(
            cache_config['directory'],
            cache_key,
            cache_ttl,
            cache_config['enabled']
        )
        if cache_hit:
            logger.info(f"Using cached data for {api_name} API request")
            return True, cached_data

    retries = 0
    max_retries = cache_config.get('max_retries', 3)
    base_retry_delay = cache_config.get('base_retry_delay', 1.0)
    max_retry_delay = cache_config.get('max_retry_delay', 10.0)

    while retries <= max_retries:
        try:
            if retries > 0:
                # Calculate backoff delay with jitter
                delay = min(base_retry_delay * (2 ** (retries - 1)) + random.uniform(0, 0.5), max_retry_delay)
                logger.info(f"Retry {retries}/{max_retries} for {api_name} API request after {delay:.2f}s delay")
                time.sleep(delay)

            logger.info(f"Making {api_name} API request to {url}" + (f" (retry {retries})" if retries > 0 else ""))
            response = requests.get(url, params=params, timeout=10)

            # Check for rate limiting or server errors that should trigger retries
            if response.status_code in [429, 500, 502, 503, 504]:
                retries += 1
                logger.warning(f"{api_name} API returned status code {response.status_code}, triggering retry")
                continue

            if response.status_code == 200:
                data = response.json()
                logger.info(f"Successful {api_name} API response")

                # Save to cache if caching is enabled
                if cache_type and cache_config['enabled']:
                    save_to_cache(cache_config['directory'], cache_key, data, cache_config['enabled'])

                return True, data
            else:
                error_msg = f"{api_name} API returned status code {response.status_code}"
                logger.error(error_msg)
                return False, f"Error: {error_msg}"

        except requests.exceptions.Timeout:
            retries += 1
            if retries <= max_retries:
                logger.warning(f"{api_name} API request timed out, retry {retries}/{max_retries}")
                continue
            error_msg = f"{api_name} API request timed out after {max_retries} retries"
            logger.error(error_msg)
            return False, f"Error: {error_msg}"

        except requests.exceptions.ConnectionError:
            retries += 1
            if retries <= max_retries:
                logger.warning(f"Connection error when accessing {api_name} API, retry {retries}/{max_retries}")
                continue
            error_msg = f"Connection error when accessing {api_name} API after {max_retries} retries"
            logger.error(error_msg)
            return False, f"Error: {error_msg}"

        except json.JSONDecodeError:
            error_msg = f"Invalid JSON response from {api_name} API"
            logger.error(error_msg)
            return False, f"Error: {error_msg}"

        except Exception as e:
            error_msg = f"Unexpected error in {api_name} API request: {str(e)}"
            logger.error(error_msg)
            return False, f"Error: {error_msg}"

    # Should only be reached if all retries were used up
    error_msg = f"All {max_retries} retries failed for {api_name} API request"
    logger.error(error_msg)
    return False, f"Error: {error_msg}"

@async_timing_decorator
async def handle_api_request_async(url, params, api_name, cache_type=None, cache_config=None):
    """
    Asynchronous version of handle_api_request for parallel API calls.

    Args:
        url (str): API endpoint URL
        params (dict): Parameters for the API request
        api_name (str): Name of the API for logging purposes
        cache_type (str, optional): Type of cache to use ('coordinates', 'weather', 'historical')
        cache_config (dict, optional): Configuration for caching

    Returns:
        tuple: (success, data) where success is a boolean and data is the JSON response or error message
    """
    # Set default cache configuration if not provided
    if cache_config is None:
        cache_config = {
            'enabled': False,
            'directory': 'cache',
            'ttl': {
                'coordinates': 60 * 60 * 24 * 30,  # 30 days
                'weather': 60 * 60,  # 1 hour
                'historical': 60 * 60 * 24 * 365  # 1 year
            },
            'max_retries': 3,
            'base_retry_delay': 1.0,
            'max_retry_delay': 10.0
        }

    # Check cache if enabled and cache_type is provided
    if cache_type and cache_config['enabled']:
        cache_key = generate_cache_key(url, params, cache_type)
        cache_ttl = cache_config['ttl'].get(cache_type, 3600)  # Default to 1 hour if type not found

        cache_hit, cached_data = get_from_cache(
            cache_config['directory'],
            cache_key,
            cache_ttl,
            cache_config['enabled']
        )
        if cache_hit:
            logger.info(f"Using cached data for {api_name} API request (async)")
            return True, cached_data

    retries = 0
    max_retries = cache_config.get('max_retries', 3)
    base_retry_delay = cache_config.get('base_retry_delay', 1.0)
    max_retry_delay = cache_config.get('max_retry_delay', 10.0)

    while retries <= max_retries:
        try:
            if retries > 0:
                # Calculate backoff delay with jitter
                delay = min(base_retry_delay * (2 ** (retries - 1)) + random.uniform(0, 0.5), max_retry_delay)
                logger.info(f"Retry {retries}/{max_retries} for {api_name} API request after {delay:.2f}s delay (async)")
                await asyncio.sleep(delay)

            logger.info(f"Making async {api_name} API request to {url}" + (f" (retry {retries})" if retries > 0 else ""))

            # Use aiohttp for async HTTP requests
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params, timeout=10) as response:
                    # Check for rate limiting or server errors that should trigger retries
                    if response.status in [429, 500, 502, 503, 504]:
                        retries += 1
                        logger.warning(f"{api_name} API returned status code {response.status}, triggering retry (async)")
                        continue

                    if response.status == 200:
                        data = await response.json()
                        logger.info(f"Successful {api_name} API response (async)")

                        # Save to cache if caching is enabled
                        if cache_type and cache_config['enabled']:
                            save_to_cache(cache_config['directory'], cache_key, data, cache_config['enabled'])

                        return True, data
                    else:
                        error_msg = f"{api_name} API returned status code {response.status} (async)"
                        logger.error(error_msg)
                        return False, f"Error: {error_msg}"

        except asyncio.TimeoutError:
            retries += 1
            if retries <= max_retries:
                logger.warning(f"{api_name} API request timed out, retry {retries}/{max_retries} (async)")
                continue
            error_msg = f"{api_name} API request timed out after {max_retries} retries (async)"
            logger.error(error_msg)
            return False, f"Error: {error_msg}"

        except aiohttp.ClientConnectionError:
            retries += 1
            if retries <= max_retries:
                logger.warning(f"Connection error when accessing {api_name} API, retry {retries}/{max_retries} (async)")
                continue
            error_msg = f"Connection error when accessing {api_name} API after {max_retries} retries (async)"
            logger.error(error_msg)
            return False, f"Error: {error_msg}"

        except json.JSONDecodeError:
            error_msg = f"Invalid JSON response from {api_name} API (async)"
            logger.error(error_msg)
            return False, f"Error: {error_msg}"

        except Exception as e:
            error_msg = f"Unexpected error in {api_name} API request: {str(e)} (async)"
            logger.error(error_msg)
            return False, f"Error: {error_msg}"

    # Should only be reached if all retries were used up
    error_msg = f"All {max_retries} retries failed for {api_name} API request (async)"
    logger.error(error_msg)
    return False, f"Error: {error_msg}"
