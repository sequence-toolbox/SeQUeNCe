"""Logging information.

This module defines the behavior for the default SeQUeNCe logging system.
The logger used and log format are specified here.
Modules will use the `logger` attribute as a normal logging system, saving log outputs in a user specified file.
If a file is not set, no output will be recorded.

Attributes:
    logger (Logger): logger object used for logging by sequence modules.
    LOG_FORMAT (str): formatting string for logging.
"""

import logging


def _init_logger():
    lg = logging.getLogger(__name__)
    lg.addHandler(logging.NullHandler())
    return lg

logger = _init_logger()
LOG_FORMAT = '%(asctime)-15s %(simtime)s %(levelname)-8s %(objname)s: %(message)s'


def set_logger(name: str, timeline, logfile="out.log"):
    """Function to link logger to output file.

    The provided timeline is used to add simulation timestamps to the logs.

    Args:
        name (str): name to use for the logger.
        timeline (Timeline): timeline to use for simulation timestamps.
        logfile (str): file to use in recording log output (default "out.log")
    """

    global logger
    logger = logging.getLogger(name)

    handler = logging.FileHandler(logfile)
    fmt = logging.Formatter(LOG_FORMAT)
    f = ContextFilter(timeline)

    handler.setFormatter(fmt)
    logger.addHandler(handler)
    logger.addFilter(f)


def set_logger_level(level: str):
    """Function to set output level of logger without requiring logging import.

    Args:
        level (str): level to set logger to, given as string (in all caps)
    """

    global logger
    logger.setLevel(getattr(logging, level))


class ContextFilter(logging.Filter):
    """Custom filter class to use for the logger."""

    def __init__(self, timeline):
        super().__init__()
        self.timeline = timeline

    def filter(self, record):
        record.simtime = self.timeline.now()
        record.objname = "unnamed"

        if hasattr(record, "caller"):
            caller = record.caller
            if hasattr(caller, "name"):
                record.objname = caller.name
            if hasattr(caller, "logflag"):
                return record.caller.logflag

        return True
