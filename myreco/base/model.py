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
from sqlalchemy.orm.properties import RelationshipProperty
from sqlalchemy.orm.attributes import InstrumentedAttribute
from sqlalchemy import or_
from copy import deepcopy

from myreco.exceptions import ModelBaseError

import json


MODEL_BASE_CLASS_NAME = 'ModelBase'


class _SQLAlchemyModelMeta(DeclarativeMeta):
    def __init__(cls, name, bases_classes, attributes):
        DeclarativeMeta.__init__(cls, name, bases_classes, attributes)

        if name != MODEL_BASE_CLASS_NAME:
            if not hasattr(cls, 'id_name'):
                cls.id_name = 'id'
            cls.get_model_id()

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
            cls.tablename = str(cls.__table__.name)
            cls.todict_schema = {}
            base_class.all_models.add(cls)

            cls._build_backrefs_for_all_models(base_class.all_models)
        else:
            cls.all_models = set()

    def get_model_id(cls):
        return getattr(cls, cls.id_name)

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
        if isinstance(attr, InstrumentedAttribute) and isinstance(attr.prop, RelationshipProperty):
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

    def insert(cls, session, objs, commit=True, todict=True):
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

        if todict:
            new_insts = [inst.todict() for inst in new_insts]

        return list(new_insts)

    def _to_list(cls, objs):
        return objs if isinstance(objs, list) else [objs]

    def _update_instance(cls, session, instance, values, input_):
        for attr_name in set(values.keys()):
            relationship = cls._get_relationship(attr_name)

            if relationship is not None:
                rel_model = cls.get_model_from_rel(relationship)
                insts_to_update = dict()
                insts_to_delete = dict()
                insts_to_remove = dict()
                rels_values = values.pop(attr_name)

                if relationship.prop.uselist is not True:
                    rels_values = [rels_values]

                rel_insts = cls._build_relationship_instances(
                    session, rel_model, attr_name, rels_values, instance)

                for rel_values in rels_values:
                    to_update = rel_values.pop('_update', None)
                    to_delete = rel_values.pop('_delete', None)
                    to_remove = rel_values.pop('_remove', None)
                    rel_id = rel_values.get(rel_model.id_name)
                    op_count = [op for op in (to_update, to_delete, to_remove) if op is not None]
                    no_rel_insts_message = "Can't execute nested '_{}'"

                    if len(op_count) > 1:
                        raise ModelBaseError(
                            "ambiguous operations 'update'"\
                            ", 'delete' or 'remove'", input_)

                    if to_update:
                        if not rel_insts:
                            raise ModelBaseError(no_rel_insts_message.format('update'), input_)

                        cls._exec_update_on_instance(
                            session, rel_model, attr_name, relationship, rel_id,
                            rel_values, rel_insts, instance, values, input_)

                    elif to_delete:
                        if not rel_insts:
                            raise ModelBaseError(no_rel_insts_message.format('delete'), input_)

                        rel_model.delete(session, rel_id, commit=False)
                        insts_to_delete[rel_id] = rel_values

                    elif to_remove:
                        if not rel_insts:
                            raise ModelBaseError(no_rel_insts_message.format('remove'), input_)

                        cls._exec_remove_on_instance(
                            rel_model, attr_name, relationship,
                            rel_id, rel_insts, instance, values, input_)
                    else:
                        cls._exec_insert_on_instance(
                            session, rel_model, attr_name, relationship, rel_values, values)

        instance.update_(**values)

    def _build_relationship_instances(cls, session, rel_model, attr_name, rels_values, instance):
        if not instance in session.identity_map.values():
            ids_to_get = cls._get_ids_from_rels_values(rel_model, rels_values)
            rel_insts = rel_model.get(session, ids_to_get, todict=False) if ids_to_get else []
        else:
            rel_insts = getattr(instance, attr_name)
            if not rel_insts:
                ids_to_get = cls._get_ids_from_rels_values(rel_model, rels_values)
                rel_insts = rel_model.get(session, ids_to_get, todict=False)

        return rel_insts

    def _get_ids_from_rels_values(cls, rel_model, rels_values):
        return [rel_value.get(rel_model.id_name) for rel_value in rels_values \
            if rel_value.get(rel_model.id_name) is not None]

    def _exec_update_on_instance(
            cls, session, rel_model, attr_name, relationship,
            rel_id, rel_values, rel_insts, instance, values, input_):
        if relationship.prop.uselist is True:
            for rel_inst in rel_insts:
                if rel_inst.get_id() == rel_id:
                    rel_model._update_instance(session, rel_inst, rel_values, input_)
                    setattr(instance, attr_name, rel_insts)
                    break

        else:
            rel_model._update_instance(session, rel_insts[0], rel_values, input_)
            setattr(instance, attr_name, rel_insts[0])

    def _exec_remove_on_instance(
            cls, rel_model, attr_name, relationship,
            rel_id, rel_insts, instance, values, input_):
        rel_to_remove = None
        if relationship.prop.uselist is True:
            for rel_inst in rel_insts:
                if rel_inst.get_id() == rel_id:
                    rel_to_remove = rel_inst
                    break

            if rel_to_remove is not None:
                rel_insts.remove(rel_to_remove)

            else:
                raise ModelBaseError(
                    "can't remove model '{}' on column '{}' with value '{}'".format(
                        rel_model.tablename, rel_model.id_name, rel_id
                    ), input_)

        else:
            setattr(instance, attr_name, None)

    def _exec_insert_on_instance(
            cls, session, rel_model, attr_name,
            relationship, rel_values, values):
        inserted_objs = rel_model.insert(
                session, rel_values, commit=False, todict=False)
        if relationship.prop.uselist is not True:
            values[attr_name] = inserted_objs[0]
        else:
            rels_ = values.get(attr_name, [])
            rels_.extend(inserted_objs)
            values[attr_name] = rels_

    def update(cls, session, objs):
        input_ = deepcopy(objs)
        objs = cls._to_list(objs)
        ids_objs_map = {obj.get(cls.id_name): obj for obj in objs}
        insts = cls.get(session, list(ids_objs_map.keys()), todict=False)
        id_insts_map = {inst.get_id(): inst for inst in insts}

        for id_, inst in id_insts_map.items():
            cls._update_instance(session, inst, ids_objs_map[id_], input_)

        session.commit()

        return list(id_insts_map.keys())

    def delete(cls, session, ids, commit=True):
        ids = cls._to_list(ids)
        for id_ in ids:
            session.query(cls).filter(cls.get_model_id() == id_).delete()

        if commit:
            session.commit()

    def get(cls, session, ids=None, limit=None, offset=None, todict=True):
        if (ids is not None) and (limit is not None or offset is not None):
            raise ModelBaseError(
                "'get' method can't be called with 'ids' and with 'offset' or 'limit'",
                {'ids': ids, 'limit': limit, 'offset': offset})

        if ids is None:
            query = session.query(cls)

            if limit is not None:
                query = query.limit(limit)

            if offset is not None:
                query = query.offset(offset)

            return [each.todict() for each in query.all()] if todict else query.all()

        return cls._get_many(session, ids, todict=todict)

    def _get_many(cls, session, ids, todict=True):
        ids = ids if isinstance(ids, list) else [ids]

        if not todict or session.redis_bind is None:
            filters_ids = cls._build_filters_by_ids(ids)
            return session.query(cls).filter(filters_ids).all()

        model_redis_key = session.build_model_redis_key(cls)
        ids_redis_keys = [str(id_) for id_ in ids]
        objs = session.redis_bind.hmget(model_redis_key, ids_redis_keys)
        ids = [id_ for id_, obj in zip(ids, objs) if obj is None]
        objs = [json.loads(obj) for obj in objs if obj is not None]

        if ids:
            filters_ids = cls._build_filters_by_ids(ids)
            instances = session.query(cls).filter(filters_ids).all()
            no_cached_map = {each.get_id(): each.todict() for each in instances}
            session.redis_bind.hmset(model_redis_key, no_cached_map)
            objs.extend(no_cached_map.values())

        return objs

    def _build_filters_by_ids(cls, ids):
        if len(ids) == 1:
            return cls._get_obj_i_comparison(0, ids)

        comparison1 = cls._get_obj_i_comparison(0, ids)
        comparison2 = cls._get_obj_i_comparison(1, ids)
        or_clause = or_(comparison1, comparison2)

        for i in range(2, len(ids)):
            comparison = cls._get_obj_i_comparison(i, ids)
            or_clause = or_(or_clause, comparison)

        return or_clause

    def _get_obj_i_comparison(cls, i, ids):
        return (cls.get_model_id() == ids[i])


