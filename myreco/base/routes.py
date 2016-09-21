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


class RoutesBuilderBase(object):

    def __new__(cls, model, build_from_schemas=True, build_generic=False, auth_hook=None):
        routes = set()

        if build_from_schemas:
            routes.update(cls._build_default_routes(model, auth_hook))

        if build_generic:
            routes.update(cls._build_generic_routes(model))

        return routes

    @classmethod
    def _build_generic_routes(cls, model):
        uri = uri_single = model.__api_prefix__ + model.__name__

        for id_name in model.__ids_names__:
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

    @classmethod
    def _get_action(cls, uri_template, method):
        uri_name = 'base'
        try:
            uri_template.format()
        except KeyError:
            uri_name = 'ids'

        action_class_name = 'Default{}Actions'.format(method.capitalize())
        action_class = getattr(ROUTES_MODULE, action_class_name)
        return getattr(action_class, '{}_action'.format(uri_name))