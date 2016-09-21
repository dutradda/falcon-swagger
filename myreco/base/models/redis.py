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


from myreco.base.routes import Route, RoutesBuilderBase
from myreco.base.models.base import ModelBaseMeta
from myreco.exceptions import ModelBaseError
from jsonschema import Draft4Validator
from collections import defaultdict
import json


class RedisRoutesBuilderBase(RoutesBuilderBase):

    @classmethod
    def _build_default_routes(cls, model, auth_hook):
        models = set()
        for model_type in models_types:
            uri_template = '{}{}'.format(uri_prefix, model_type['name'])
            routes = set()

            for route in model_type['routes']:
                routes.add(cls._build_route(route))

            models.add(cls._build_model(model_type['name'], routes))

        return models

    @classmethod
    def _build_route(cls, route):
        validator = None
        if route.get('input_schema'):
            validator = Draft4Validator(route['input_schema'])

        action = cls._get_action(route['uri_template'], route['method']['name'])
        return Route(uri_template, method, action, validator, output_schema)


class RedisModelMeta(ModelBaseMeta):
    pass


class _RedisModel(object):
    __api_prefix__ = '/'


class RedisModelsBuilder(object):

    def __new__(cls, models_types, api_prefix='/'):
        return cls._build_models(models_types, api_prefix)

    def _build_models(cls, models_types, api_prefix):
        models = set()
        for model_type in models_types:
            models.add(cls._build_model(model_type['name'], routes, api_prefix))
        return models

    @classmethod
    def _build_model(cls, model_type, routes, api_prefix):
        if api_prefix is not None:
            if not api_prefix.endswith('/') or not api_prefix.startswith('/'):
                raise ModelBaseError("'api_prefix' must ends and starts with a '/'")

        name = model_type['name'].capitalize() + 'Model'
        attributes = {
            'key': model_type['name'],
            '__routes__': routes,
            '__ids_names__': tuple(json.loads(model_type['id_names_json']))
        }
        return RedisModelMeta(name, (_RedisModel,), attributes)
