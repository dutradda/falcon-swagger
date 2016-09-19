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


from collections import defaultdict
from glob import glob
from re import match as re_match, sub as re_sub
from jsonschema import RefResolver, Draft4Validator, ValidationError
from falcon import HTTP_CREATED, HTTPNotFound, HTTP_NO_CONTENT
from copy import deepcopy
import os.path
import json


class Route(object):

    def __init__(self, uri_template, method, action,
                 validator=None, output_schema=None,
                 authorizer=None):
        self.uri_template = uri_template
        self.method = method
        self.action = action
        self.validator = validator
        self._output_schema = output_schema
        self._schemas_sinks = dict()
        self.authorizer = authorizer

        if validator:
            schema_uri = self.uri_template + '/_schemas/input'
            self._schemas_sinks[self._sink_input_schema] = schema_uri

        if output_schema:
            schema_uri = self.uri_template + '/_schemas/output'
            self._schemas_sinks[self._sink_output_schema] = schema_uri

    @property
    def has_schemas(self):
        return bool(self._schemas_sinks)

    def register(self, api, model):
        api.add_route(self.uri_template, model)

        if self.validator:
            schema_uri = self.uri_template + '/_schemas/input'
            api.add_sink(self._sink_input_schema, schema_uri)

        if self._output_schema:
            schema_uri = self.uri_template + '/_schemas/output'
            api.add_sink(self._sink_output_schema, schema_uri)
            self._schemas_sinks[schema_uri] = self._output_schema

        if self.has_schemas:
            api.add_sink(self._sink_schemas, self.uri_template + '/_schemas')

    def _sink_input_schema(self, req, resp):
        resp.body = self.validator.schema

    def _sink_output_schema(self, req, resp):
        resp.body = self._output_schema

    def _sink_schemas(self, req, resp):
        build_link = lambda uri: '{}://{}{}'.format(
            req.protocol, req.host, uri)
        resp.body = [build_link(schema_uri)
                     for schema_uri in self._schemas_uris]


class URISchemaHandler(object):

    def __init__(self, schemas_path):
        self._schemas_path = schemas_path

    def __call__(self, uri):
        schema_filename = os.path.join(
            self._schemas_path, uri.replace('schema:', ''))
        with open(schema_filename) as json_schema_file:
            return json.load(json_schema_file)


