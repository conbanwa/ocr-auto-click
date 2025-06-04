import logging
import os
import sys
from datetime import datetime


class ColoredFormatter(logging.Formatter):
    """Custom formatter with single-letter levels and colored output"""

    # Single-letter level names with colors
    LEVEL_LETTERS = {
        'DEBUG': ('D', '\x1b[36m'),  # Cyan
        'INFO': ('I', '\x1b[32m'),  # Green
        'WARNING': ('W', '\x1b[33m'),  # Yellow
        'ERROR': ('E', '\x1b[31m'),  # Red
        'CRITICAL': ('C', '\x1b[31;1m')  # Bold Red
    }
    RESET = '\x1b[0m'

    def formatTime(self, record, datefmt=None):
        """Format time as just HH:MM:SS"""
        ct = datetime.fromtimestamp(record.created)
        return ct.strftime("%H:%M:%S")

    def format(self, record):
        # Get single-letter level and color
        level_letter, color = self.LEVEL_LETTERS.get(record.levelname, ('?', ''))

        # Apply color to level letter
        colored_level = f"{color}{level_letter}{self.RESET}"
        record.levelname = colored_level

        # Format the message with time, single-letter level, and location
        return super().format(record)


def setup_logging():
    """Configure logging with single-letter colored levels and time-only format"""
    # Enable ANSI colors on Windows
    if sys.platform == "win32":
        os.system("")

    # Create formatter with simplified format
    formatter = ColoredFormatter(
        '%(asctime)s %(levelname)s %(filename)s:%(lineno)d - %(message)s'
    )

    # Configure root logger
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)
    logger.setLevel(logging.INFO)

    # Clear existing handlers
    logger.handlers.clear()

    # Add colored handler
    handler = logging.StreamHandler()
    handler.setFormatter(formatter)
    logger.addHandler(handler)


# Initialize logging
setup_logging()

# Example usage
if __name__ == "__main__":
    logging.debug("Debug message")
    logging.info("Information message")
    logging.warning("Warning message")
    logging.error("Error message")
    logging.critical("Critical message")


window = None

import pyautogui
def get_active_window():
    global window
    window = pyautogui.getActiveWindow()
