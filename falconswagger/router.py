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
from falconswagger.utils import build_validator
from collections import defaultdict, deque
from jsonschema import RefResolver, Draft4Validator
from falcon import HTTP_METHODS, HTTPMethodNotAllowed
from copy import deepcopy
import re
import os.path
import json


DefaultDict = lambda: defaultdict(DefaultDict)


def _build_private_method_name(method_name):
        return '__{}__'.format(method_name)


PRIVATE_METHODS_KEYS = set([_build_private_method_name(method) for method in HTTP_METHODS])


class Route(object):

    def __init__(
            self, uri_template, method_name, operation_name, module,
            schema, definitions, authorizer=None):
        self.uri_template = uri_template
        self.method_name = method_name
        self._operation_name = operation_name
        self.module = module
        self._authorizer = authorizer
        self._body_validator = None
        self._uri_template_validator = None
        self._query_string_validator = None
        self._headers_validator = None
        self._schema_dir = module.__schema_dir__
        self._body_required = False
        self._has_body_parameter = False
        self._auth_required = False

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
            if has_auth and self._authorizer is None:
                raise ModelBaseError("'authorizer' must be setted with Authorization header setted")

            self._auth_required = (has_auth
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

    def __call__(self, req, resp, **kwargs):
        if self._auth_required:
            authorization_hook(self._authorizer, req, resp, kwargs)

        body_params = self._build_body_params(req)
        query_string_params = self._build_non_body_params(self._query_string_validator, req.params)
        uri_template_params = self._build_non_body_params(self._uri_template_validator, kwargs)
        headers_params = self._build_non_body_params(self._headers_validator, req, 'headers')
        req.context['parameters'] = {
            'query_string': query_string_params,
            'path': uri_template_params,
            'headers': headers_params,
            'body': body_params
        }

        if self._body_validator:
            req.context['body_schema'] = self._body_validator.schema

        getattr(self.module, self._operation_name)(req, resp)

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

    def _build_non_body_params(self, validator, kwargs, type_=None):
        if validator:
            params = {}
            for param_name, prop in validator.schema['properties'].items():
                if type_ == 'headers':
                    param = kwargs.get_header(param_name)
                else:
                    param = kwargs.get(param_name)

                if param is not None:
                    params[param_name] = JsonBuilder.build(param, prop)

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


class DefaultDictRouter(object):
    _method_map_key = '__method_map__'

    def __init__(self):
        self._nodes = DefaultDict()

    def add_route(self, uri_template, method_map, resource, *args, **kwargs):
        uri_nodes = deque([UriNode(uri_node) for uri_node in uri_template.split('/')])
        nodes_tree = self._nodes
        while uri_nodes:
            nodes_tree = self._set_node(nodes_tree, uri_nodes, method_map, resource)

    def _set_node(self, nodes_tree, uri_nodes, method_map, resource):
        node_uri_template = uri_nodes.popleft()
        self._raise_method_map_error(node_uri_template)

        if len(uri_nodes) == 0:
            last_node = nodes_tree[node_uri_template]
            resource_method_map = last_node.get(type(self)._method_map_key)

            if resource_method_map:
                raise ModelBaseError(
                    "Route with uri_template '{}' was alreadly registered by resource '{}'"
                    .format(node_uri_template, str(resource_method_map[0])))
            else:
                last_node[type(self)._method_map_key] = (resource, method_map)

        else:
            if node_uri_template.is_complex:
                for key in nodes_tree.keys():
                    if isinstance(key, UriNode) and \
                            key != node_uri_template and key.is_complex:
                        if key.regex.match(node_uri_template.example):
                            raise ModelBaseError(
                                "Ambiguous node uri_template '{}' and '{}'"
                                .format(
                                    node_uri_template, key),
                                input_=nodes_tree)

            return nodes_tree[node_uri_template]

    def _raise_method_map_error(self, node_uri_template):
        if type(self)._method_map_key == node_uri_template:
            raise ModelBaseError("invalid uri_template with '{}' value".format(node_uri_template))

    def find(self, path):
        path_nodes = deque(path.split('/'))
        params = dict()
        nodes_tree = self._nodes
        resource, method_map = None, None

        while path_nodes:
            path_node = path_nodes.popleft()
            self._raise_method_map_error(path_node)
            match = self._match_uri_node_template_and_set_params(nodes_tree, path_node, params)

            if match is None:
                break

            elif path_nodes:
                nodes_tree = nodes_tree[match]

            else:
                (resource, method_map) = nodes_tree[match][type(self)._method_map_key]
                break

        return resource, method_map, params, path

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


class ModelRouter(object):

    def __init__(self):
        self._nodes = DefaultDict()

    def add_model(self, model, base_path=''):
        for route in model.__routes__:
            self.add_route(route)

    def add_route(self, route, base_path=''):
        uri_template = route.uri_template.strip('/')
        uri_template = base_path + uri_template
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
                    .format(node_uri_template, route.method_name_))
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
                                .format(
                                    node_uri_template, key),
                                input_=nodes_tree)

            return nodes_tree[node_uri_template]

    def _raise_private_method_error(self, node_uri_template):
        if node_uri_template in PRIVATE_METHODS_KEYS:
            raise ModelBaseError("invalid uri_template with '{}' value".format(node_uri_template))

    def get_route_and_params(self, req):
        path_nodes = deque(self._split_uri(req.path))
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

    def _split_uri(self, uri):
        return uri.strip('/').split('/')

    def _match_uri_node_template_and_set_params(self, nodes_tree, path_node, params):
        if not '{' in path_node or not '}' in path_node:
            if path_node in nodes_tree:
                return path_node

        match_complex = None

        for uri_node_template in nodes_tree.keys():
            if not isinstance(uri_node_template, UriNode):
                continue

            if uri_node_template.is_complex:
                uri_regex_match = uri_node_template.regex.match(path_node)
                if uri_regex_match:
                    params.update(uri_regex_match.groupdict())
                    match_complex = uri_node_template
                    continue

        return match_complex

    def remove_model(self, model):
        for route in model.__routes__:
            self.remove_route(route)

        for route in model.__options_routes__:
            self.remove_route(route)

    def remove_route(self, route):
        path_nodes = route.uri_template.strip('/').split('/')
        nodes_tree = self._nodes
        nodes_tree_reverse = [nodes_tree]

        for node_name in path_nodes:
            nodes_tree = nodes_tree.get(node_name)
            if nodes_tree is None:
                break
            else:
                nodes_tree_reverse.append(nodes_tree)

        if nodes_tree is not None: # this node_tree is a method_map
            method_map = nodes_tree_reverse.pop()
            method_map.pop(_build_private_method_name(route.method_name), None)

            if not method_map:
                while nodes_tree_reverse:
                    nodes_tree_reverse.pop().pop(path_nodes.pop())
