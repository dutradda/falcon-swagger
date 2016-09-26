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


from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.ext.declarative.api import DeclarativeMeta
from sqlalchemy.ext.declarative.base import _declarative_constructor
from sqlalchemy.ext.declarative.clsregistry import _class_resolver
from sqlalchemy.orm.properties import RelationshipProperty, ColumnProperty
from sqlalchemy.orm.attributes import InstrumentedAttribute
from sqlalchemy.orm.collections import InstrumentedList
from sqlalchemy import or_, and_
from jsonschema import RefResolver, Draft4Validator
from copy import deepcopy
from collections import OrderedDict
from importlib import import_module
from re import match as re_match, sub as re_sub
from glob import glob

from myreco.exceptions import ModelBaseError
from myreco.base.routes import RoutesBuilderBase, Route
from myreco.base.models.base import ModelBaseMeta, ModelBase, ModelBuilderBaseMeta

import json
import msgpack
import os.path


MODEL_BASE_CLASS_NAME = 'SQLAlchemyRedisModelBase'


class URISchemaHandler(object):

    def __init__(self, schemas_path):
        self._schemas_path = schemas_path

    def __call__(self, uri):
        schema_filename = os.path.join(
            self._schemas_path, uri.replace('schema:', ''))
        with open(schema_filename) as json_schema_file:
            return json.load(json_schema_file)


class SQLAlchemyRedisModelRoutesBuilder(RoutesBuilderBase):

    @classmethod
    def _build_default_routes(cls, model, routes, auth_hook):
        if routes is None:
            routes = set()

        schemas_path = model.get_schemas_path()
        schemas_glob = os.path.join(schemas_path, '*.json')
        schema_regex = r'(([\w\d_-]+)_)?(([\w\d%_-]+)_)?(post|put|patch|delete|get)_(input|output)(_auth)?.json'
        new_routes = dict()

        for json_schema_filename in glob(schemas_glob):
            json_schema_basename = os.path.basename(json_schema_filename)
            match = re_match(schema_regex, json_schema_basename)
            if match:
                route = cls._set_route(new_routes, model, match,
                                       json_schema_filename,
                                       auth_hook)

        routes.update(set(new_routes.values()))
        return routes

    @classmethod
    def _set_route(cls, routes, model, match, json_schema_filename, auth_hook):
        model_name = match.groups()[1]
        uri_template = cls._build_uri(model, match.groups()[3])
        method = match.groups()[4].upper()
        type_ = match.groups()[5]
        auth = match.groups()[6]
        hooks = {auth_hook} if auth and auth_hook else None
        output_schema = None
        validator = None

        if model_name and model_name != model.tablename:
            return

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

    @classmethod
    def _build_uri(cls, model, uri_template_sufix):
        base_uri_template = model.__api_prefix__ + model.tablename
        uri_template_sufix_regex = r'%([\d\w_-]+)%'

        if uri_template_sufix is not None:
            uri_template_sufix = re_sub(
                uri_template_sufix_regex, r'{\1}', uri_template_sufix)
            uri_template_sufix = uri_template_sufix.replace('__', '/')

            return '/'.join((base_uri_template, uri_template_sufix))

        return base_uri_template

    @classmethod
    def _build_validator(cls, schema, model):
        handlers = {'schema': URISchemaHandler(model.get_schemas_path())}
        resolver = RefResolver.from_schema(schema, handlers=handlers)
        Draft4Validator.check_schema(schema)
        return Draft4Validator(schema, resolver=resolver)


