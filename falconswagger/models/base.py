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


from falconswagger.router import Route, build_validator
from falconswagger.exceptions import ModelBaseError, JSONError
from falcon.errors import HTTPNotFound, HTTPMethodNotAllowed
from falcon import HTTP_CREATED, HTTP_NO_CONTENT, HTTP_METHODS
from falcon.responders import create_default_options
from jsonschema import ValidationError
from collections import defaultdict
from copy import deepcopy
from importlib import import_module
import json
import os.path


def get_dir_path(filename):
    return os.path.dirname(os.path.abspath(filename))


def get_model_schema(filename):
    return json.load(open(os.path.join(get_dir_path(filename), 'schema.json')))


def get_module_path(cls):
    module_filename = import_module(cls.__module__).__file__
    return get_dir_path(module_filename)


SWAGGER_VALIDATOR = build_validator(
    {'$ref': 'swagger_schema_extended.json#/definitions/paths'},
    get_dir_path(__file__))


class BaseModelRouteMeta(type):

    def _get_context_values(cls, context):
        session = context['session']
        parameters = context['parameters']
        req_body = parameters['body']
        id_ = parameters['uri_template']
        kwargs = deepcopy(parameters['headers'])
        kwargs.update(parameters['query_string'])
        return session, req_body, id_, kwargs


class BaseModelPostMixinMeta(BaseModelRouteMeta):

    def post_by_body(cls, req, resp):
        cls._insert(req, resp)

    def _insert(cls, req, resp, with_update=False):
        session, req_body, id_, kwargs = cls._get_context_values(req.context)

        if with_update:
            if isinstance(req_body, list):
                [cls._update_dict(obj, id_) for obj in req_body]
            elif isinstance(req_body, dict):
                cls._update_dict(req_body, id_)

        resp_body = cls.insert(session, req_body, **kwargs)
        resp_body = resp_body if isinstance(req_body, list) else resp_body[0]
        resp.body = json.dumps(resp_body)
        resp.status = HTTP_CREATED

    def _update_dict(cls, dict_, other):
        dict_.update({k: v for k, v in other.items() if k not in dict_})

    def post_by_uri_template(cls, req, resp):
        cls._insert(req, resp, with_update=True)


class BaseModelPutMixinMeta(BaseModelPostMixinMeta):

    def put_by_body(cls, req, resp):
        cls._update(req, resp)

    def _update(cls, req, resp):
        session, req_body, _, kwargs = cls._get_context_values(req.context)

        objs = cls.update(session, req_body, **kwargs)

        if objs:
            resp.body = json.dumps(objs)
        else:
            raise HTTPNotFound()

    def put_by_uri_template(cls, req, resp):
        session, req_body, id_, kwargs = cls._get_context_values(req.context)
        req_body_copy = deepcopy(req_body)

        cls._update_dict(req_body, id_)
        objs = cls.update(session, req_body, ids=id_, **kwargs)

        if not objs:
            req_body = req_body_copy

            ambigous_keys = [
                kwa for kwa in id_ if kwa in req_body and req_body[kwa] != id_[kwa]]
            if ambigous_keys:
                body_schema = req.context.get('body_schema')
                raise ValidationError(
                    "Ambiguous value for '{}'".format(
                        "', '".join(ambigous_keys)),
                    instance={'body': req_body, 'uri': id_}, schema=body_schema)

            req.context['parameters']['body'] = req_body
            cls._insert(req, resp, with_update=True)
        else:
            resp.body = json.dumps(objs[0])


class BaseModelPatchMixinMeta(BaseModelPutMixinMeta):

    def patch_by_body(cls, req, resp):
        cls._update(req, resp)

    def patch_by_uri_template(cls, req, resp):
        session, req_body, id_, kwargs = cls._get_context_values(req.context)

        cls._update_dict(req_body, id_)
        objs = cls.update(session, req_body, ids=id_, **kwargs)
        if objs:
            resp.body = json.dumps(objs[0])
        else:
            raise HTTPNotFound()


class BaseModelDeleteMixinMeta(BaseModelRouteMeta):

    def delete_by_body(cls, req, resp):
        session, req_body, _, kwargs = cls._get_context_values(req.context)

        cls.delete(session, req_body, **kwargs)
        resp.status = HTTP_NO_CONTENT

    def delete_by_uri_template(cls, req, resp):
        session, _, id_, kwargs = cls._get_context_values(req.context)

        cls.delete(session, id_, **kwargs)
        resp.status = HTTP_NO_CONTENT


class BaseModelGetMixinMeta(BaseModelRouteMeta):

    def get_by_body(cls, req, resp):
        session, req_body, _, kwargs = cls._get_context_values(req.context)

        if req_body:
            resp_body = cls.get(session, req_body, **kwargs)
        else:
            resp_body = cls.get(session, **kwargs)

        if not resp_body:
            raise HTTPNotFound()

        resp.body = json.dumps(resp_body)

    def get_by_uri_template(cls, req, resp):
        session, _, id_, kwargs = cls._get_context_values(req.context)

        resp_body = cls.get(session, id_, **kwargs)
        if not resp_body:
            raise HTTPNotFound()

        resp.body = json.dumps(resp_body[0])

    def get_schema(cls, req, resp):
        resp.body = json.dumps(cls.__schema__)


class ModelBaseRoutesMixinMeta(type):

    def __init__(cls, name, bases, attributes):
        cls.__routes__ = set()
        cls.__key__ = getattr(cls, '__key__', cls.__name__.replace('Model', '').lower())
        schema = getattr(cls, '__schema__', None)

        if schema:
            SWAGGER_VALIDATOR.validate(schema)
            cls._build_routes_from_schema(schema)

    def get_module_path(cls):
        return get_module_path(cls)

    def _build_routes_from_schema(cls, schema):
        for uri_template in schema:
            all_methods_parameters = schema[uri_template].get('parameters', [])
            for method_name in HTTP_METHODS:
                method = schema[uri_template].get(method_name.lower())
                if method:
                    operation_id = method['operationId']
                    try:
                        action = getattr(cls, operation_id)
                    except AttributeError:
                        raise ModelBaseError("'operationId' '{}' was not found".format(operation_id))

                    definitions = schema.get('definitions')
                    route = Route(uri_template, method_name, operation_id,
                                    method, all_methods_parameters, definitions, cls)
                    cls.__routes__.add(route)

        schema_route = \
            Route(cls.build_schema_uri_template(), 'GET', 'get_schema', {}, [], {}, cls)
        cls.__routes__.add(schema_route)

        routes = defaultdict(set)
        for route in cls.__routes__:
            routes[route.uri_template].add(route.method_name)

        for uri_template, methods_names in routes.items():
            if not 'OPTIONS' in methods_names:
                route = Route(uri_template, 'OPTIONS',
                    create_default_options(methods_names), {}, [], {}, cls)

    def build_schema_uri_template(cls):
        return '/' + cls.__key__ + '/_schema/'


class ModelBaseMeta(
        BaseModelPatchMixinMeta,
        BaseModelDeleteMixinMeta,
        BaseModelGetMixinMeta,
        ModelBaseRoutesMixinMeta):

    def _to_list(cls, objs):
        return objs if isinstance(objs, list) else [objs]

    def get_filters_names_key(cls):
        return cls.__key__ + '_filters_names'

    def get_key(cls, filters_names=None):
        if not filters_names or filters_names == cls.__key__:
            return cls.__key__

        return '{}_{}'.format(cls.__key__, filters_names)


class ModelBase(object):
    __session__ = None

    def get_key(self, id_names=None):
        return str(self.get_ids_values(id_names))
