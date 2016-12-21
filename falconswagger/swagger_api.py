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
from falconswagger.middlewares import SessionMiddleware, SwaggerMiddleware
from falconswagger.router import ModelRouter, Route
from falconswagger.exceptions import JSONError, ModelBaseError, UnauthorizedError, SwaggerAPIError
from falconswagger.mixins import LoggerMixin
from falconswagger.utils import get_module_path
from falconswagger.constants import SWAGGER_TEMPLATE, SWAGGER_SCHEMA
from falconswagger.hooks import authorization_hook
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
                 title=None, version='1.0.0', authorizer=None,
                 get_swagger_req_auth=True):
        self._build_logger()
        self._validate_metadata(title, version, swagger_template)
        middleware = self._set_session_middleware(sqlalchemy_bind, redis_bind, middleware)
        self._set_swagger_template(swagger_template, title, version)
        self.authorizer = authorizer
        self._get_swagger_req_auth = get_swagger_req_auth

        self.models = dict()
        for model in models:
            self.associate_model(model)

        swagger_mid = SwaggerMiddleware(models, authorizer=authorizer)
        middleware.append(swagger_mid)

        API.__init__(self, router=router, middleware=middleware)

        for model in self.models.values():
            for uri_template in getattr(model, '__schema__', {}):
                self.add_route(uri_template, model)

        self.add_route('/swagger.json', self)

        self.add_error_handler(Exception, self._handle_generic_error)
        self.add_error_handler(HTTPError, self._handle_http_error)
        self.add_error_handler(IntegrityError, self._handle_integrity_error)
        self.add_error_handler(
            ValidationError, self._handle_json_validation_error)
        self.add_error_handler(JSONError)
        self.add_error_handler(ModelBaseError)
        self.add_error_handler(UnauthorizedError)

    def _set_session_middleware(self, sqlalchemy_bind, redis_bind, middleware):
        if sqlalchemy_bind is not None or redis_bind is not None:
            sess_mid = SessionMiddleware(sqlalchemy_bind, redis_bind)

            if middleware is None:
                middleware = [sess_mid]
            else:
                middleware.append(sess_mid)

        return middleware

    def _validate_metadata(self, title, version, swagger_template):
        if bool(title is None) == bool(swagger_template is None):
            raise SwaggerAPIError("One of 'title' or 'swagger_template' "
                                  "arguments must be setted.")

        if version != '1.0.0' and swagger_template is not None:
            raise SwaggerAPIError("'version' argument can't be setted when "
                                  "'swagger_template' was setted.")

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

                self.models[model.__name__] = model
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
                self.models.pop(model.__name__)
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

    def add_route(self, uri_template, resource, *args, **kwargs):
        base_path = self.swagger.get('basePath', '')
        base_path = '' if base_path == '/' else base_path.strip('/')
        uri_template = '/'.join([base_path, uri_template.strip('/')])
        return API.add_route(self, uri_template, resource, *args, **kwargs)

    def on_get(self, req, resp):
        if self.authorizer and self._get_swagger_req_auth:
            authorization_hook(self.authorizer, req, resp, {})

        resp.body = json.dumps(self.swagger, indent=2)

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