class SQLAlchemyModelMeta(DeclarativeMeta, ModelBaseMeta):

    def __init__(cls, name, bases_classes, attributes):
        DeclarativeMeta.__init__(cls, name, bases_classes, attributes)

        if name != MODEL_BASE_CLASS_NAME:
            cls._build_primary_keys()

            base_class = None
            for base in bases_classes:
                if base.__name__ == MODEL_BASE_CLASS_NAME:
                    base_class = base
                    break

            if base_class is None:
                raise ModelBaseError(
                    "'{}' class must inherit from '{}'".format(
                        name, MODEL_BASE_CLASS_NAME))

            cls.backrefs = set()
            cls.relationships = set()
            cls.columns = set(cls.__table__.c)
            cls.tablename = cls.__name__ = cls.__key__ = str(cls.__table__.name)
            cls.todict_schema = {}
            cls.valid_attributes = set()
            base_class.all_models.add(cls)
            cls._build_backrefs_for_all_models(base_class.all_models)

            ModelBaseMeta.__init__(cls, name, bases_classes, attributes)
        else:
            cls.all_models = set()

    def _build_primary_keys(cls):
        primaries_keys = {}

        for attr_name in cls.__dict__:
            primary_key = cls._get_primary_key(attr_name)
            if primary_key:
                primaries_keys[attr_name] = primary_key

        cls.primaries_keys = cls.__ids_names__ = OrderedDict(sorted(primaries_keys.items()))

    def _get_primary_key(cls, attr_name):
        attr = getattr(cls, attr_name)
        if isinstance(attr, InstrumentedAttribute) \
                and isinstance(attr.prop, ColumnProperty) \
                and [col for col in attr.prop.columns if col.primary_key]:
            return attr

    def _build_backrefs_for_all_models(cls, all_models):
        all_relationships = set()

        for model in all_models:
            model._build_relationships()
            all_relationships.update(model.relationships)

        for model in all_models:
            for relationship in all_relationships:
                if model != cls.get_model_from_rel(relationship, all_models, parent=True) and \
                        model == cls.get_model_from_rel(relationship, all_models):
                    model.backrefs.add(relationship)

    def _build_relationships(cls):
        if cls.relationships:
            return

        for attr_name in cls.__dict__:
            relationship = cls._get_relationship(attr_name)
            if relationship:
                cls.relationships.add(relationship)

    def _get_relationship(cls, attr_name):
        attr = getattr(cls, attr_name)
        if isinstance(attr, InstrumentedAttribute):
            cls.valid_attributes.add(attr_name)
            if isinstance(attr.prop, RelationshipProperty):
                return attr

    def get_model_from_rel(cls, relationship, all_models=None, parent=False):
        if parent:
            return relationship.prop.parent.class_

        if isinstance(relationship.prop.argument, _class_resolver):
            if all_models is None:
                return relationship.prop.argument()

            for model in all_models:
                if model.__name__ == relationship.prop.argument.arg:
                    return model

            return

        return relationship.prop.argument

    def insert(cls, session, objs, commit=True, todict=True, **kwargs):
        input_ = deepcopy(objs)
        objs = cls._to_list(objs)
        new_insts = set()

        for obj in objs:
            instance = cls()
            cls._update_instance(session, instance, obj, input_)
            new_insts.add(instance)

        session.add_all(new_insts)

        if commit:
            session.commit()

        return cls._build_todict_list(new_insts) if todict else list(new_insts)

    def _build_todict_list(cls, insts):
        return [inst.todict() for inst in insts]

    def _update_instance(cls, session, instance, values, input_):
        for attr_name in set(values.keys()):
            relationship = cls._get_relationship(attr_name)

            if relationship is not None:
                rel_model = cls.get_model_from_rel(relationship)
                rels_values = values.pop(attr_name)

                if relationship.prop.uselist is not True:
                    rels_values = [rels_values]

                rel_insts = cls._get_instances_from_values(
                    session, rel_model, attr_name, rels_values, instance)

                for rel_values, rel_inst in zip(rels_values, rel_insts):
                    to_update = rel_values.pop('_update', None)
                    to_delete = rel_values.pop('_delete', None)
                    to_remove = rel_values.pop('_remove', None)
                    cls._raise_ambiguous_operations_error(to_update, to_delete, to_remove, input_)
                    if rel_inst is None:
                        cls._raise_nested_operation_error(to_update, to_delete, to_remove, input_)

                    if to_update:
                        cls._exec_update_on_instance(
                            session, rel_model, attr_name, relationship,
                            rel_inst, rel_values, instance, input_)

                    elif to_delete:
                        rel_model.delete(session, rel_inst.get_ids_map(), commit=False)

                    elif to_remove:
                        cls._exec_remove_on_instance(
                            rel_model, attr_name, relationship, rel_inst, instance, input_)

                    else:
                        cls._exec_insert_on_instance(
                            session, rel_model, attr_name, relationship, rel_values, instance)

        instance.update_(**values)

    def _get_instances_from_values(cls, session, rel_model, attr_name, rels_values, instance):
        ids_to_get = cls._get_ids_from_rels_values(rel_model, rels_values)
        if not ids_to_get:
            return []

        rel_model.get(session, ids_to_get, todict=False)
        rels_ints = []
        for rel_ids in ids_to_get:
            rel_inst = rel_model.get(session, rel_ids, todict=False)
            rel_inst = rel_inst[0] if rel_inst else None
            rels_ints.append(rel_inst)

        return rels_ints

    def _get_ids_from_rels_values(cls, rel_model, rels_values):
        ids = []
        for rel_value in rels_values:
            ids_values = rel_model.get_ids_from_values(rel_value)
            ids.append(ids_values)

        return ids

    def get_ids_from_values(cls, values):
        cast = lambda id_name, value: getattr(cls, id_name).type.python_type(value) \
            if value is not None else None
        return {id_name: cast(id_name, values.get(id_name)) for id_name in cls.primaries_keys}

    def _raise_ambiguous_operations_error(cls, to_update, to_delete, to_remove, input_):
        op_count = [op for op in (to_update, to_delete, to_remove) if op is not None]
        if len(op_count) > 1:
            raise ModelBaseError(
                "ambiguous operations 'update'"
                ", 'delete' or 'remove'", input_)

    def _raise_nested_operation_error(cls, to_update, to_delete, to_remove, input_):
        operation = ('update' if to_update else
            ('delete' if to_delete else ('remove' if to_remove else None)))

        if operation is not None:
            no_rel_insts_message = "Can't execute nested '_{}'"
            raise ModelBaseError(no_rel_insts_message.format(operation), input_)

    def _exec_update_on_instance(
            cls, session, rel_model, attr_name, relationship,
            rel_inst, rel_values, instance, input_):
        if relationship.prop.uselist is True:
            rel_model._update_instance(session, rel_inst, rel_values, input_)
            if rel_inst not in getattr(instance, attr_name):
                getattr(instance, attr_name).append(rel_inst)

        else:
            rel_model._update_instance(
                session, rel_inst, rel_values, input_)
            setattr(instance, attr_name, rel_inst)

    def _exec_remove_on_instance(
            cls, rel_model, attr_name, relationship,
            rel_inst, instance, input_):
        if relationship.prop.uselist is True:
            if rel_inst in getattr(instance, attr_name):
                getattr(instance, attr_name).remove(rel_inst)
            else:
                columns_str = ', '.join(rel_model.primaries_keys)
                ids_str = ', '.join([str(id_) for id_ in rel_inst.get_ids_values()])
                error_message = "can't remove model '{}' on column(s) '{}' with value(s) {}"
                error_message = error_message.format(rel_model.tablename, columns_str, ids_str)
                raise ModelBaseError(error_message, input_)
        else:
            setattr(instance, attr_name, None)

    def _exec_insert_on_instance(
            cls, session, rel_model, attr_name,
            relationship, rel_values, instance):
        inserted_objs = rel_model.insert(
            session, rel_values, commit=False, todict=False)
        if relationship.prop.uselist is not True:
            setattr(instance, attr_name, inserted_objs[0])
        else:
            if inserted_objs[0] not in getattr(instance, attr_name):
                getattr(instance, attr_name).append(inserted_objs[0])

    def update(cls, session, objs, commit=True, todict=True, ids=None, **kwargs):
        input_ = deepcopy(objs)

        objs = cls._to_list(objs)
        ids = [cls.get_ids_from_values(
            obj) for obj in objs] if not ids else cls._to_list(ids)

        insts = cls.get(session, ids, todict=False)

        for inst in insts:
            inst.old_redis_key = inst.get_key()

        ids_keys = ids[0].keys()
        id_insts_zip = [(inst.get_ids_map(ids_keys), inst) for inst in insts]

        for id_, inst in id_insts_zip:
            cls._update_instance(session, inst, objs[ids.index(id_)], input_)

        if commit:
            session.commit()

        return cls._build_todict_list(insts) if todict else insts

    def delete(cls, session, ids, commit=True, **kwargs):
        ids = cls._to_list(ids)
        filters = cls.build_filters_by_ids(ids)

        session.query(cls).filter(filters).delete()

        if commit:
            session.commit()

    def build_filters_by_ids(cls, ids):
        if len(ids) == 1:
            return cls._get_obj_i_comparison(ids[0])

        or_clause_args = []
        for i in range(0, len(ids)):
            comparison = cls._get_obj_i_comparison(ids[i])
            or_clause_args.append(comparison)

        return or_(*or_clause_args)

    def _get_obj_i_comparison(cls, pk_attributes):
        if len(pk_attributes) == 1:
            pk_name = [i for i in pk_attributes.keys()][0]
            return cls._build_id_attribute_comparison(pk_name, pk_attributes)

        and_clause_args = []
        for pk_name in pk_attributes:
            comparison = cls._build_id_attribute_comparison(
                pk_name, pk_attributes)
            and_clause_args.append(comparison)

        return and_(*and_clause_args)

    def _build_id_attribute_comparison(cls, pk_name, pk_attributes):
        return getattr(cls, pk_name) == pk_attributes[pk_name]

    def get(cls, session, ids=None, limit=None, offset=None, todict=True, **kwargs):
        if ids is None:
            query = session.query(cls)

            if limit is not None:
                query = query.limit(limit)

            if offset is not None:
                query = query.offset(offset)

            return cls._build_todict_list(query.all()) if todict else query.all()

        if limit is not None and offset is not None:
            limit += offset

        ids = cls._to_list(ids)
        return cls._get_many(session, ids[offset:limit], todict=todict)

    def _get_many(cls, session, ids, todict=True):
        if not todict or session.redis_bind is None:
            filters = cls.build_filters_by_ids(ids)
            insts = session.query(cls).filter(filters).all()
            if todict:
                return [inst.todict() for inst in insts]
            else:
                return insts

        model_redis_key = cls.__key__
        ids_redis_keys = [str(tuple(sorted(id_.values()))) for id_ in ids]
        objs = session.redis_bind.hmget(model_redis_key, ids_redis_keys)
        ids_not_cached = [id_ for i, (id_, obj) in enumerate(zip(ids, objs)) if obj is None]
        objs = [msgpack.loads(obj, encoding='utf-8') for obj in objs if obj is not None]

        if ids_not_cached:
            filters = cls.build_filters_by_ids(ids_not_cached)
            instances = session.query(cls).filter(filters).all()
            items_to_set = {
                inst.get_key(): msgpack.dumps(inst.todict()) for inst in instances}
            session.redis_bind.hmset(model_redis_key, items_to_set)

            for inst in instances:
                inst_ids = inst.get_ids_map()
                index = ids_not_cached.index(inst_ids)
                objs.insert(index, inst.todict())

        return objs

    def get_schemas_path(cls):
        module_filename = import_module(cls.__module__).__file__
        module_path = os.path.dirname(os.path.abspath(module_filename))
        return os.path.join(module_path, 'schemas')


