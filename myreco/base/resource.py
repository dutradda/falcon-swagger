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


from jsonschema import Draft4Validator, RefResolver, ValidationError
from falcon.errors import HTTPMethodNotAllowed, HTTPNotFound
from falcon import HTTP_CREATED, HTTP_NO_CONTENT
from myreco.base.session import Session
from myreco.exceptions import JSONError
from importlib import import_module
from glob import glob
from re import match as re_match, sub as re_sub
from collections import namedtuple
from copy import deepcopy

import os.path
import json


Route = namedtuple('Route', ['uri', 'method', 'schema', 'validator'])


class FalconModelResource(object):
    def __init__(self, api, allowed_methods, model, api_prefix='/', routes=None):
        self.model = model
        self.api_prefix = api_prefix
        self.allowed_methods = [method.upper() for method in allowed_methods]
        self.routes = self._build_routes(api)

        if routes is not None:
            for route in routes:
                self.routes[(route.uri, route.method)] = route

    def _build_base_uri(self, api_prefix):
        return os.path.join(api_prefix, self.model.tablename)

    def _build_routes(self, api):
        schemas_path = self.get_schemas_path()
        schemas_glob = os.path.join(schemas_path, '*.json')
        ids_str = '_'.join(self.model.primaries_keys.keys())
        schema_regex = '(([\w\d%_-]+)_)?(post|put|patch|delete|get)_(input|output).json'
        routes = {}
        added_uris = set()

        for json_schema_filename in glob(schemas_glob):
            json_schema_basename = os.path.basename(json_schema_filename)
            match = re_match(schema_regex, json_schema_basename)
            if match:
                uri = self._build_uri(match.groups()[1])
                method = match.groups()[2].upper()
                type_ = match.groups()[3]
                schema = {}
                validator = None

                with open(json_schema_filename) as json_schema_file:
                    schema = json.load(json_schema_file)

                if type_ == 'input':
                    validator = self._build_validator(schema)

                if uri not in added_uris:
                    api.add_route(uri, self)
                    added_uris.add(uri)

                routes[(uri, method)] = Route(uri, method, schema, validator)

        if not routes:
            routes = self._build_generic_routes(api)

        return routes

    def get_schemas_path(self):
        module_filename = import_module(type(self).__module__).__file__
        module_path = os.path.dirname(os.path.abspath(module_filename))
        return os.path.join(module_path, 'schemas')

    def _build_uri(self, uri_str):
        uri = self._build_base_uri(self.api_prefix)
        if uri_str is None:
            return uri

        return '/'.join((uri, re_sub(r'%([\d\w_-]+)%', r'{\1}', uri_str).replace('__', '/')))

    def _build_validator(self, schema):
        handlers = {'schema': self._handle_schema_uri}
        resolver = RefResolver.from_schema(schema, handlers=handlers)
        return Draft4Validator(schema, resolver=resolver)

    def _handle_schema_uri(self, uri):
        schema_filename = os.path.join(self.get_schemas_path(), uri.replace('schema:', ''))
        with open(schema_filename) as json_schema_file:
            return json.load(json_schema_file)

    def _build_generic_routes(self, api):
        uri = uri_single = os.path.join(self.api_prefix, '{}/'.format(self.model.tablename))

        for id_name in self.model.primaries_keys:
            uri_single += '{' + id_name + '}/'

        api.add_route(uri, self)
        api.add_route(uri_single, self)

        routes = {}
        for method in self.allowed_methods:
            routes[(uri, method)] = Route(uri, method, {}, None)
            routes[(uri_single, method)] = Route(uri_single, method, {}, None)

        return routes

    def on_post(self, req, resp, **kwargs):
        self._raise_method_not_allowed(req)

        if kwargs:
            raise HTTPNotFound()

        session = req.context['session']
        resp.body = self.model.insert(session, req.context['body'])
        resp.body = resp.body if isinstance(req.context['body'], list) else resp.body[0]
        resp.status = HTTP_CREATED

    def _primaries_keys_names_in_kwargs(self, kwargs):
        return bool([True for id_name in self.model.primaries_keys if id_name in kwargs])

    def _raise_method_not_allowed(self, req):
        if not req.method.upper() in self.allowed_methods:
            raise HTTPMethodNotAllowed(self.allowed_methods)

    def on_put(self, req, resp, **kwargs):
        self._update(req, resp, **kwargs)

    def _update(self, req, resp, with_insert=True, **kwargs):
        self._raise_method_not_allowed(req)

        if kwargs:
            body = deepcopy(req.context['body'])
            req.context['body'].update(kwargs)
            objs = self.model.update(req.context['session'], req.context['body'], ids=kwargs)

            if not objs and with_insert:
                ambigous_keys = \
                    [kwa for kwa in kwargs if kwa in body and body[kwa] != kwargs[kwa]]
                if ambigous_keys:
                    schema = self.routes[(req.uri_template, req.method)].schema
                    raise ValidationError(
                        "Ambiguous value for '{}'".format("', '".join(ambigous_keys)),
                        instance={'body': body, 'uri': kwargs}, schema=schema)

                body.update(kwargs)
                req.context['body'] = body
                self.on_post(req, resp)
            elif objs:
                resp.body = objs[0]
            else:
                raise HTTPNotFound()

        else:
            objs = self.model.update(req.context['session'], req.context['body'])

            if objs:
                resp.body = objs
            else:
                raise HTTPNotFound()

    def on_patch(self, req, resp, **kwargs):
        self._update(req, resp, with_insert=False, **kwargs)

    def on_delete(self, req, resp, **kwargs):
        self._raise_method_not_allowed(req)
        session = req.context['session']

        if kwargs:
            id_ = self.model.get_ids_from_values(kwargs)
            self.model.delete(session, id_)
        else:
            self.model.delete(session, req.context['body'])

        resp.status = HTTP_NO_CONTENT

    def on_get(self, req, resp, **kwargs):
        self._raise_method_not_allowed(req)
        session = req.context['session']

        if kwargs: # get one
            id_ = self.model.get_ids_from_values(kwargs)
            resp.body = self.model.get(session, id_)
            if resp.body:
                resp.body = resp.body[0]

        elif req.context['body']:  # get many
            resp.body = self.model.get(session, req.context['body'])

        else:  # get all
            resp.body = self.model.get(session)

        if not resp.body:
            raise HTTPNotFound()