class _RoutesBuilderMeta(type):

    def _build_routes_from_schemas(cls, model):
        schemas_path = cls.get_schemas_path(model)
        schemas_glob = os.path.join(schemas_path, '*.json')
        schema_regex = r'(([\w\d%_-]+)_)?(post|put|patch|delete|get)_(input|output).json'
        routes_data = defaultdict(lambda: defaultdict(dict))

        for json_schema_filename in glob(schemas_glob):
            json_schema_basename = os.path.basename(json_schema_filename)
            match = re_match(schema_regex, json_schema_basename)
            if match:
                cls._set_route_data(routes_data, model,
                                    match, json_schema_filename)

        return cls._build_routes(routes_data)

    def get_schemas_path(cls, model):
        module_filename = model.get_module_filename()
        module_path = os.path.dirname(os.path.abspath(module_filename))
        return os.path.join(module_path, 'schemas')

    def _set_route_data(cls, routes_data, model, match, json_schema_filename):
        uri_template = cls._build_uri(model, match.groups()[1])
        method = match.groups()[2].upper()
        type_ = match.groups()[3]
        schema = {}

        with open(json_schema_filename) as json_schema_file:
            schema = json.load(json_schema_file)

        if type_ == 'input':
            schema = cls._build_validator(schema, model)

        routes_data[uri_template][method][type_] = schema

    def _build_uri(cls, model, uri_template_sufix):
        base_uri_template = model.api_prefix + model.tablename
        uri_template_sufix_regex = r'%([\d\w_-]+)%'

        if uri_template_sufix is not None:
            uri_template_sufix = re_sub(
                uri_template_sufix_regex, r'{\1}', uri_template_sufix)
            uri_template_sufix = uri_template_sufix.replace('__', '/')

            return '/'.join((base_uri_template, uri_template_sufix))

        return base_uri_template

    def _build_validator(cls, schema, model):
        handlers = {'schema': URISchemaHandler(cls.get_schemas_path(model))}
        resolver = RefResolver.from_schema(schema, handlers=handlers)
        Draft4Validator.check_schema(schema)
        return Draft4Validator(schema, resolver=resolver)

    def _build_routes(cls, routes_data):
        added_uris = set()
        routes = set()

        for uri_template, methods in routes_data.items():
            cls._set_route(routes, uri_template, methods)

        return routes

    def _set_route(cls, routes, uri_template, methods):
        for method, types in methods.items():
            validator = None
            output_schema = {}

            for type_, schema in types.items():
                if type_ == 'input':
                    validator = schema
                else:
                    output_schema = schema

            action = cls._get_action(uri_template, method)
            routes.add(Route(uri_template, method,
                             action, validator, output_schema))

    def _get_action(cls, uri_template, method):
        uri_name = 'model_name'
        try:
            uri_template.format()
        except KeyError:
            uri_name = 'primaries_keys'

        return getattr(cls, '_{}_uri_{}_action'.format(uri_name, method.lower()))

    def _build_generic_routes(cls, model):
        uri = uri_single = model.api_prefix + model.tablename

        for id_name in model.primaries_keys:
            uri_single += '/{' + id_name + '}'

        routes = set()
        for method in ['POST', 'PUT', 'PATCH', 'DELETE', 'GET']:
            action = cls._get_action(uri, method)
            route = Route(uri, method, action)
            routes.add(route)

            action = cls._get_action(uri_single, method)
            route = Route(uri_single, method, action)
            routes.add(route)

        return routes

    def _model_name_uri_post_action(cls, req, resp, **kwargs):
        cls._insert(req, resp, with_update=False, **kwargs)

    def _insert(cls, req, resp, with_update=False, **kwargs):
        model = req.context['model']
        session = req.context['session']
        req_body = req.context['body']

        if with_update:
            if isinstance(req_body, list):
                [obj.update(kwargs) for obj in req_body]
            elif isinstance(req_body, dict):
                req_body.update(kwargs)

        resp.body = model.insert(session, req_body)
        resp.body = resp.body if isinstance(req_body, list) else resp.body[0]
        resp.status = HTTP_CREATED

    def _primaries_keys_uri_post_action(cls, req, resp, **kwargs):
        cls._insert(req, resp, with_update=True, **kwargs)

    def _model_name_uri_put_action(cls, req, resp, **kwargs):
        cls._update(req, resp, **kwargs)

    def _update(cls, req, resp, **kwargs):
        model = req.context['model']
        session = req.context['session']
        req_body = req.context['body']

        objs = model.update(session, req_body)

        if objs:
            resp.body = objs
        else:
            raise HTTPNotFound()

    def _primaries_keys_uri_put_action(cls, req, resp, **kwargs):
        model = req.context['model']
        session = req.context['session']
        route = req.context['route']
        req_body = req.context['body']
        req_body_copy = deepcopy(req.context['body'])

        req_body.update({k: v for k, v in kwargs.items() if k not in req_body})
        objs = model.update(session, req_body, ids=kwargs)

        if not objs:
            req_body = req_body_copy
            ambigous_keys = [
                kwa for kwa in kwargs if kwa in req_body and req_body[kwa] != kwargs[kwa]]
            if ambigous_keys:
                raise ValidationError(
                    "Ambiguous value for '{}'".format(
                        "', '".join(ambigous_keys)),
                    instance={'body': req_body, 'uri': kwargs}, schema=route.validator.schema)

            req.context['body'] = req_body
            cls._insert(req, resp, with_update=True, **kwargs)
        else:
            resp.body = objs[0]

    def _model_name_uri_patch_action(cls, req, resp, **kwargs):
        cls._update(req, resp, **kwargs)

    def _primaries_keys_uri_patch_action(cls, req, resp, **kwargs):
        model = req.context['model']
        session = req.context['session']
        req_body = req.context['body']
        req_body.update(kwargs)
        objs = model.update(session, req_body, ids=kwargs)
        if objs:
            resp.body = objs[0]
        else:
            raise HTTPNotFound()

    def _model_name_uri_delete_action(cls, req, resp, **kwargs):
        model = req.context['model']
        session = req.context['session']
        req_body = req.context['body']
        model.delete(session, req.context['body'])
        resp.status = HTTP_NO_CONTENT

    def _primaries_keys_uri_delete_action(cls, req, resp, **kwargs):
        model = req.context['model']
        session = req.context['session']
        model.delete(session, kwargs)
        resp.status = HTTP_NO_CONTENT

    def _model_name_uri_get_action(cls, req, resp, **kwargs):
        model = req.context['model']
        session = req.context['session']
        req_body = req.context['body']

        if req_body:
            resp.body = model.get(session, req_body)
        else:
            resp.body = model.get(session)

        if not resp.body:
            raise HTTPNotFound()

    def _primaries_keys_uri_get_action(cls, req, resp, **kwargs):
        model = req.context['model']
        session = req.context['session']
        resp.body = model.get(session, kwargs)
        if resp.body:
            resp.body = resp.body[0]


class RoutesBuilder(metaclass=_RoutesBuilderMeta):

    def __new__(cls, model, build_from_schemas=True, build_generic=False):
        routes = set()

        if build_from_schemas:
            routes.update(cls._build_routes_from_schemas(model))

        if build_generic:
            routes.update(cls._build_generic_routes(model))

        return routes
