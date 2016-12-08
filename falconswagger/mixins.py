import logging


class LoggerMixin(object):

    def _build_logger(self):
        self._logger = logging.getLogger(self._build_logger_name())

    def _build_logger_name(self):
        return '{}.{}'.format(type(self).__module__, type(self).__name__)
