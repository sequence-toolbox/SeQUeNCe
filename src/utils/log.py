"""Logging information.

This module defines a method to create loggers for SeQUeNCe.
These loggers are created on and used by timelines.

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
    global logger
    logger = logging.getLogger(name)

    handler = logging.FileHandler(logfile)
    fmt = logging.Formatter(LOG_FORMAT)
    f = ContextFilter(timeline)

    handler.setFormatter(fmt)
    logger.addHandler(handler)
    logger.addFilter(f)


class ContextFilter(logging.Filter):
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
