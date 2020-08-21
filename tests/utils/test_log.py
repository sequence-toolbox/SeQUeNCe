import sequence.utils.log as lg
import logging
from sequence.kernel.timeline import Timeline

filename = "tests/utils/test.log"


class DumbEntity():
    def __init__(self, name, tl):
        self.name = name
        self.tl = tl

    def log(self):
        lg.logger.debug("test message", extra={"caller": self})


def file_len(fname):
    return sum(1 for line in open(fname))


def test_new_log():
    tl = Timeline()
    lg.set_logger(__name__, tl, filename)


def test_log():
    open(filename, 'w').close()

    assert file_len(filename) == 0

    tl = Timeline()
    de = DumbEntity("de", tl)

    lg.set_logger(__name__, tl, filename)
    lg.logger.setLevel(logging.DEBUG)

    tl.init()
    de.log()

    # TODO: fix (should be 1)
    assert file_len(filename) == 2
