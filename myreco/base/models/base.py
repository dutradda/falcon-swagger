from sqlalchemy.ext import declarative_base

from myreco.base.models.json_schema import JsonSchemaModelMeta
from myreco.base.models.sqlalchemy import SQLAlchemyModelMeta, SQLAlchemyModel
from myreco.base.models.falcon import FalconModel


MODEL_BASE_CLASS_NAME = 'ModelBase'


class BaseMeta(JsonSchemaModelMeta, SQLAlchemyModelMeta):
    pass


ModelBase = declarative_base(
    name=MODEL_BASE_CLASS_NAME, metaclass=BaseMeta,
    cls=FalconModel, constructor=FalconModel.__init__)
