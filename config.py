"""
Configuration file for Substack Downloader
All configurable values in one place
"""
import os

# Network settings
REQUEST_TIMEOUT = int(os.getenv('SUBSTACK_TIMEOUT', '30'))
MAX_RETRIES = int(os.getenv('SUBSTACK_MAX_RETRIES', '3'))
RETRY_BACKOFF_FACTOR = float(os.getenv('SUBSTACK_RETRY_BACKOFF', '1.0'))
RATE_LIMIT_DELAY = float(os.getenv('SUBSTACK_RATE_LIMIT_DELAY', '1.0'))

# Retry on these HTTP status codes
RETRY_STATUS_CODES = [429, 500, 502, 503, 504]

# Headers
USER_AGENT = os.getenv(
    'SUBSTACK_USER_AGENT',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36'
)

# Content selectors (in priority order)
# Format: (tag, class_name) - class_name can be None
CONTENT_SELECTORS = [
    ('div', 'available-content'),
    ('div', 'body markup'),
    ('article', None),
    ('div', 'post-content'),
    ('main', None)
]

# API settings
API_LIMIT_PER_REQUEST = 12

# Image settings
IMAGE_CHUNK_SIZE = 8192
MAX_IMAGE_SIZE = int(os.getenv('SUBSTACK_MAX_IMAGE_SIZE', str(10 * 1024 * 1024)))  # 10MB default

# File settings
MAX_FILENAME_LENGTH = 255
OUTPUT_DIR = os.getenv('SUBSTACK_OUTPUT_DIR', 'output')

# Cache settings
ENABLE_CACHE = os.getenv('SUBSTACK_ENABLE_CACHE', 'false').lower() == 'true'
CACHE_DIR = os.getenv('SUBSTACK_CACHE_DIR', '.cache')

# Concurrency settings
MAX_CONCURRENT_FETCHES = int(os.getenv('SUBSTACK_MAX_WORKERS', '5'))

# Logging settings
LOG_LEVEL = os.getenv('SUBSTACK_LOG_LEVEL', 'INFO')
LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
LOG_FILE = os.getenv('SUBSTACK_LOG_FILE', None)  # None = console only
