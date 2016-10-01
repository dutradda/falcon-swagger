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
from myreco.domain.engines.types.base import EngineTypeChooser
from types import MethodType, FunctionType
import sqlalchemy as sa
import json


class EnginesModel(SQLAlchemyRedisModelBase):
    __tablename__ = 'engines'
    __table_args__ = {'mysql_engine':'innodb'}
    __schema__ = get_model_schema(__file__)

    id = sa.Column(sa.Integer, primary_key=True)
    configuration_json = sa.Column(sa.Text, nullable=False)
    store_id = sa.Column(sa.ForeignKey('stores.id'), nullable=False)
    type_id = sa.Column(sa.ForeignKey('engines_types.id'), nullable=False)
    item_type_id = sa.Column(sa.ForeignKey('items_types.id'), nullable=False, primary_key=True)

    type = sa.orm.relationship('EnginesTypesModel')
    item_type = sa.orm.relationship('ItemsTypesModel')
    filters = sa.orm.relationship('FiltersModel', uselist=True)

    def __setattr__(self, attr_name, value):
        if attr_name == 'type':
            type_ = EngineTypeChooser(value.name)
            self._set_type(type_)

        elif attr_name == 'configuration_json':
            self.configuration = json.loads(value)

        SQLAlchemyRedisModelBase.__setattr__(self, attr_name, value)

    def _set_type(self, type_):
        self.__class__ = type_
        for attr_name, attr in type_.__dict__.items():
            if isinstance(attr, FunctionType) and attr_name != 'type':
                self.__setattr__(attr_name, MethodType(attr, self))


class EnginesTypesModel(SQLAlchemyRedisModelBase):
    __tablename__ = 'engines_types'
    __table_args__ = {'mysql_engine':'innodb'}

    id = sa.Column(sa.Integer, primary_key=True)
    name = sa.Column(sa.String(255), unique=True, nullable=False)


class FiltersModel(SQLAlchemyRedisModelBase):
    __tablename__ = 'filters'
    __table_args__ = {'mysql_engine':'innodb'}

    name = sa.Column(sa.String(255), nullable=False, primary_key=True)
    item_type_id = sa.Column(sa.ForeignKey('items_types.id', ondelete='CASCADE', onupdate='CASCADE'), primary_key=True)
    engine_id = sa.Column(sa.ForeignKey('engines.id', ondelete='CASCADE', onupdate='CASCADE'), primary_key=True)
    store_id = sa.Column(sa.ForeignKey('stores.id', ondelete='CASCADE', onupdate='CASCADE'), nullable=False)
