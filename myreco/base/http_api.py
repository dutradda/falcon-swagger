# MIT License

# Copyright (c) 2016 Diogo Dutra

# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.


from falcon import API, HTTP_INTERNAL_SERVER_ERROR, HTTP_BAD_REQUEST, HTTPError
from myreco.base.middlewares import FalconSQLAlchemyRedisMiddleware
from myreco.exceptions import JSONError
from sqlalchemy.exc import IntegrityError
from jsonschema import ValidationError

import logging


class HttpAPI(API):
    def __init__(self, sqlalchemy_bind, redis_bind=None):
        sqlalchemy_redis_mid = FalconSQLAlchemyRedisMiddleware(sqlalchemy_bind, redis_bind)
        API.__init__(self, middleware=sqlalchemy_redis_mid)

        self.add_error_handler(IntegrityError, self._handle_integrity_error)
        self.add_error_handler(ValidationError, self._handle_json_validation_error)
        self.add_error_handler(JSONError, self._handle_json_error)
        self._error_handlers.append((Exception, self._handle_generic_error))

    def _handle_integrity_error(self, exception, req, resp, params):
        resp.status = HTTP_BAD_REQUEST
        resp.body = {
            'error': {
                'params': exception.params,
                'database message': {
                    'code': exception.orig.args[0],
                    'message': exception.orig.args[1]
                },
                'details': exception.detail
            }
        }
        logging.exception(exception)

    def _handle_json_error(self, exception, req, resp, params):
        resp.status = HTTP_BAD_REQUEST
        resp.body = {
            'error': {
                'message': exception.args[0],
                'instance': req.context['body']
            }
        }
        logging.exception(exception)

    def _handle_json_validation_error(self, exception, req, resp, params):
        resp.status = HTTP_BAD_REQUEST
        resp.body = {
            'error': {
                'message': exception.message,
                'schema': exception.schema,
                'instance': exception.instance
            }
        }
        logging.exception(exception)

    def _handle_generic_error(self, exception, req, resp, params):
        resp.status = HTTP_INTERNAL_SERVER_ERROR
        resp.body = {'error': {'message': 'Something unexpected happened'}}
        logging.exception(exception)
