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
from falconswagger.constants import SWAGGER_VALIDATOR
from falconswagger.utils import get_dir_path, get_module_path, build_validator
from falconswagger.models.base import ModelBaseMeta
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


class ModelHttpMeta(ModelBaseMeta):

    def __init__(cls, name, bases_classes, attributes):
        SWAGGER_VALIDATOR.validate(cls.__schema__)

        for path in cls.__schema__:
            if path != 'definitions':
                for key, method_schema in cls.__schema__[path].items():
                    if key != 'parameters' and key != 'definitions':
                        operation_id = method_schema['operationId']
                        if not hasattr(cls, operation_id):
                            raise ModelBaseError(
                                "'operationId' '{}' was not found".format(operation_id))

        ModelBaseMeta.__init__(cls, name, bases_classes, attributes)

        if not hasattr(cls, '__api__'):
            cls.__api__ = None

        if not hasattr(cls, '__schema_dir__'):
            cls.__schema_dir__ = get_module_path(cls)
        
        cls._set_default_options()

    def _set_default_options(cls):
        for uri_template, schema in cls.__schema__.items():
            if not 'options' in schema:
                options_operation = create_default_options([k.upper() for k in schema.keys()])
                uri_template_norm = uri_template.strip('/').replace('{', '_').replace('}', '_')
                options_operation_name = '{}_{}'.format('options', uri_template_norm) \
                    if uri_template_norm else 'options'

                setattr(cls, options_operation_name, options_operation)
                schema['options'] = cls._build_options_schema(options_operation_name)

    def _build_options_schema(cls, options_operation_name):
        return {
            'operationId': options_operation_name,
            'responses': {
                '204': {
                    'description': 'No Content',
                    'headers': {'Allow': {'type': 'string'}}
                }
            }
        }

    def on_delete(cls, req, resp, **kwargs):
        pass

    def on_get(cls, req, resp, **kwargs):
        pass

    def on_head(cls, req, resp, **kwargs):
        pass

    def on_options(cls, req, resp, **kwargs):
        pass

    def on_patch(cls, req, resp, **kwargs):
        pass

    def on_post(cls, req, resp, **kwargs):
        pass

    def on_put(cls, req, resp, **kwargs):
        pass
