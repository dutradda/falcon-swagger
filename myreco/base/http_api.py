from falcon import API, HTTP_INTERNAL_SERVER_ERROR, HTTP_BAD_REQUEST, HTTPError
from myreco.base.middlewares import FalconJsonSchemaMiddleware, FalconSQLAlchemyRedisMiddleware
from myreco.exceptions import JSONError
from sqlalchemy.exc import IntegrityError
from jsonschema import ValidationError

import logging


class HttpAPI(API):
    def __init__(self, sqlalchemy_bind, redis_bind=None):
        json_schema_mid = FalconJsonSchemaMiddleware()
        sqlalchemy_redis_mid = FalconSQLAlchemyRedisMiddleware(sqlalchemy_bind, redis_bind)
        API.__init__(self, middleware=[json_schema_mid, sqlalchemy_redis_mid])

        # self.add_error_handler(Exception, self._handle_generic_error)
        self.add_error_handler(IntegrityError, self._handle_integrity_error)
        self.add_error_handler(ValidationError, self._handle_json_validation_error)
        self.add_error_handler(JSONError, self._handle_json_error)

    def _handle_generic_error(self, exception, req, resp, params):
        resp.status = HTTP_INTERNAL_SERVER_ERROR
        resp.body = {'message': 'Something unexpected happened'}
        logging.exception(exception)

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
