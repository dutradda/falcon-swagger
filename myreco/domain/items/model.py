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


from myreco.base.model import SQLAlchemyRedisModelBase
from myreco.base.routes import Route
from myreco.exceptions import ModelBaseError
from jsonschema import Draft4Validator
from collections import defaultdict
import sqlalchemy as sa
import json


class ItemsTypesModel(SQLAlchemyRedisModelBase):
    __tablename__ = 'items_types'
    __table_args__ = {'mysql_engine':'innodb'}
    _build_routes_from_schemas = False

    id = sa.Column(sa.Integer, primary_key=True)
    name = sa.Column(sa.Integer, unique=True, nullable=False)
    
    json_schemas = sa.orm.relationships('JsonSchemasModel', uselist=True, secondary='engines_fallbacks')


class JsonSchemasModel(SQLAlchemyRedisModelBase):
    __tablename__ = 'json_schemas'
    __table_args__ = {'mysql_engine':'innodb'}
    _build_routes_from_schemas = False

    id = sa.Column(sa.Integer, primary_key=True)
    method_id = sa.Column(sa.ForeignKey('methods.id'), nullable=False)
    type_id = sa.Column(sa.ForeignKey('json_schemas_types.id'), nullable=False)
    schema = sa.Column(sa.Text, nullable=False)

    method = sa.orm.relationship('MethodsModel')
    type = sa.orm.relationship('JsonSchemasTypesModel')


class JsonSchemasTypesModel(SQLAlchemyRedisModelBase):
    __tablename__ = 'json_schemas_types'
    __table_args__ = {'mysql_engine':'innodb'}
    _build_routes_from_schemas = False

    id = sa.Column(sa.Integer, primary_key=True)
    name = sa.Column(sa.String(255), nullable=False)


engines_fallbacks = sa.Table("items_types_json_schemas", SQLAlchemyRedisModelBase.metadata,
    sa.Column("item_type_id", sa.Integer, sa.ForeignKey("items_types.id", ondelete='CASCADE', onupdate='CASCADE'), primary_key=True),
    sa.Column("json_schema_id", sa.Integer, sa.ForeignKey("json_schemas.id", ondelete='CASCADE', onupdate='CASCADE'), primary_key=True)
    mysql_engine='innodb'
)


class _ItemsActionsMeta(type):

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


class ItemsActions(metaclass=_ItemsActionsMeta):
    pass


class _ItemsRoutesBuilderMeta(type):
    def _build_routes(cls, session):
        routes = set()
        for item_type in ItemsTypesModel.get(session):
            uri_template = '/items/{}'.format(item_type['name'])
            schemas = defaultdict(list)
            for schema in item_type['json_schemas']:
                method = schema['method']['name']
                type_ = schema['type']['name']
                schema_ = schema['schema'] if type_ == 'output' else Draft4Validator(schema['schema'])
                schemas[method].append(schema_)

            for method, schemas in schemas.items():
                validator = None
                output_schema = None
                for schema in schemas:
                    if isinstance(schema, Draft4Validator):
                        validator = schema
                    else:
                        output_schema = schema

                action = getattr(ItemsActions, '{}_action',format(method.lower()))
                route = Route(uri_template, method, action, validator, output_schema)
                routes.add(route)

        return routes

class ItemsRoutesBuilder(metaclass=_ItemsRoutesBuilderMeta):
    def __new__(cls, session):
        return cls._build_routes(session)


class _ItemsModelMeta(type):
    def get(cls, item_type_name):
        instance = cls._instances.get(item_type_name, cls(item_type_name))


class ItemsModel(metaclass=_ItemsModelMeta):
    _instances = dict()

    def __init__(self, item_type_name):
        type_ = ItemsTypesModel.get({'name': item_type_name})
        if not type_:
            raise ModelBaseError("Item type with id '{}' was not found".format(type_id))

        self._validator = Draft4Validator(json.loads(type_['schema']))
