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


from myreco.exceptions import JSONError
from myreco.base.session import Session
from falcon.errors import HTTPNotFound, HTTPMethodNotAllowed
import json


class FalconRoutesMiddleware(object):
    def __init__(self, routes):
        self._routes = dict()
        self._allowed_methods = set()
        for route in routes:
            self._routes[(route.uri_template, route.method)] = route
            self._allowed_methods.add(route.method)

    def process_resource(self, req, resp, model, uri_params):
        route = self._get_route(req.uri_template, req.method)
        body = req.stream.read().decode()
        if body:
            try:
                req.context['body'] = json.loads(body)
            except ValueError as error:
                req.context['body'] = body
                raise JSONError(*error.args, input_=req.context['body'])
        else:
            req.context['body'] = {}

        if route.has_schemas:
            resp.add_link(route.uri_template + '/schemas/', 'schemas')

        if route.validator is not None:
            route.validator.validate(req.context['body'])

        route.action(req, resp, model, uri_params)

    def _get_route(self, uri_template, method):
        if not method in self._allowed_methods:
            raise HTTPMethodNotAllowed(self._allowed_methods)

        route = self._routes.get((uri_template, method))
        if not route:
            raise HTTPNotFound()

        return route

    def process_response(self, req, resp, model):
        if resp.body and resp.body != 0:
            resp.body = json.dumps(resp.body)


class FalconSQLAlchemyRedisMiddleware(FalconRoutesMiddleware):

    def __init__(self, bind, redis_bind=None, routes=None):
        self._bind = bind
        self._redis_bind = redis_bind

        if routes is None:
            routes = set()

        FalconRoutesMiddleware.__init__(self, routes)

    def process_resource(self, req, resp, model, uri_params):
        FalconRoutesMiddleware.process_resource(
            self, req, resp, model, uri_params)
        req.context['session'] = Session(
            bind=self._bind, redis_bind=self._redis_bind)

    def process_response(self, req, resp, model):
        FalconRoutesMiddleware.process_response(self, req, resp, model)
        session = req.context.pop('session', None)
        if session is not None:
            session.close()
