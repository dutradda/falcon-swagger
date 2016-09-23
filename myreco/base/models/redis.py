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
from myreco.base.models.base import ModelBaseMeta, ModelBase, ModelBuilderBaseMeta
from myreco.exceptions import ModelBaseError
from jsonschema import Draft4Validator
from collections import defaultdict, OrderedDict
from copy import deepcopy
from types import MethodType
import json
import msgpack


class RedisRoutesBuilder(RoutesBuilderBase):

    @classmethod
    def _build_default_routes(cls, model, routes, auth_hook):
        new_routes = set()
        if routes is None:
            return new_routes

        for route in routes:
            new_routes.add(cls._build_route(model, route, auth_hook))

        return new_routes

    @classmethod
    def _build_route(cls, model, route, auth_hook):
        validator = None
        input_schema = route.get('input_schema')
        output_schema = route.get('output_schema')
        method = route['method']['name']
        uri_template = model.__api_prefix__ + route['uri_template'].strip('/')
        validator = None
        hooks = {auth_hook} if auth_hook else None

        if input_schema:
            Draft4Validator.check_schema(input_schema)
            validator = Draft4Validator(input_schema)

        action = cls._get_action(uri_template, method)
        return Route(uri_template, method, action, validator, output_schema, hooks=hooks)


class RedisModelMeta(ModelBaseMeta):
    CHUNKS = 100

    def insert(cls, session, objs):
        input_ = deepcopy(objs)
        objs = cls._to_list(objs)
        ids_objs_map = dict()

        for obj in objs:
            obj = cls(obj)
            obj_key = obj.get_key()
            ids_objs_map[obj_key] = msgpack.dumps(obj)

            if len(ids_objs_map) == cls.CHUNKS:
                session.bind.hmset(cls.__key__, ids_objs_map)
                ids_objs_map = dict()

        if ids_objs_map:
            session.bind.hmset(cls.__key__, ids_objs_map)

        return objs

    def update(cls, session, objs, ids=None):
        input_ = deepcopy(objs)

        objs = cls._to_list(objs)
        if ids:
            ids = cls._to_list(ids)
            ids_keys = ids[0].keys()
            keys = set([cls._build_key(id_) for id_ in ids])
            keys_objs_map = OrderedDict()
            for obj in objs:
                obj_ids = cls(obj).get_ids_map(ids_keys)
                if obj_ids in ids:
                    keys_objs_map[cls._build_key(obj_ids)] = obj

        else:
            keys_objs_map = OrderedDict([(cls(obj).get_key(), obj) for obj in objs])
            keys = set(keys_objs_map.keys())

        keys.difference_update(set(session.bind.hkeys(cls.__key__)))
        keys.intersection_update(keys)
        invalid_keys = keys

        for key in invalid_keys:
            keys_objs_map.pop(key, None)

        if len(keys_objs_map) > cls.CHUNKS:
            return cls.insert(session, list(keys_objs_map.values()))

        elif keys_objs_map:
            set_map = OrderedDict()
            for key in keys_objs_map:
                set_map[key] = msgpack.dumps(keys_objs_map[key])

            session.bind.hmset(cls.__key__, set_map)

        return list(keys_objs_map.values())

    def _build_key(cls, id_):
        return str(tuple(sorted(id_.values())))

    def delete(cls, session, ids):
        keys = [cls.get_key(id_) for id_ in cls._to_list(ids)]
        cls.hdel(cls.__key__, *keys)

    def get(cls, session, ids=None, limit=None, offset=None):
        cls._raises_ids_limit_offset_error(ids, limit, offset)

        if ids is None and limit is None and offset is None:
            return cls._unpack_objs(session.bind.hgetall(cls.__key__))
        elif ids is None:
            keys = session.bind.hkeys(cls.__key__)
            return cls._unpack_objs(session.bind.hmget(cls.__key__, *keys[offset:limit]))
        else:
            ids = [cls._build_key(id_) for id_ in cls._to_list(ids)]
            return cls._unpack_objs(session.bind.hmget(cls.__key__, *ids))

    def _unpack_objs(cls, objs):
        return [msgpack.loads(obj, enconding='utf-8') for obj in objs]


class _RedisModel(dict, ModelBase):
    __routes_builder__ = RedisRoutesBuilder

    def get_ids_values(self):
        ids_names = sorted(type(self).__ids_names__)
        return tuple([self.get(id_name) for id_name in ids_names])

    def get_ids_map(self, keys=None):
        if keys is None:
            keys = type(self).__ids_names__

        keys = sorted(keys)
        return {key: self[key] for key in keys}


class RedisModelsBuilder(metaclass=ModelBuilderBaseMeta):

    def __new__(cls, models_types, api_prefix=None):
        return cls._build_models(models_types, api_prefix)

    @classmethod
    def _build_models(cls, models_types, api_prefix):
        models = set()
        for model_type in models_types:
            models.add(cls._build_model(model_type, api_prefix))
        return models

    @classmethod
    def _build_model(cls, model_type, api_prefix):
        cls._set_api_prefix(api_prefix)

        name = model_type['name'].capitalize() + 'Model'
        attributes = {
            '__key__': model_type['name'],
            '__routes__': model_type.get('routes', []),
            '__ids_names__': tuple(model_type['id_names'])
        }
        model = RedisModelMeta(name, (_RedisModel,), attributes)
        model.update = MethodType(RedisModelMeta.update, model)
        model.update_ = MethodType(dict.update, model)
        return model
