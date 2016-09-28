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


from myreco.exceptions import ModelBaseError, JSONError
from falcon.errors import HTTPNotFound, HTTPMethodNotAllowed
from falcon import HTTP_CREATED
from jsonschema import RefResolver, Draft4Validator
from collections import defaultdict
from copy import deepcopy
from importlib import import_module
import json
import os.path


class BaseModelOperationMeta(type):
    def _get_context_values(cls, context):
        session = context['session']
        req_body = context['parameters']['body']
        id_ = context['parameters']['uri_template']
        kwargs = deepcopy(context['parameters']['headers'])
        kwargs.update(context['parameters']['query_string'])

        return session, req_body, id_, kwargs


class BaseModelPostMixinMeta(BaseModelOperationMeta):

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
                kwa for kwa in id_ if kwa in req_body and str(req_body[kwa]) != id_[kwa]]
            if ambigous_keys:
                raise ValidationError(
                    "Ambiguous value for '{}'".format(
                        "', '".join(ambigous_keys)),
                    instance={'body': req_body, 'uri': id_}, schema=cls._body_validator.schema)

            req.context['parameters']['body'] = req_body
            cls._insert(req, resp, with_update=True)
        else:
            resp.body = json.dumps(objs[0])


class BaseModelPatchMixinMeta(BaseModelPutMixinMeta):

    def patch_by_uri_template(cls, req, resp):
        session, req_body, id_, kwargs = cls._get_context_values(req.context)

        cls._update_dict(req_body, id_)
        objs = cls.update(session, req_body, ids=id_, **kwargs)
        if objs:
            resp.body = json.dumps(objs[0])
        else:
            raise HTTPNotFound()


class BaseModelDeleteMixinMeta(BaseModelOperationMeta):

    def delete_by_body(cls, req, resp):
        session, req_body, _, kwargs = cls._get_context_values(req.context)

        cls.delete(session, req_body, **kwargs)
        resp.status = HTTP_NO_CONTENT

    def delete_by_uri_template(cls, req, resp):
        session, _, id_, kwargs = cls._get_context_values(req.context)

        cls.delete(session, id_, **kwargs)
        resp.status = HTTP_NO_CONTENT


class BaseModelGetMixinMeta(BaseModelOperationMeta):

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


class URISchemaHandler(object):

    def __init__(self, schemas_path):
        self._schemas_path = schemas_path

    def __call__(self, uri):
        schema_filename = os.path.join(self._schemas_path, uri.replace('schema:', ''))
        with open(schema_filename) as json_schema_file:
            return json.load(json_schema_file)


def _get_dir_path(filename):
    return os.path.dirname(os.path.abspath(filename))


def _get_model_schema(filename):
    return json.load(open(os.path.join(_get_dir_path(filename), 'schema.json')))


PATHS_SCHEMA = {'$ref': 'swagger_schema_extended.json#/definitions/paths'}
SCHEMAS_HANDLERS = {'': URISchemaHandler(_get_dir_path(__file__))}
RESOLVER = RefResolver.from_schema(PATHS_SCHEMA, handlers=SCHEMAS_HANDLERS)
SWAGGER_VALIDATOR = Draft4Validator(PATHS_SCHEMA, resolver=RESOLVER)
HTTP_METHODS = ('post', 'put', 'patch', 'delete', 'get', 'options', 'head')
CAST = {
    'string': str,
    'number': float,
    'boolean': bool,
    'integer': int,
    'array': list
}


