from sqlalchemy.ext.declarative.api import DeclarativeMeta as DeclarativeMeta
from sqlalchemy.ext.declarative.clsregistry import _class_resolver
from sqlalchemy.orm.properties import RelationshipProperty
from sqlalchemy.orm.attributes import InstrumentedAttribute
from sqlalchemy.orm.collections import InstrumentedList
from sqlalchemy.sql.expression import or_

from weakref import WeakValueDictionary

from myreco.base.models.base import MODEL_BASE_CLASS_NAME


class SQLAlchemyModelMeta(DeclarativeMeta):
    def __init__(cls, name, bases_classes, attributes):
        if not hasattr(cls, '_decl_class_registry'):
            cls._decl_class_registry = WeakValueDictionary()

        if not hasattr(cls, 'id_name'):
            cls.id_name = 'id'
        cls.get_id()

        cls.backrefs = set()
        cls.relationships = {}

        cls._build_backrefs_for_all_models(name, bases_classes)

        DeclarativeMetaSA.__init__(cls, name, bases_classes, attributes)

    def get_id(cls):
        return getattr(cls, cls.id_name)

    def _build_backrefs_for_all_models(cls, name, bases_classes):
        if name != MODEL_BASE_CLASS_NAME:
            all_models = set()

            for base in bases_classes:
                all_models.update(set(base.__subclasses__()))

            all_relationships = {}

            for model in all_models:
                model._build_relationships(all_models)
                all_relationships[model] = model.relationships.values()

            for model in all_models:
                for model_rel, rels in all_relationships.items():
                    if model in rels:
                        model.backrefs.add(model_rel)

    def _build_relationships(cls, all_models):
        rels = {}
        for attr_name in cls.__dict__:
            attr = cls._get_relationship_model(attr_name, all_models)
            if attr:
                rels[attr_name] = attr
        cls.relationships = rels

    def _get_relationship_model(cls, attr_name, all_models):
        attr = getattr(cls, attr_name)

        if isinstance(attr, RelationshipProperty):
            attr_model = attr.argument

            if isinstance(attr_model, str):
                for model in all_models:
                    if model.__name__ == attr_model:
                        return model
                return None

            return attr_model


class SQLAlchemyModel(object):
    def get_id(self):
        return getattr(self, type(self).id_name)

    def get_related(self, session, inst_id):
        related = set()
        cls = type(self)

        for related_model in cls.relationships.values():
            related_model_insts = self._get_related_model_insts(related_model)
            related.update(related_model_insts)

        for related_model in cls.backrefs:
            related_model_insts = self._get_related_model_insts(related_model)
            related.update(related_model_insts)

        return related

    def _get_related_model_insts(self, related_model):
        cls = type(self)
        insts = session.query(related_model).join(cls).filter(cls.get_id() == self.get_id()).all()
        return set(insts)
