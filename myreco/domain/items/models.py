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


from myreco.base.models.sqlalchemy_redis import SQLAlchemyRedisModelBase, RedisModelMeta
from myreco.base.routes import Route
from myreco.exceptions import ModelBaseError
from jsonschema import Draft4Validator
from collections import defaultdict
import sqlalchemy as sa
import json


class ItemsTypesModel(SQLAlchemyRedisModelBase):
    __tablename__ = 'items_types'
    __table_args__ = {'mysql_engine': 'innodb'}
    _build_routes_from_schemas = False

    id = sa.Column(sa.Integer, primary_key=True)
    name = sa.Column(sa.Integer, unique=True, nullable=False)
    id_names_json = sa.Column(sa.String(255), default='["id"]')

    json_schemas = sa.orm.relationships(
        'JsonSchemasModel', uselist=True, secondary='engines_fallbacks')

    def insert(cls, session, objs, commit=True, todict=True):
        cls._validate_json(objs)
        type(cls).insert(cls, session, objs, commit, todict)

    def _validate_json(cls, objs_):
        objs = cls._to_list(objs_)
        for obj in ojbs:
            id_names_json = obj.get('id_names_json')
            if id_names_json:
                try:
                    json.loads(id_names_json)
                except ValueError as error:
                    raise JSONError(*error.args, input_=objs_)

    def update(cls, session, objs, commit=True, todict=True):
        cls._validate_json(objs)
        type(cls).update(cls, session, objs, commit, todict)



class JsonSchemasModel(SQLAlchemyRedisModelBase):
    __tablename__ = 'json_schemas'
    __table_args__ = {'mysql_engine': 'innodb'}
    _build_routes_from_schemas = False

    id = sa.Column(sa.Integer, primary_key=True)
    method_id = sa.Column(sa.ForeignKey('methods.id'), nullable=False)
    type_id = sa.Column(sa.ForeignKey('json_schemas_types.id'), nullable=False)
    schema = sa.Column(sa.Text, nullable=False)

    method = sa.orm.relationship('MethodsModel')
    type = sa.orm.relationship('JsonSchemasTypesModel')


class JsonSchemasTypesModel(SQLAlchemyRedisModelBase):
    __tablename__ = 'json_schemas_types'
    __table_args__ = {'mysql_engine': 'innodb'}
    _build_routes_from_schemas = False

    id = sa.Column(sa.Integer, primary_key=True)
    name = sa.Column(sa.String(255), nullable=False)


engines_fallbacks = sa.Table("items_types_json_schemas", SQLAlchemyRedisModelBase.metadata,
                             sa.Column("item_type_id", sa.Integer, sa.ForeignKey(
                                 "items_types.id", ondelete='CASCADE', onupdate='CASCADE'), primary_key=True),
                             sa.Column("json_schema_id", sa.Integer, sa.ForeignKey("json_schemas.id",
                                        ondelete='CASCADE', onupdate='CASCADE'), primary_key=True)
                             mysql_engine='innodb'
                             )
