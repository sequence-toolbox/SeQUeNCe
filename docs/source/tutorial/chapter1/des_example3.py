"""Demonstrate the usage of the logging system, which is a very useful debugging tool
"""
import sequence as sq
from sequence import log

class Store:
    def __init__(self, tl: sq.Timeline):
        self.opening = False
        self.timeline = tl

    def open(self) -> None:
        if self.timeline.now() >= 60:
            self.timeline.stop()
        
        log.logger.info('Store being opened.')
        if self.opening == True:
            log.logger.warning('Store was already open.')

        self.opening = True
        process = sq.Process(self, 'close', [])
        event = sq.Event(self.timeline.now() + 12, process)
        self.timeline.schedule(event)

    def close(self) -> None:
        if self.timeline.now() >= 60:
            self.timeline.stop()

        log.logger.info('Store being closed.')
        if self.opening == False:
            log.logger.warning('Store was already closed.')

        self.opening = False
        process = sq.Process(self, 'open', [])
        event = sq.Event(self.timeline.now() + 12, process)
        self.timeline.schedule(event)


if __name__ == '__main__':
    tl = sq.Timeline()
    tl.show_progress = False
    store = Store(tl)
    process = sq.Process(store, 'open', [])
    event = sq.Event(7, process)
    tl.schedule(event)

    log_filename = 'store.log'
    log.set_logger(__name__, tl, log_filename)
    log.set_logger_level('INFO')
    log.track_module('des_example3')
    tl.run()