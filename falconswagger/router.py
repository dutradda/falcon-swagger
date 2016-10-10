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
from falconswagger.exceptions import ModelBaseError, JSONError
from falconswagger.hooks import authorization_hook
from collections import defaultdict, deque
from jsonschema import RefResolver, Draft4Validator
from falcon import HTTP_METHODS, HTTPMethodNotAllowed
from copy import deepcopy
import re
import os.path
import json


DefaultDict = lambda: defaultdict(DefaultDict)


def build_validator(schema, path):
    handlers = {'': URISchemaHandler(path)}
    resolver = RefResolver.from_schema(schema, handlers=handlers)
    return Draft4Validator(schema, resolver=resolver)


def _build_private_method_name(method_name):
        return '__{}__'.format(method_name)


PRIVATE_METHODS_KEYS = set([_build_private_method_name(method) for method in HTTP_METHODS])


class URISchemaHandler(object):

    def __init__(self, schemas_path):
        self._schemas_path = schemas_path

    def __call__(self, uri):
        schema_filename = os.path.join(self._schemas_path, uri.replace('schema:', ''))
        with open(schema_filename) as json_schema_file:
            return json.load(json_schema_file)


class Route(object):

    def __init__(
            self, uri_template, method_name, operation_name,
            schema, all_methods_parameters, definitions, model):
        self.uri_template = uri_template
        self.method_name = method_name
        self.model = model
        self._operation_name = operation_name
        self._body_validator = None
        self._uri_template_validator = None
        self._query_string_validator = None
        self._headers_validator = None
        self._model_dir = model.get_module_path()
        self._body_required = False
        self._has_body_parameter = False
        self._has_auth = False

        query_string_schema = self._build_default_schema()
        uri_template_schema = self._build_default_schema()
        headers_schema = self._build_default_schema()

        for parameter in all_methods_parameters + schema.get('parameters', []):
            if parameter['in'] == 'body':
                if definitions:
                    body_schema = deepcopy(parameter['schema'])
                    body_schema.update({'definitions': definitions})
                else:
                    body_schema = parameter['schema']

                self._body_validator = build_validator(body_schema, self._model_dir)
                self._body_required = parameter.get('required', False)
                self._has_body_parameter = True

            elif parameter['in'] == 'path':
                self._set_parameter_on_schema(parameter, uri_template_schema)

            elif parameter['in'] == 'query':
                self._set_parameter_on_schema(parameter, query_string_schema)

            elif parameter['in'] == 'header':
                self._set_parameter_on_schema(parameter, headers_schema)

        if uri_template_schema['properties']:
            self._uri_template_validator = build_validator(uri_template_schema, self._model_dir)

        if query_string_schema['properties']:
            self._query_string_validator = build_validator(query_string_schema, self._model_dir)

        if headers_schema['properties']:
            self._has_auth = ('Authorization' in headers_schema['properties']) \
                and ('Authorization' in headers_schema.get('required', []))
            self._headers_validator = build_validator(headers_schema, self._model_dir)

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

    def __call__(self, req, resp, **kwargs):
        if self._has_auth or req.get_header('Authorization'):
            authorization_hook(req, resp, self.model, kwargs)

        body_params = self._build_body_params(req)
        query_string_params = self._build_non_body_params(self._query_string_validator, req.params)
        uri_template_params = self._build_non_body_params(self._uri_template_validator, kwargs)
        headers_params = self._build_non_body_params(self._headers_validator, req, 'headers')
        req.context['parameters'] = {
            'query_string': query_string_params,
            'uri_template': uri_template_params,
            'headers': headers_params,
            'body': body_params
        }

        if self._body_validator:
            req.context['body_schema'] = self._body_validator.schema

        if hasattr(self.model, '__schema__'):
            resp.add_link(self.model.build_schema_uri_template(), 'schema')

        getattr(self.model, self._operation_name)(req, resp)

    def _build_body_params(self, req):
        if req.content_length and (req.content_type is None or 'application/json' in req.content_type):
            if not self._has_body_parameter:
                raise ModelBaseError('Request body is not acceptable')

            body = req.stream.read().decode()
            try:
                body = json.loads(body)
            except ValueError as error:
                raise JSONError(*error.args, input_=body)

            if self._body_validator:
                self._body_validator.validate(body)

            return body

        elif self._body_required:
            raise ModelBaseError('Request body is missing')

        else:
            return None

        return req.stream

    def _build_non_body_params(self, validator, kwargs, type_=None):
        if validator:
            params = {}
            for param_name, prop in validator.schema['properties'].items():
                if type_ == 'headers':
                    param = kwargs.get_header(param_name)
                else:
                    param = kwargs.get(param_name)

                if param:
                    params[param_name] = JsonBuilder(param, prop)

            validator.validate(params)
            return params

        elif type_ == 'headers':
            return {}
        else:
            return kwargs


