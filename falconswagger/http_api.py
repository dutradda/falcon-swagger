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


from falcon import API, HTTP_INTERNAL_SERVER_ERROR, HTTP_BAD_REQUEST, HTTPError, HTTPNotFound
from falconswagger.middlewares import SessionMiddleware
from falconswagger.router import ModelRouter
from falconswagger.exceptions import JSONError, ModelBaseError, UnauthorizedError
from sqlalchemy.exc import IntegrityError
from jsonschema import ValidationError
import logging
import json


class HttpAPI(API):

    def __init__(self, models, sqlalchemy_bind=None, redis_bind=None):
        API.__init__(self, router=ModelRouter(),
            middleware=SessionMiddleware(sqlalchemy_bind, redis_bind))
        self.add_route = None
        del self.add_route

        for model in models:
            self.associate_model(model)

        self.add_error_handler(Exception, self._handle_generic_error)
        self.add_error_handler(HTTPError, self._handle_http_error)
        self.add_error_handler(IntegrityError, self._handle_integrity_error)
        self.add_error_handler(
            ValidationError, self._handle_json_validation_error)
        self.add_error_handler(JSONError)
        self.add_error_handler(ModelBaseError)
        self.add_error_handler(UnauthorizedError)

    def associate_model(self, model):
        self._router.add_model(model)

    def disassociate_model(self, model):
        self._router.remove_model(model)

    def _get_responder(self, req):
        route, params = self._router.get_route_and_params(req)
        if route is None:
            return self._get_sink_responder(req)

        return route, params, route.model, route.uri_template

    def _get_sink_responder(self, path):
        params = {}
        for pattern, sink in self._sinks:
            m = pattern.match(path)
            if m:
                params = m.groupdict()
                return sink, params, None, None
        else:
            raise HTTPNotFound()

    def _handle_http_error(self, exception, req, resp, params):
        self._compose_error_response(req, resp, exception)

    def _handle_integrity_error(self, exception, req, resp, params):
        resp.status = HTTP_BAD_REQUEST
        resp.body = json.dumps({
            'error': {
                'params': exception.params,
                'database message': {
                    'code': exception.orig.args[0],
                    'message': exception.orig.args[1]
                },
                'details': exception.detail
            }
        })

    def _handle_json_validation_error(self, exception, req, resp, params):
        resp.status = HTTP_BAD_REQUEST
        resp.body = json.dumps({
            'error': {
                'message': exception.message,
                'schema': exception.schema,
                'input': exception.instance
            }
        })

    def _handle_generic_error(self, exception, req, resp, params):
        resp.status = HTTP_INTERNAL_SERVER_ERROR
        resp.body = json.dumps({'error': {'message': 'Something unexpected happened'}})
        logging.exception(exception)
