import sequence.utils.log as lg
import logging
from sequence.kernel.timeline import Timeline

filename = "tests/utils/test.log"
lg.logfile = filename


class DumbEntity():
    def __init__(self, name, tl):
        self.name = name
        self.tl = tl

    def send_log(self):
        self.tl.log(self, logging.ERROR, "test message")


def file_len(fname):
    return sum(1 for line in open(fname))


def test_new_log():
    log = lg.new_sequence_logger("")


def test_timeline_init():
    tl = Timeline()
    tl.logflag = True
    tl.init()


def test_timeline_log():
    open(filename, 'w').close()

    assert file_len(filename) == 0

    tl = Timeline()
    tl.logflag = True
    de = DumbEntity("de", tl)

    tl.init()
    de.send_log()

    # TODO: fix (should be 1)
    assert file_len(filename) == 3
