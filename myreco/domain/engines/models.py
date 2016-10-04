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


from myreco.base.models.sqlalchemy_redis import SQLAlchemyRedisModelBase
from myreco.base.models.base import get_model_schema
from myreco.domain.engines.types.base import EngineTypeChooser
from myreco.domain.items_types.models import ItemsTypesModel
from types import MethodType, FunctionType
from jsonschema import ValidationError
import sqlalchemy as sa
import json


class EnginesModel(SQLAlchemyRedisModelBase):
    __tablename__ = 'engines'
    __table_args__ = {'mysql_engine':'innodb'}
    __schema__ = get_model_schema(__file__)

    id = sa.Column(sa.Integer, primary_key=True, autoincrement=True)
    name = sa.Column(sa.String(255), unique=True, nullable=False)
    configuration_json = sa.Column(sa.Text, nullable=False)
    store_id = sa.Column(sa.ForeignKey('stores.id'), nullable=False)
    type_name_id = sa.Column(sa.ForeignKey('engines_types_names.id'), nullable=False)
    item_type_id = sa.Column(sa.ForeignKey('items_types.id'), nullable=False, primary_key=True)

    type_name = sa.orm.relationship('EnginesTypesNamesModel')
    item_type = sa.orm.relationship('ItemsTypesModel')
    filters = sa.orm.relationship('FiltersModel', uselist=True)
    store = sa.orm.relationship('StoresModel')

    @property
    def type_(self):
        if not hasattr(self, '_type'):
            self._set_type()
        return self._type

    def __init__(self, session, input_=None, **kwargs):
        SQLAlchemyRedisModelBase.__init__(self, session, input_=input_, **kwargs)

        self._validate_config(session, input_)
        self._validate_filters(session)

    def _validate_config(self, session, input_):
        if self.type_name is None:
            if self.type_name_id is not None:
                types_names = EnginesTypesNamesModel.get(
                    session, {'id': self.type_name_id}, todict=False)

                if not types_names:
                    raise ValidationError(
                        "type_name_id '{}' was not found".format(self.type_name_id),
                        instance=input_, schema={})

                self.type_name = types_names[0]

        if self.type_name is not None:
            validator = self.type_.__config_validator__
            if validator:
                validator.validate(json.loads(self.configuration_json))

    def _validate_filters(self, session):
        if self.item_type is None:
            if self.item_type_id is not None:
                items_types = ItemsTypesModel.get(
                    session, {'id': self.item_type_id}, todict=False)

                if not items_types:
                    raise ValidationError(
                        "item_type_id '{}' was not found".format(self.item_type_id),
                        instance=input_)

                self.item_type = items_types[0]

        if self.item_type is not None:
            available_filters = self.item_type.todict()['available_filters']
            for my_filter in self.filters:
                if my_filter.name not in available_filters:
                    raise ValidationError(
                        "invalid filter '{}'".format(my_filter.name),
                        instance={
                            'filters_names': [f['name'] for f in self.todict()['filters']]},
                        schema={'available_filters': available_filters})

    def _set_type(self):
        self._type = EngineTypeChooser(self.type_name.name)(json.loads(self.configuration_json))

    def _setattr(self, attr_name, value, session, input_):
        if attr_name == 'configuration':
            value = json.dumps(value)
            attr_name = 'configuration_json'

        if attr_name == 'type_name_id':
            value = {'id': value}
            attr_name = 'type_name'

        SQLAlchemyRedisModelBase._setattr(self, attr_name, value, session, input_)

    def todict(self, schema=None):
        dict_inst = SQLAlchemyRedisModelBase.todict(self, schema)
        self._format_output_json(dict_inst)
        return dict_inst

    def _format_output_json(self, dict_inst):
        if 'configuration_json' in dict_inst:
            dict_inst['configuration'] = json.loads(dict_inst.pop('configuration_json'))

        dict_inst['variables'] = self.type_.get_variables()

    @classmethod
    def get_recommendations(cls):
        pass


class EnginesTypesNamesModel(SQLAlchemyRedisModelBase):
    __tablename__ = 'engines_types_names'
    __table_args__ = {'mysql_engine':'innodb'}

    id = sa.Column(sa.Integer, primary_key=True)
    name = sa.Column(sa.String(255), unique=True, nullable=False)


class FiltersModel(SQLAlchemyRedisModelBase):
    __tablename__ = 'filters'
    __table_args__ = {'mysql_engine':'innodb'}

    name = sa.Column(sa.String(255), nullable=False, primary_key=True)
    engine_id = sa.Column(sa.ForeignKey('engines.id', ondelete='CASCADE', onupdate='CASCADE'), primary_key=True)
