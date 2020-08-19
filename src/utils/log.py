"""Logging information.

This module defines a method to create loggers for SeQUeNCe.
These loggers are created on and used by timelines.

Attributes:
    logfile (str): file name to use for logging.
    LOG_FORMAT (str): formatting string for logging.
"""

import logging

logfile = None
LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'

def new_sequence_logger(name: str):
    """Function to generate and configure new logger.

    Currently uses default `Logger` class.

    Args:
        name (str): name of logger.

    Returns:
        Logger: configured logger to use.
    """

    logger = logging.getLogger(name)
    handler = logging.FileHandler(logfile)
    handler.setFormatter(LOG_FORMAT)
    logger.addHandler(handler)
    return logger
