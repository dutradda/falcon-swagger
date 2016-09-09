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


from jsonschema import ValidationError
from myreco.exceptions import JSONError
import json


class FalconJsonSchemaMiddleware(object):
    def process_resource(self, req, resp, resource, params):
        self._process_resource(req, resource)

    def _process_resource(self, req, resource):
        method = req.method.upper()
        if method in resource.allowed_methods:
            if req.body:
                try:
                    req.body = json.loads(req.body)
                except ValueError as error:
                    raise JSONError(*error.args)

            validator = getattr(resource, 'on_{}_validator'.format(method), None)

            if validator is not None:
                try:
                    validator.validate(req.body)
                except ValidationError as error:
                    raise JSONError(*error.args)

    def process_response(self, req, resp, resource):
        try:
            resp.body = json.dumps(resp.body)
        except ValueError as error:
            raise JSONError(*error.args)


class FalconSQLAlchemyRedisMiddleware(object):
    def __int__(self, bind, redis_bind):
        self._bind = bind
        self._redis_bind = redis_bind

    def process_resource(self, req, resp, resource, params):
        session = Session(bind=self._bind, redis_bind=self._redis_bind)
        resource.session = session

    def process_response(self, req, resp, resource):
        resource.session.close()
        resource.session = None
