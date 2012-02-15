import logging
import logging.handlers
import weakref

logger = logging.getLogger('cornice')

# stolen from the packaging stdlib testsuite tools


class _TestHandler(logging.handlers.BufferingHandler):
    # stolen and adapted from test.support

    def __init__(self):
        logging.handlers.BufferingHandler.__init__(self, 0)
        self.setLevel(logging.DEBUG)

    def shouldFlush(self):
        return False

    def emit(self, record):
        self.buffer.append(record)


class LoggingCatcher(object):
    """TestCase-compatible mixin to receive logging calls.

    Upon setUp, instances of this classes get a BufferingHandler that's
    configured to record all messages logged to the 'cornice' logger
    """

    def setUp(self):
        super(LoggingCatcher, self).setUp()
        self.loghandler = handler = _TestHandler()
        self._old_level = logger.level
        logger.addHandler(handler)
        logger.setLevel(logging.DEBUG)  # we want all messages

    def tearDown(self):
        handler = self.loghandler
        # All this is necessary to properly shut down the logging system and
        # avoid a regrtest complaint.  Thanks to Vinay Sajip for the help.
        handler.close()
        logger.removeHandler(handler)
        for ref in weakref.getweakrefs(handler):
            logging._removeHandlerRef(ref)
        del self.loghandler
        logger.setLevel(self._old_level)
        super(LoggingCatcher, self).tearDown()

    def get_logs(self, level=logging.WARNING, flush=True):
        """Return all log messages with given level.

        *level* defaults to logging.WARNING.

        For log calls with arguments (i.e.  logger.info('bla bla %r', arg)),
        the messages will be formatted before being returned (e.g. "bla bla
        'thing'").

        Returns a list.  Automatically flushes the loghandler after being
        called, unless *flush* is False (this is useful to get e.g. all
        warnings then all info messages).
        """
        messages = [log.getMessage() for log in self.loghandler.buffer
                    if log.levelno == level]
        if flush:
            self.loghandler.flush()
        return messages
