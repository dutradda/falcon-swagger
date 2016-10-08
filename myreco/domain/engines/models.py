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


from myreco.base.models.base import get_model_schema
from myreco.domain.engines.types.base import EngineTypeChooser
from myreco.exceptions import ModelBaseError
from types import MethodType, FunctionType
from jsonschema import ValidationError
import sqlalchemy as sa
import json


class EnginesModelBase(sa.ext.declarative.AbstractConcreteBase):
    __tablename__ = 'engines'
    __schema__ = get_model_schema(__file__)

    id = sa.Column(sa.Integer, primary_key=True, autoincrement=True)
    name = sa.Column(sa.String(255), unique=True, nullable=False)
    configuration_json = sa.Column(sa.Text, nullable=False)

    @sa.ext.declarative.declared_attr
    def store_id(cls):
        return sa.Column(sa.ForeignKey('stores.id'), nullable=False)

    @sa.ext.declarative.declared_attr
    def type_name_id(cls):
        return sa.Column(sa.ForeignKey('engines_types_names.id'), nullable=False)

    @sa.ext.declarative.declared_attr
    def item_type_id(cls):
        return sa.Column(sa.ForeignKey('items_types.id'), nullable=False)

    @sa.ext.declarative.declared_attr
    def type_name(cls):
        return sa.orm.relationship('EnginesTypesNamesModel')

    @sa.ext.declarative.declared_attr
    def item_type(cls):
        return sa.orm.relationship('ItemsTypesModel')

    @sa.ext.declarative.declared_attr
    def store(cls):
        return sa.orm.relationship('StoresModel')

    @property
    def type_(self):
        if not hasattr(self, '_type'):
            self._set_type()
        return self._type

    def _set_type(self):
        self._type = EngineTypeChooser(self.type_name.name)(json.loads(self.configuration_json))

    def __init__(self, session, input_=None, **kwargs):
        super().__init__(session, input_=input_, **kwargs)
        self._validate_config(session, input_)

    def _validate_config(self, session, input_):
        if self.type_name is not None:
            validator = self.type_.__config_validator__
            if validator:
                validator.validate(self.type_.configuration)
                self.type_.validate_config(self)

    def _setattr(self, attr_name, value, session, input_):
        if attr_name == 'configuration':
            value = json.dumps(value)
            attr_name = 'configuration_json'

        if attr_name == 'type_name_id':
            value = {'id': value}
            attr_name = 'type_name'

        if attr_name == 'item_type_id':
            value = {'id': value}
            attr_name = 'item_type'

        super()._setattr(attr_name, value, session, input_)

    def _format_output_json(self, dict_inst):
        dict_inst['configuration'] = json.loads(dict_inst.pop('configuration_json'))
        dict_inst['variables'] = self.type_.get_variables(self)


class EnginesTypesNamesModelBase(sa.ext.declarative.AbstractConcreteBase):
    __tablename__ = 'engines_types_names'
    __use_redis__ = False

    id = sa.Column(sa.Integer, primary_key=True)
    name = sa.Column(sa.String(255), unique=True, nullable=False)
