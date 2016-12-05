import logging


class LoggerMixin(object):

    def _build_logger(self):
        self._logger = logging.getLogger('{}.{}'.format(type(self).__module__, type(self).__name__))