class UriNode(str):
    __regex__ = re.compile('{([-_a-zA-Z0-9]+)}')

    def __new__(cls, *args, **kwargs):
        uri_node = str.__new__(cls, *args, **kwargs)
        if '}{' in uri_node:
            raise ModelBaseError("Invalid node URI Template '{}'. "
                "A place holder can't be succeed directly another place holder. "
                "Try to put some(s) character(s) between them.".format(uri_node))

        if cls.__regex__.findall(uri_node):
            uri_node.is_complex = True
            uri_regex = cls.__regex__.sub(r'(?P<\1>[-_a-zA-Z0-9]+)', uri_node)
            uri_node.regex = re.compile(uri_regex)
            uri_node.example = cls.__regex__.sub(r'\1', uri_node)
        else:
            uri_node.is_complex = False

        return uri_node


class ModelRouter(object):

    def __init__(self):
        self._nodes = DefaultDict()

    def add_model(self, model):
        for route in model.__routes__:
            uri_template = route.uri_template.strip('/')
            uri_nodes = deque([UriNode(uri_node) for uri_node in uri_template.split('/')])
            nodes_tree = self._nodes
            while uri_nodes:
                nodes_tree = self._set_node(nodes_tree, uri_nodes, route)

    def _set_node(self, nodes_tree, uri_nodes, route):
        node_uri_template = uri_nodes.popleft()
        self._raise_private_method_error(node_uri_template)
        private_method_name = _build_private_method_name(route.method_name)

        if len(uri_nodes) == 0:
            last_node = nodes_tree[node_uri_template]
            route_ = last_node.get(private_method_name)

            if route_:
                raise ModelBaseError(
                    "Route with uri_template '{}' and method '{}' was alreadly registered"
                    " with model '{}'".format(node_uri_template, route.method_name,
                        route_.model.__key__))
            else:
                last_node[private_method_name] = route

        else:
            if node_uri_template.is_complex:
                for key in nodes_tree.keys():
                    if isinstance(key, UriNode) and \
                            key != node_uri_template and key.is_complex:
                        if key.regex.match(node_uri_template.example):
                            raise ModelBaseError(
                                "Ambiguous node uri_template '{}' and '{}'"
                                " with model '{}'".format(
                                    node_uri_template, key, route.model.__key__),
                                input_=nodes_tree)

            return nodes_tree[node_uri_template]

    def _raise_private_method_error(self, node_uri_template):
        if node_uri_template in PRIVATE_METHODS_KEYS:
            raise ModelBaseError("invalid uri_template with '{}' value".format(node_uri_template))

    def remove_model(self, model):
        for route in model.__routes__:
            path_nodes = route.uri_template.strip('/').split('/')
            nodes_tree = self._nodes
            for node_name in path_nodes:
                nodes_tree = nodes_tree.get(node_name)
                if not nodes_tree:
                    break

            if nodes_tree:
                nodes_tree.pop(_build_private_method_name(route.method_name), None)

                for _ in path_nodes:
                    last_path_node = path_nodes[0]
                    nodes_tree = self._nodes[last_path_node]

                    for node_name in path_nodes[1:]:
                        node = nodes_tree.get(node_name)
                        nodes_tree = node
                        if isinstance(nodes_tree, dict) and not nodes_tree:
                            self._nodes[last_path_node].pop(node_name)

    def get_route_and_params(self, req):
        path_nodes = deque(req.path.strip('/').split('/'))
        params = dict()
        private_method_name = _build_private_method_name(req.method)
        nodes_tree = self._nodes
        route = None

        while path_nodes:
            path_node = path_nodes.popleft()
            self._raise_private_method_error(path_node)
            match = self._match_uri_node_template_and_set_params(nodes_tree, path_node, params)

            if match is None:
                break

            elif path_nodes:
                nodes_tree = nodes_tree[match]

            elif private_method_name not in nodes_tree[match]:
                re_string = '__({})__'.format('|'.join(HTTP_METHODS))
                methods = [key.replace('_', '') \
                    for key in nodes_tree[match].keys() if re.match(re_string, key)]
                raise HTTPMethodNotAllowed(methods)

            else:
                route = nodes_tree[match][private_method_name]

        return route, params

    def _match_uri_node_template_and_set_params(self, nodes_tree, path_node, params):
        match_complex = None
        match_simple = None
        for uri_node_template in nodes_tree.keys():
            if not isinstance(uri_node_template, UriNode):
                continue

            if uri_node_template.is_complex:
                uri_regex_match = uri_node_template.regex.match(path_node)
                if uri_regex_match:
                    params.update(uri_regex_match.groupdict())
                    match_complex = uri_node_template
                    continue

            elif str(uri_node_template) == str(path_node):
                match_simple = uri_node_template
                continue

        if match_simple is not None:
            return match_simple

        return match_complex
