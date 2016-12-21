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
        ModelBaseMeta.__init__(cls, name, bases_classes, attributes)

        if not hasattr(cls, '__api__'):
            cls.__api__ = None

        if not hasattr(cls, '__schema_dir__'):
            cls.__schema_dir__ = get_module_path(cls)
        
        cls._set_default_options()

    def _set_default_options(cls):
        for uri_template, schema in cls.__schema__.items():
            if not 'options' in schema:
                options_operation = create_default_options(schema.keys())
                uri_template_norm = uri_template.replace('{', '_').replace('}', '_')
                options_operation_name = '{}_{}'.format(uri_template_norm, 'options')

                setattr(cls, options_operation_name, options_operation)
                schema['options'] = cls._build_options_schema(options_operation_name)

    def on_delete(cls, req, resp):
        cls._execute_operation(req, resp)

    def _execute_operation(cls, req, resp):
        operation_name = req.context['method_schema']['operationId']
        getattr(cls, operation_name)(req, resp)

    def on_get(cls, req, resp):
        cls._execute_operation(req, resp)

    def on_patch(cls, req, resp):
        cls._execute_operation(req, resp)

    def on_post(cls, req, resp):
        cls._execute_operation(req, resp)

    def on_put(cls, req, resp):
        cls._execute_operation(req, resp)

    def on_head(cls, req, resp):
        cls._execute_operation(req, resp)

    def on_options(cls, req, resp):
        cls._execute_operation(req, resp)
