"""Logging information.

This module defines the behavior for the default SeQUeNCe logging system.
The logger used and log format are specified here.
Modules will use the `logger` attribute as a normal logging system, saving log outputs in a user specified file.
If a file is not set, no output will be recorded.

Attributes:
    logger (Logger): logger object used for logging by sequence modules.
    LOG_FORMAT (str): formatting string for logging as '{real time}\t{simulation time}\t%{log level}\t{module name}\t{message}'.
    _log_modules (List[str]): modules to track with logging (given as list of names)
"""

import logging


def _init_logger():
    lg = logging.getLogger(__name__)
    lg.addHandler(logging.NullHandler())
    return lg


logger = _init_logger()
LOG_FORMAT = '%(asctime)-15s\t%(simtime)s\t%(levelname)-8s\t%(module)s:\t%(message)s'
_log_modules = []


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

    # reset logging
    open(logfile, 'w').close()
    

def set_logger_level(level: str):
    """Function to set output level of logger without requiring logging import.

    Args:
        level (str): level to set logger to, given as string (in all caps)
    """

    global logger
    logger.setLevel(getattr(logging, level))


def track_module(module_name: str):
    """Sets a given module to be tracked by logger."""

    global _log_modules
    _log_modules.append(module_name)


def remove_module(module_name: str):
    """Sets a given module to no longer be tracked."""

    global _log_modules
    assert module_name in _log_modules, "Module is not currently logged: " + module_name
    _log_modules.remove(module_name)


class ContextFilter(logging.Filter):
    """Custom filter class to use for the logger."""

    def __init__(self, timeline):
        super().__init__()
        self.timeline = timeline

    def filter(self, record):
        global _log_modules
        record.simtime = self.timeline.now()
        return record.module in _log_modules