class _SQLAlchemyModel(object):
    def get_id(self):
        return getattr(self, type(self).id_name)

    def get_related(self, session):
        related = set()
        cls = type(self)

        for relationship in cls.relationships:
            related_model_insts = self._get_related_model_insts(session, relationship)
            related.update(related_model_insts)

        for relationship in cls.backrefs:
            related_model_insts = self._get_related_model_insts(session, relationship, parent=True)
            related.update(related_model_insts)

        return related

    def _get_related_model_insts(self, session, relationship, parent=False):
        cls = type(self)
        rel_model = cls.get_model_from_rel(relationship, parent=parent)

        result = set(session.query(rel_model).join(relationship).filter(
            cls.get_model_id() == self.get_id()).all())
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
                rel_schema = rel_schema if isinstance(rel_schema, dict) else None
                attr = getattr(self, rel.prop.key)
                relationships = None
                if rel.prop.uselist is True:
                    relationships = [rel.todict(rel_schema) for rel in attr]
                elif attr is not None:
                    relationships = attr.todict(rel_schema)

                dict_inst[rel_name] = relationships

    def update_(self, **kwargs):
        type(self).__init__(self, **kwargs)


def model_base_builder(
        bind=None, metadata=None, mapper=None,
        constructor=_declarative_constructor,
        class_registry=None):
    return declarative_base(
        name=MODEL_BASE_CLASS_NAME, metaclass=_SQLAlchemyModelMeta,
        cls=_SQLAlchemyModel, bind=bind, metadata=metadata,
        mapper=mapper, constructor=constructor)