class _SQLAlchemyModel(ModelBase):
    __routes_builder__ = SQLAlchemyRedisModelRoutesBuilder

    def get_ids_values(self):
        ids_names = sorted(type(self).__ids_names__)
        return tuple([getattr(self, id_name) for id_name in ids_names])

    def get_ids_map(self, keys=None):
        if keys is None:
            keys = type(self).primaries_keys.keys()

        pk_names = sorted(keys)
        return {id_name: getattr(self, id_name) for id_name in pk_names}

    def get_related(self, session):
        related = set()
        cls = type(self)
        for relationship in cls.backrefs:
            related_model_insts = self._get_related_model_insts(
                session, relationship, parent=True)
            related.update(related_model_insts)

        return related

    def _get_related_model_insts(self, session, relationship, parent=False):
        cls = type(self)
        rel_model = cls.get_model_from_rel(relationship, parent=parent)

        filters = cls.build_filters_by_ids([self.get_ids_map()])
        result = set(session.query(rel_model).join(
            relationship).filter(filters).all())
        return result

    def todict(self, schema=None):
        dict_inst = dict()
        if schema is None:
            schema = type(self).todict_schema

        self._todict_columns(dict_inst, schema)
        self._todict_relationships(dict_inst, schema)

        return dict_inst

    def _todict_columns(self, dict_inst, schema):
        for col in type(self).columns:
            col_name = str(col.name)
            if self._attribute_in_schema(col_name, schema):
                dict_inst[col_name] = getattr(self, col_name)

    def _attribute_in_schema(self, attr_name, schema):
        return (attr_name in schema and schema[attr_name]) or (not attr_name in schema)

    def _todict_relationships(self, dict_inst, schema):
        for rel in type(self).relationships:
            rel_name = rel.key
            if self._attribute_in_schema(rel_name, schema):
                rel_schema = schema.get(rel_name)
                rel_schema = rel_schema if isinstance(
                    rel_schema, dict) else None
                attr = getattr(self, rel.prop.key)
                relationships = None
                if rel.prop.uselist is True:
                    relationships = [rel.todict(rel_schema) for rel in attr]
                elif attr is not None:
                    relationships = attr.todict(rel_schema)

                dict_inst[rel_name] = relationships

    def update_(self, **kwargs):
        type(self).__init__(self, **kwargs)


class SQLAlchemyRedisModelBuilder(metaclass=ModelBuilderBaseMeta):

    def __new__(cls, bind=None, metadata=None, mapper=None,
            constructor=_declarative_constructor,
            class_registry=None, api_prefix=None):
        cls._set_api_prefix(api_prefix)
        return declarative_base(
            name=MODEL_BASE_CLASS_NAME, metaclass=SQLAlchemyModelMeta,
            cls=_SQLAlchemyModel, bind=bind, metadata=metadata,
            mapper=mapper, constructor=constructor)


SQLAlchemyRedisModelBase = SQLAlchemyRedisModelBuilder()
