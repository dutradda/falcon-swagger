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


from falconswagger.json_builder import JsonBuilder
from falconswagger.exceptions import SwaggerMethodError, JSONError
from falconswagger.utils import build_validator
from copy import deepcopy
import json


class SwaggerMethod(object):

    def __init__(self, operation, schema, definitions, schema_dir):
        self._operation = operation
        self._body_validator = None
        self._uri_template_validator = None
        self._query_string_validator = None
        self._headers_validator = None
        self._schema_dir = schema_dir
        self._body_required = False
        self._has_body_parameter = False
        self.auth_required = False

        query_string_schema = self._build_default_schema()
        uri_template_schema = self._build_default_schema()
        headers_schema = self._build_default_schema()

        for parameter in schema.get('parameters', []):
            if parameter['in'] == 'body':
                if definitions:
                    body_schema = deepcopy(parameter['schema'])
                    body_schema.update({'definitions': definitions})
                else:
                    body_schema = parameter['schema']

                self._body_validator = build_validator(body_schema, self._schema_dir)
                self._body_required = parameter.get('required', False)
                self._has_body_parameter = True

            elif parameter['in'] == 'path':
                self._set_parameter_on_schema(parameter, uri_template_schema)

            elif parameter['in'] == 'query':
                self._set_parameter_on_schema(parameter, query_string_schema)

            elif parameter['in'] == 'header':
                self._set_parameter_on_schema(parameter, headers_schema)

        if uri_template_schema['properties']:
            self._uri_template_validator = build_validator(uri_template_schema, self._schema_dir)

        if query_string_schema['properties']:
            self._query_string_validator = build_validator(query_string_schema, self._schema_dir)

        if headers_schema['properties']:
            has_auth = ('Authorization' in headers_schema['properties'])

            self.auth_required = (has_auth
                and ('Authorization' in headers_schema.get('required', [])))

            self._headers_validator = build_validator(headers_schema, self._schema_dir)

    def _build_default_schema(self):
        return {'type': 'object', 'required': [], 'properties': {}}

    def _set_parameter_on_schema(self, parameter, schema):
        name = parameter['name']
        property_ = {'type': parameter['type']}

        if parameter['type'] == 'array':
            items = parameter.get('items', {})
            if items:
                property_['items'] = items

        if parameter['type'] == 'object':
            obj_schema = parameter.get('schema', {})
            if obj_schema:
                property_.update(obj_schema)

        if parameter.get('required'):
            schema['required'].append(name)

        schema['properties'][name] = property_

    def __call__(self, req, resp, uri_params):
        body_params = self._build_body_params(req)
        query_string_params = self._build_non_body_params(self._query_string_validator, req.params)
        uri_template_params = self._build_non_body_params(self._uri_template_validator, uri_params)
        headers_params = self._build_non_body_params(self._headers_validator, req, 'headers')
        req.context['parameters'] = {
            'query_string': query_string_params,
            'path': uri_template_params,
            'headers': headers_params,
            'body': body_params
        }

        if self._body_validator:
            req.context['body_schema'] = self._body_validator.schema

        self._operation(req, resp)

    def _build_body_params(self, req):
        if req.content_length and (req.content_type is None or 'application/json' in req.content_type):
            if not self._has_body_parameter:
                raise SwaggerMethodError('Request body is not acceptable')

            body = req.stream.read().decode()
            try:
                body = json.loads(body)
            except ValueError as error:
                raise JSONError(*error.args, input_=body)

            if self._body_validator:
                self._body_validator.validate(body)

            return body

        elif self._body_required:
            raise SwaggerMethodError('Request body is missing')

        else:
            return None

    def _build_non_body_params(self, validator, params, type_=None):
        if validator:
            for param_name, prop in validator.schema['properties'].items():
                if type_ == 'headers':
                    param = params.get_header(param_name)
                    params = {}
                else:
                    param = params.get(param_name)

                if param is not None:
                    params[param_name] = JsonBuilder.build(param, prop)

            validator.validate(params)
            return params

        elif type_ == 'headers':
            return {}
        else:
            return params
