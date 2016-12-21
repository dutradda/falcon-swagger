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


from falconswagger.models.orm.session import Session
from falconswagger.swagger_method import SwaggerMethod
from falconswagger.utils import get_module_path
from falconswagger.hooks import authorization_hook
from falconswagger.exceptions import SwaggerAPIError
from falcon import HTTP_METHODS
from falcon.errors import HTTPMethodNotAllowed
from collections import defaultdict


class SessionMiddleware(object):

    def __init__(self, sqlalchemy_bind=None, redis_bind=None):
        self.sqlalchemy_bind = sqlalchemy_bind
        self.redis_bind = redis_bind

    def process_resource(self, req, resp, model, uri_params):
        if getattr(model, '__session__', None):
            req.context['session'] = model.__session__
            return

        req.context['session'] = Session(bind=self.sqlalchemy_bind, redis_bind=self.redis_bind)

    def process_response(self, req, resp, model):
        session = req.context.pop('session', None)
        if session is not None \
                and hasattr(session, 'close') \
                and not getattr(model, '__session__', None):
            session.close()


class SwaggerMiddleware(object):

    def __init__(self, schema, models_map, authorizer=None):
        self.schema = schema
        self.authorizer = authorizer
        self._build_uri_method_map(models_map)

    def _build_uri_method_map(self):
        self._uri_method_map = defaultdict(dict)
        paths_schema = self.schema['paths']

        for uri_template in paths_schema:
            all_methods_parameters = paths_schema[uri_template].get('parameters', [])
            self._validate_authorizer(all_methods_parameters)

            for method_name in HTTP_METHODS:
                method_schema = paths_schema[uri_template].get(method_name.lower())

                if method_schema is not None:
                    method_schema = deepcopy(method_schema)

                    model_name, operation_id = '.'.split(method_schema['operationId'])
                    model = models_map[model_name]

                    definitions = paths_schema.get('definitions')

                    parameters = method_schema.get('parameters', [])
                    self._validate_authorizer(parameters)
                    parameters.extend(all_methods_parameters)

                    method_schema['parameters'] = parameters
                    method = SwaggerMethod(method_schema, definitions, get_module_path(model))
                    self._uri_method_map[uri_template][method_name] = method

    def _validate_authorizer(self, parameters):
        for param in parameters:
            if param['in'] == 'header' and param['name'] == 'Authorization' and self.authorizer is None:
                raise SwaggerAPIError(
                    "'authorizer' attribute must be setted with 'Authorization' header setted")

    def process_resource(self, req, resp, model, uri_params):
        method = self._uri_method_map[req.uri_template].get(req.method)
        if method is None:
            raise HTTPMethodNotAllowed()

        elif method.auth_required or (self.authorizer and req.get_header('Authorization')):
            authorization_hook(self.authorizer, req, resp, kwargs)

        method.set_swagger_parameters(req, resp, uri_params)

    def process_response(self, req, resp, model):
        pass
