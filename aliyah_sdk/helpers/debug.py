from functools import wraps
from pprint import pformat

from aliyah_sdk.logging import logger


def debug_print_function_params(func):
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        logger.debug("\n<AALIYAH_DEBUG_OUTPUT>")
        logger.debug(f"{func.__name__} called with arguments:")

        for key, value in kwargs.items():
            logger.debug(f"{key}: {pformat(value)}")

        logger.debug("</AALIYAH_DEBUG_OUTPUT>\n")

        return func(self, *args, **kwargs)

    return wrapper