class Operation(object):

    def __init__(self, action, schema, all_methods_parameters, definitions, model_dir):
        self._action = action
        self._body_validator = None
        self._uri_template_validator = None
        self._query_string_validator = None
        self._headers_validator = None
        self._model_dir = model_dir

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

                self._body_validator = self._build_validator(body_schema)

            elif parameter['in'] == 'path':
                self._set_parameter_on_schema(parameter, uri_template_schema)

            elif parameter['in'] == 'query':
                self._set_parameter_on_schema(parameter, query_string_schema)

            elif parameter['in'] == 'header':
                self._set_parameter_on_schema(parameter, headers_schema)

        if uri_template_schema['properties']:
            self._uri_template_validator = self._build_validator(uri_template_schema)

        if query_string_schema['properties']:
            self._query_string_validator = self._build_validator(query_string_schema)

        if headers_schema['properties']:
            self._headers_validator = self._build_validator(headers_schema)

    def _build_default_schema(self):
        return {'type': 'object', 'required': [], 'properties': {}}

    def _set_parameter_on_schema(self, parameter, schema):
        name = parameter['name']
        property_ = {'type': parameter['type']}

        if parameter['type'] == 'array':
            items = parameter.get('items', {})
            if items:
                property_['items'] = items

        if parameter.get('required'):
            schema['required'].append(name)

        schema['properties'][name] = property_

    def _build_validator(self, schema):
        resolver = RefResolver.from_schema(schema, handlers={'': URISchemaHandler(self._model_dir)})
        return Draft4Validator(schema, resolver=resolver)

    def __call__(self, req, resp, **kwargs):
        body_params = self._build_body_params(req)
        query_string_params = self._build_params_from_schema(self._query_string_validator, req.params)
        uri_template_params = self._build_params_from_schema(self._uri_template_validator, kwargs)
        headers_params = self._build_params_from_schema(self._headers_validator, req, 'headers')

        req.context['parameters'] = {
            'query_string': query_string_params,
            'uri_template': uri_template_params,
            'headers': headers_params,
            'body': body_params
        }
        self._action(req, resp)

    def _build_body_params(self, req):
        if req.content_length and (req.content_type is None or 'application/json' in req.content_type):
            body = req.stream.read().decode()
            try:
                body = json.loads(body)
            except ValueError as error:
                raise JSONError(*error.args, input_=body)

            if self._body_validator:
                self._body_validator.validate(body)

            return body

        return req.stream

    def _build_params_from_schema(self, validator, kwargs, type_=None):
        if validator:
            params = {}
            for param_name, prop in validator.schema['properties'].items():
                if type_ == 'headers':
                    param = kwargs.get_header(param_name)
                else:
                    param = kwargs.get(param_name)

                if param:
                    if prop['type'] == 'array' and not isinstance(param, list):
                        param = param.split(',')

                    if prop['type'] == 'array' and prop.get('items', {}).get('type'):
                        array_type = CAST[prop['items']['type']]
                        params[param_name] = [array_type(param_) for param_ in param]
                    else:
                        params[param_name] = CAST[prop['type']](param)

            validator.validate(params)
            return params
        elif type_ == 'headers':
            return {}
        else:
            return kwargs


class ModelBaseRoutesMixinMeta(type):

    def __init__(cls, name, bases, attributes):
        cls.__routes__ = defaultdict(dict)
        cls.__key__ = getattr(cls, '__key__', cls.__name__.replace('Model', '').lower())
        cls.__allowed_methods__ = set()
        schema = attributes.get('__schema__')

        if schema:
            SWAGGER_VALIDATOR.validate(schema)
            cls._build_routes_from_schema(schema)

    def get_module_path(cls):
        module_filename = import_module(cls.__module__).__file__
        return _get_dir_path(module_filename)

    def _build_routes_from_schema(cls, schema):
        for uri_template in schema:
            all_methods_parameters = schema[uri_template].get('parameters', [])
            for method_name in HTTP_METHODS:
                method = schema[uri_template].get(method_name)
                if method:
                    operation_id = method['operationId']
                    try:
                        action = getattr(cls, operation_id)
                    except AttributeError:
                        raise ModelBaseError("'operationId' '{}' was not found".format(operation_id))

                    definitions = schema.get('definitions')
                    operation = Operation(action, method, all_methods_parameters, definitions, cls.get_module_path())
                    cls.__routes__[uri_template][method_name] = operation
                    cls.__allowed_methods__.add(method_name.upper())

        cls.__routes__[cls._build_schema_uri_template()]['get'] = cls.get_schema

    def _build_schema_uri_template(cls):
        return '/' + cls.__key__ + '/_schema/'

    def on_post(cls, req, resp, **kwargs):
        cls._route(req, resp, **kwargs)

    def _route(cls, req, resp, **kwargs):
        cls._raise_not_found(req, resp, **kwargs)
        cls._raise_method_not_allowed(req, resp, **kwargs)
        cls._add_schema_link(req, resp, **kwargs)
        cls.__routes__[req.uri_template][req.method.lower()](req, resp, **kwargs)

    def _raise_not_found(cls, req, resp, **kwargs):
        if not req.uri_template in cls.__routes__:
            raise HTTPNotFound()

    def _raise_method_not_allowed(cls, req, resp, **kwargs):
        if not req.method.lower() in cls.__routes__[req.uri_template]:
            raise HTTPMethodNotAllowed(cls.__allowed_methods__)

    def _add_schema_link(cls, req, resp, **kwargs):
        if hasattr(cls, '__schema__'):
            resp.add_link(cls._build_schema_uri_template(), 'schema')

    def on_put(cls, req, resp, **kwargs):
        cls._route(req, resp, **kwargs)

    def on_patch(cls, req, resp, **kwargs):
        cls._route(req, resp, **kwargs)

    def on_delete(cls, req, resp, **kwargs):
        cls._route(req, resp, **kwargs)

    def on_get(cls, req, resp, **kwargs):
        cls._route(req, resp, **kwargs)

    def on_options(cls, req, resp, **kwargs):
        cls._route(req, resp, **kwargs)

    def on_head(cls, req, resp, **kwargs):
        cls._route(req, resp, **kwargs)


class ModelBaseMeta(
        BaseModelPatchMixinMeta,
        BaseModelDeleteMixinMeta,
        BaseModelGetMixinMeta,
        ModelBaseRoutesMixinMeta):

    def _to_list(cls, objs):
        return objs if isinstance(objs, list) else [objs]


class ModelBase(object):
    def get_key(self):
        return str(self.get_ids_values())
