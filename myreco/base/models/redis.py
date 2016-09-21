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


from myreco.base.routes import Route
from jsonschema import Draft4Validator
from collections import defaultdict
from myreco.base.models.base import ModelBaseMeta

import json


class RedisModelMeta(ModelBaseMeta):
    pass


class _RedisModelActionsMeta(type):

    def post_action(cls, req, resp, **kwargs):
        pass

    def put_action(cls, req, resp, **kwargs):
        pass

    def patch_action(cls, req, resp, **kwargs):
        pass

    def delete_action(cls, req, resp, **kwargs):
        pass

    def get_action(cls, req, resp, **kwargs):
        pass


class RedisModelActions(metaclass=_RedisModelActionsMeta):
    pass


class RedisModelsBuilder(object):

    def __new__(cls, models_types, actions_class=RedisModelActions, uri_prefix='/'):
        return cls._build_models(models_types, actions_class, uri_prefix)

    @classmethod
    def _build_models(cls, models_types, actions_class, uri_prefix):
        models = set()
        for model_type in models_types:
            uri_template = '{}{}'.format(uri_prefix, model_type['name'])
            method_schemas_map = self._build_method_schemas_map(model_type)
            routes = set()

            for method, schemas in method_schemas_map.items():
                routes.add(cls._build_route(uri_template, method, schemas, actions_class))

            models.add(cls._build_model(model_type['name'], routes))

        return models

    @classmethod
    def _build_model(cls, model_type, routes):
        name = model_type['name'].capitalize() + 'Model'
        attributes = {
            'key': model_type['name'],
            'routes': routes,
            'id_names': tuple(json.loads(model_type['id_names_json']))
        }
        return RedisModelMeta(name, (object,), attributes)

    @classmethod
    def _build_method_schemas_map(cls, model_type):
        method_schemas_map = defaultdict(list)
        for schema in model_type['json_schemas']:
            method = schema['method']['name']
            type_ = schema['type']['name']
            schema_ = schema['schema'] if type_ == 'output' else Draft4Validator(schema[
                                                                                 'schema'])
            method_schemas_map[method].append(schema_)
        return schemas

    @classmethod
    def _build_route(cls, uri_template, method, schemas, actions_class):
        validator = None
        output_schema = None
        for schema in schemas:
            if isinstance(schema, Draft4Validator):
                validator = schema
            else:
                output_schema = schema

        action = getattr(actions_class, '{}_action', format(method.lower()))
        return Route(uri_template, method, action, validator, output_schema)
