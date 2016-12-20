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
from falconswagger.router import ModelRouter, Route
from falconswagger.exceptions import JSONError, ModelBaseError, UnauthorizedError, SwaggerAPIError
from falconswagger.mixins import LoggerMixin
from falconswagger.utils import get_module_path
from falconswagger.constants import SWAGGER_TEMPLATE, SWAGGER_SCHEMA
from sqlalchemy.exc import IntegrityError
from jsonschema import Draft4Validator
from jsonschema import ValidationError
from copy import deepcopy
import logging
import json
import re


class SwaggerAPI(API, LoggerMixin):

    def __init__(self, models, sqlalchemy_bind=None, redis_bind=None,
                 middleware=None, router=None, swagger_template=None,
                 title=None, version='1.0.0', authorizer=None):
        if sqlalchemy_bind is not None or redis_bind is not None:
            sess_mid = SessionMiddleware(sqlalchemy_bind, redis_bind)

            if middleware is None:
                middleware = sess_mid
            else:
                middleware.append(sess_mid)

        if router is None:
            router = ModelRouter()

        API.__init__(self, router=router, middleware=middleware)
        self._build_logger()

        type(self).__schema_dir__ = get_module_path(type(self))

        if bool(title is None) == bool(swagger_template is None):
            raise SwaggerAPIError("One of 'title' or 'swagger_template' "
                                  "arguments must be setted.")

        if version != '1.0.0' and swagger_template is not None:
            raise SwaggerAPIError("'version' argument can't be setted when "
                                  "'swagger_template' was setted.")

        self._set_swagger_template(swagger_template, title, version)

        self._logger = logging.getLogger(type(self).__module__ + '.' + type(self).__name__)
        self.models = dict()
        self.add_route = None
        del self.add_route

        for model in models:
            self.associate_model(model)

        self._set_swagger_json_route(authorizer)

        self.add_error_handler(Exception, self._handle_generic_error)
        self.add_error_handler(HTTPError, self._handle_http_error)
        self.add_error_handler(IntegrityError, self._handle_integrity_error)
        self.add_error_handler(
            ValidationError, self._handle_json_validation_error)
        self.add_error_handler(JSONError)
        self.add_error_handler(ModelBaseError)
        self.add_error_handler(UnauthorizedError)

    def _set_swagger_template(self, swagger_template, title, version):
        if swagger_template is None:
            swagger_template = deepcopy(SWAGGER_TEMPLATE)
            swagger_template['info']['title'] = title
            swagger_template['info']['version'] = version

        if swagger_template['paths']:
            raise SwaggerAPIError("The Swagger Json 'paths' property will be populated "
                "by the 'models' contents. This property must be empty.")

        Draft4Validator(SWAGGER_SCHEMA).validate(swagger_template)

        self.swagger = deepcopy(swagger_template)
        definitions = self.swagger.get('definitions', {})
        self.swagger['definitions'] = definitions

    def associate_model(self, model):
        if hasattr(model, '__schema__'):
            if model.__api__ is not self:
                if isinstance(model.__api__, SwaggerAPI):
                    model.__api__.disassociate_model(model)

                base_path = self.swagger.get('basePath', '')
                base_path = '' if base_path == '/' else base_path

                self._router.add_model(model, base_path)
                self.models[model.__key__] = model
                model.__api__ = self

                model_paths = deepcopy(model.__schema__)
                definitions = {}

                for definition, values in model_paths.pop('definitions', {}).items():
                    definitions['{}.{}'.format(model.__name__, definition)] = values

                for path in model_paths.values():
                    for method in path.values():
                        if not isinstance(method, list):
                            opId = method['operationId']
                            method['operationId'] = '{}.{}'.format(model.__name__, opId)

                self._validate_model_paths(model_paths, model.__name__)
                json_paths = json.dumps(model_paths)
                json_paths = re.sub(r'"#/definitions/([a-zA-Z0-9_]+)"',
                        r'"#/definitions/{}.\1"'.format(model.__name__),
                        json_paths)
                model_paths = json.loads(json_paths)

                self.swagger['paths'].update(model_paths)
                self.swagger['definitions'].update(definitions)

    def disassociate_model(self, model):
        if hasattr(model, '__schema__'):
            if model.__api__ is self:
                self._router.remove_model(model)
                self.models.pop(model.__key__)
                [self.swagger['paths'].pop(path, None) for path in model.__schema__]

                for definition in model.__schema__.get('definitions', {}):
                    self.swagger['definitions'].pop('{}.{}'.format(model.__name__, definition))

    def _validate_model_paths(self, model_paths, model_name):
        for path in model_paths:
            if path in self.swagger['paths']:
                raise SwaggerAPIError("Duplicated path '{}' for models '{}' and '{}'".format(
                    path, model_name, self._get_duplicated_path_model_name(path)))

    def _get_duplicated_path_model_name(self, path):
        models_repeated_paths = []
        for model in self.models.values():
            if path in model.__schema__:
                return model.__name__

    def _set_swagger_json_route(self, authorizer):
        if authorizer:
            schema = {
                'parameters': [{
                    'name': 'Authorization',
                    'in': 'header',
                    'required': True,
                    'type': 'string'
                }]
            }
        else:
            schema = {}

        self._swagger_route = Route('/swagger.json', 'GET', '_get_swagger_json',
                      self, schema, [], authorizer)
        self._router.add_route(self._swagger_route, self.swagger.get('basePath', ''))

    def _get_swagger_json(self, req, resp):
        resp.body = json.dumps(self.swagger, indent=2)

    def _get_responder(self, req):
        route, params = self._router.get_route_and_params(req)
        if route is None:
            return self._get_sink_responder(req)

        return route, params, route.module, route.uri_template

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
        self._logger.exception('ERROR Unexpected')
