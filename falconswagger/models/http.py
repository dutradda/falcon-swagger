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


from falconswagger.router import Route
from falconswagger.exceptions import ModelBaseError, JSONError
from falconswagger.models.logger import ModelLoggerMetaMixin
from falconswagger.constants import SWAGGER_VALIDATOR
from falconswagger.utils import get_dir_path, get_module_path, build_validator
from falcon.errors import HTTPNotFound, HTTPMethodNotAllowed
from falcon import HTTP_CREATED, HTTP_NO_CONTENT, HTTP_METHODS
from falcon.responders import create_default_options
from jsonschema import ValidationError
from collections import defaultdict
from copy import deepcopy
from concurrent.futures import ThreadPoolExecutor
import json
import os.path
import logging
import random
import re


def _camel_case_convert(name):
    s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
    return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()


class ModelHttpMetaMixin(type):

    def _set_key(cls):
        name = cls.__name__.replace('Model', '')
        cls.__key__ = getattr(cls, '__key__', _camel_case_convert(name))

    def _set_routes(cls):
        SWAGGER_VALIDATOR.validate(cls.__schema__)
        cls.__routes__ = set()
        cls.__options_routes__ = set()
        dict_ = defaultdict(list)
        schema = cls.__schema__
        cls._set_key()

        if not hasattr(cls, '__schema_dir__'):
            cls.__schema_dir__ = get_module_path(cls)

        for uri_template in schema:
            all_methods_parameters = schema[uri_template].get('parameters', [])
            for method_name in HTTP_METHODS:
                method_schema = schema[uri_template].get(method_name.lower())
                if method_schema:
                    method_schema = deepcopy(method_schema)
                    operation_id = method_schema['operationId']

                    try:
                        getattr(cls, operation_id)
                    except AttributeError:
                        raise ModelBaseError("'operationId' '{}' was not found".format(operation_id))

                    definitions = schema.get('definitions')

                    parameters = method_schema.get('parameters', [])
                    parameters.extend(all_methods_parameters)
                    method_schema['parameters'] = parameters

                    route = Route(uri_template, method_name, operation_id, cls,
                                  method_schema, definitions, cls.__authorizer__)
                    cls.__routes__.add(route)

        routes = defaultdict(set)
        for route in cls.__routes__:
            routes[route.uri_template].add(route.method_name)

        for uri_template, methods_names in routes.items():
            if not 'OPTIONS' in methods_names:
                options_operation = create_default_options(methods_names)
                uri_template_norm = uri_template.replace('{', '_').replace('}', '_')
                options_operation_name = '{}_{}'.format(uri_template_norm, 'options')
                setattr(cls, options_operation_name, options_operation)

                route = Route(uri_template, 'OPTIONS', options_operation_name,
                              cls, {}, [], cls.__authorizer__)
                cls.__options_routes__.add(route)
                cls.__routes__.add(route)


class ModelHttpMeta(ModelLoggerMetaMixin, ModelHttpMetaMixin):
    __authorizer__ = None
    __api__ = None

    def __init__(cls, name, bases_classes, attributes):
        cls._set_logger()
        cls._set_routes()
