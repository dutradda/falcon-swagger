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


from myreco.base.actions import (DefaultPostActions, DefaultPutActions,
    DefaultPatchActions, DefaultDeleteActions, DefaultGetActions)
from glob import glob
from re import match as re_match, sub as re_sub
from jsonschema import RefResolver, Draft4Validator
from sys import modules
import os.path
import json


ROUTES_MODULE = modules[__name__]


class Route(object):

    def __init__(self, uri_template, method, action,
                 validator=None, output_schema=None, hooks=None):
        self._schemas_sinks = dict()
        self.uri_template = uri_template
        self.method = method
        self.action = action
        self.validator = validator
        self.output_schema = output_schema

        if hooks:
            for hook in hooks:
                self.action = hook(self.action)

    @property
    def has_schemas(self):
        return bool(self._schemas_sinks)

    @property
    def output_schema(self):
        return self._output_schema

    @property
    def validator(self):
        return self._validator

    @output_schema.setter
    def output_schema(self, schema):
        if schema:
            schema_uri = self.uri_template + '/_schemas/{}/output'.format(self.method.lower())
            self._schemas_sinks[schema_uri] = self._sink_output_schema
        self._output_schema = schema

    @validator.setter
    def validator(self, validator):
        if validator:
            schema_uri = self.uri_template + '/_schemas/{}/input'.format(self.method.lower())
            self._schemas_sinks[schema_uri] = self._sink_input_schema
        self._validator = validator

    def register(self, api, model):
        api.add_route(self.uri_template, model)

        if self.has_schemas:
            schema_uri = self.uri_template + '/_schemas/{}'.format(self.method.lower())
            api.add_sink(self._sink_schemas, schema_uri)

        for uri_sink, callback in self._schemas_sinks.items():
            api.add_sink(callback, uri_sink)

    def _sink_input_schema(self, req, resp):
        resp.body = self.validator.schema

    def _sink_output_schema(self, req, resp):
        resp.body = self.output_schema

    def _sink_schemas(self, req, resp):
        build_link = lambda uri: '{}://{}{}'.format(
            req.protocol, req.host, uri)
        resp.body = [build_link(schema_uri) for schema_uri in self._schemas_sinks]


class URISchemaHandler(object):

    def __init__(self, schemas_path):
        self._schemas_path = schemas_path

    def __call__(self, uri):
        schema_filename = os.path.join(
            self._schemas_path, uri.replace('schema:', ''))
        with open(schema_filename) as json_schema_file:
            return json.load(json_schema_file)


class _SQLAlchemyRedisModelRoutesBuilderMeta(type):

    def _build_routes_from_schemas(cls, model, auth_hook):
        schemas_path = cls.get_schemas_path(model)
        schemas_glob = os.path.join(schemas_path, '*.json')
        schema_regex = r'(([\w\d%_-]+)_)?(post|put|patch|delete|get)_(input|output)(_auth)?.json'
        routes = dict()

        for json_schema_filename in glob(schemas_glob):
            json_schema_basename = os.path.basename(json_schema_filename)
            match = re_match(schema_regex, json_schema_basename)
            if match:
                route = cls._set_route(routes, model, match,
                                       json_schema_filename,
                                       auth_hook)

        return set(routes.values())

    def get_schemas_path(cls, model):
        module_filename = model.get_module_filename()
        module_path = os.path.dirname(os.path.abspath(module_filename))
        return os.path.join(module_path, 'schemas')

    def _set_route(cls, routes, model, match, json_schema_filename, auth_hook):
        uri_template = cls._build_uri(model, match.groups()[1])
        method = match.groups()[2].upper()
        type_ = match.groups()[3]
        auth = match.groups()[4]
        hooks = {auth_hook} if auth and auth_hook else None
        output_schema = None
        validator = None

        with open(json_schema_filename) as json_schema_file:
            schema = json.load(json_schema_file)

        if type_ == 'input':
            validator = cls._build_validator(schema, model)
        else:
            output_schema = schema

        if (uri_template, method) in routes:
            if output_schema is not None:
                routes[(uri_template, method)].output_schema = output_schema
            if validator is not None:
                routes[(uri_template, method)].validator = validator
            return

        action = cls._get_action(uri_template, method)
        routes[(uri_template, method)] = Route(uri_template, method, action, validator=validator,
                                               output_schema=output_schema, hooks=hooks)

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

    def _get_action(cls, uri_template, method):
        uri_name = 'base'
        try:
            uri_template.format()
        except KeyError:
            uri_name = 'ids'

        action_class_name = 'Default{}Actions'.format(method.capitalize())
        action_class = getattr(ROUTES_MODULE, action_class_name)
        return getattr(action_class, '{}_action'.format(uri_name))

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


class SQLAlchemyRedisModelRoutesBuilder(metaclass=_SQLAlchemyRedisModelRoutesBuilderMeta):

    def __new__(cls, model, build_from_schemas=True, build_generic=False, auth_hook=None):
        routes = set()

        if build_from_schemas:
            routes.update(cls._build_routes_from_schemas(model, auth_hook))

        if build_generic:
            routes.update(cls._build_generic_routes(model))

        return routes
