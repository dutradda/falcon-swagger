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


from sqlalchemy.ext.declarative.api import DeclarativeMeta as DeclarativeMeta
from sqlalchemy.ext.declarative.clsregistry import (_class_resolver, _MultipleClassMarker)
from sqlalchemy.sql.base import ImmutableColumnCollection
from sqlalchemy.orm.properties import RelationshipProperty
from sqlalchemy.orm.attributes import InstrumentedAttribute
from sqlalchemy.orm.collections import InstrumentedList
from sqlalchemy.sql.expression import or_
from sqlalchemy.exc import InvalidRequestError

from weakref import WeakValueDictionary

from myreco.base.models.base import MODEL_BASE_CLASS_NAME


class SQLAlchemyModelMeta(DeclarativeMeta):
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

            cls.backrefs = set()
            cls.relationships = dict()
            cls.columns = cls.__table__.c
            cls.tablename = str(cls.__table__.name)
            base.all_models.add(cls)

            cls._build_backrefs_for_all_models(base.all_models)
        else:
            cls.all_models = set()

    def get_model_id(cls):
        return getattr(cls, cls.id_name)

    def _build_backrefs_for_all_models(cls, all_models):
        all_relationships = {}

        for model in all_models:
            model._build_relationships(all_models)
            all_relationships[model] = [i for i in model.relationships.values()]

        for model in all_models:
            for model_rel, rels in all_relationships.items():
                if model in rels:
                    model.backrefs.add(model_rel)

    def _build_relationships(cls, all_models):
        for attr_name in cls.__dict__:
            rel_model = cls._get_relationship_model(attr_name, all_models)
            if rel_model:
                cls.relationships[attr_name] = rel_model

    def _get_relationship_model(cls, attr_name, all_models):
        attr = getattr(cls, attr_name)

        if isinstance(attr, InstrumentedAttribute) and isinstance(attr.prop, RelationshipProperty):
            attr_model = attr.prop.argument

            if isinstance(attr_model, _class_resolver):
                for model in all_models:
                    if model.tablename == attr_model.arg:
                        return model

            return attr_model


class SQLAlchemyModel(object):
    def get_id(self):
        return getattr(self, type(self).id_name)

    def get_related(self, session):
        related = set()
        cls = type(self)

        for related_model in cls.relationships:
            related_model_insts = self._get_related_model_insts(session, related_model)
            related.update(related_model_insts)

        for related_model in cls.backrefs:
            related_model_insts = self._get_related_model_insts(session, related_model)
            related.update(related_model_insts)

        return related

    def _get_related_model_insts(self, session, related_model):
        cls = type(self)

        try:
            insts = self._build_related_query(session, related_model, cls)
        except InvalidRequestError:
            insts = self._build_related_query(session, cls, related_model)

        return set(insts)

    def _build_related_query(self, session, model1, model2):
        return session.query(model1).join(model2).filter(
            type(self).get_model_id() == self.get_id()).all()

    def todict(self):
        dict_inst = dict()
        
        for col in type(self).columns:
            col_name = str(col.name)
            dict_inst[col_name] = getattr(self, col_name)

        for rel_name in type(self).relationships:
            attr = getattr(self, rel_name)
            if isinstance(attr, InstrumentedList):
                relationships = [rel.todict() for rel in attr]
            else:
                relationships = attr.todict()

            dict_inst[rel_name] = relationships

        return dict_inst
