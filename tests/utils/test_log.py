import os

import sequence.utils.log as lg
import logging
from sequence.kernel.timeline import Timeline

filename = "tests/utils/test.log"


class DumbEntity():
    def __init__(self):
        pass

    def log(self):
        lg.logger.debug("test message")


def file_len(fname):
    return sum(1 for line in open(fname))


def test_new_log():
    tl = Timeline()
    lg.set_logger(__name__, tl, filename)


def test_track_module():
    modules = ["test1", "test2", "test3"]
    for mod in modules:
        lg.track_module(mod)

    assert len(lg._log_modules) == len(modules)
    for mod in modules:
        assert mod in lg._log_modules


def test_log():
    open(filename, 'w').close()

    assert file_len(filename) == 0

    tl = Timeline()
    de = DumbEntity()

    lg.set_logger(__name__, tl, filename)
    lg.set_logger_level("DEBUG")
    lg.track_module(__name__)

    tl.init()
    de.log()

    # TODO: fix (should be 1)
    assert file_len(filename) == 2
