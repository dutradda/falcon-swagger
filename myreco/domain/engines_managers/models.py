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
from myreco.base.models.sqlalchemy_redis import SQLAlchemyRedisModelBase
from myreco.domain.engines.models import EnginesModel
from myreco.exceptions import ModelBaseError
from jsonschema import ValidationError
import sqlalchemy as sa


class EnginesManagersVariablesModel(SQLAlchemyRedisModelBase):
    __tablename__ = 'engines_managers_variables'
    __table_args__ = {'mysql_engine':'innodb'}

    id = sa.Column(sa.Integer, primary_key=True)
    inside_engine_name = sa.Column(sa.String(255), nullable=False)
    variable_id = sa.Column(sa.ForeignKey('variables.id', ondelete='CASCADE', onupdate='CASCADE'))
    engine_manager_id = sa.Column(sa.ForeignKey('engines_managers.id', ondelete='CASCADE', onupdate='CASCADE'))
    override = sa.Column(sa.Boolean, default=False)
    override_value_json = sa.Column(sa.Text)

    variable = sa.orm.relationship('VariablesModel')


class EnginesManagersModel(SQLAlchemyRedisModelBase):
    __tablename__ = 'engines_managers'
    __table_args__ = {'mysql_engine':'innodb'}
    __schema__ = get_model_schema(__file__)

    id = sa.Column(sa.Integer, primary_key=True)
    engine_id = sa.Column(sa.ForeignKey('engines.id'), nullable=False)
    store_id = sa.Column(sa.ForeignKey('stores.id'), nullable=False)

    engine = sa.orm.relationship('EnginesModel')
    engine_variables = sa.orm.relationship('EnginesManagersVariablesModel', uselist=True)
    fallbacks = sa.orm.relationship('EnginesManagersModel',
        uselist=True, remote_side=[id],
        secondary='engines_managers_fallbacks',
        primaryjoin='engines_managers_fallbacks.c.engines_managers_id == EnginesManagersModel.id',
        secondaryjoin='engines_managers_fallbacks.c.fallback_id == EnginesManagersModel.id')

    def __init__(self, session, input_=None, **kwargs):
        SQLAlchemyRedisModelBase.__init__(self, session, input_=input_, **kwargs)
        self._set_engine(session, input_)
        self._validate_fallbacks(input_)
        self._validate_engine_variables(input_)

    def _validate_fallbacks(self, input_):
        for fallback in self.fallbacks:
            if fallback.id == self.id:
                raise ModelBaseError("a Engine Manager can't fallback itself", input_)

            if fallback.engine.item_type_id != self.engine.item_type_id:
                raise ModelBaseError("Cannot set a fallback with different items types", input_)

    def _validate_engine_variables(self, input_):
        if self.engine is not None:
            engine = self.engine.todict()
            for engine_variable in self.engine_variables:
                var_name = engine_variable.inside_engine_name
                if var_name not in engine['variables'] \
                        and var_name not in engine['item_type']['available_filters']:
                    message = "Invalid 'inside_engine_name' property value '{}'".format(var_name)
                    schema = {
                        'available_variables': engine['variables'],
                        'available_filters': engine['item_type']['available_filters']
                    }
                    raise ValidationError(message, instance=input_, schema=schema)

    def _set_engine(self, session, input_):
        if self.engine is None:
            if self.engine_id is not None:
                engines = EnginesModel.get(session, {'id': self.engine_id}, todict=False)

                if not engines:
                    raise ModelBaseError(
                        "engine_id '{}' was not found".format(self.engine_id), input_)

                self.engine = engines[0]

    def todict(self, schema=None):
        dict_inst = SQLAlchemyRedisModelBase.todict(self, schema)
        self._format_output_json(dict_inst)
        return dict_inst

    def _format_output_json(self, dict_inst):
        for fallback in dict_inst.get('fallbacks'):
            fallback.pop('fallbacks')


engines_managers_fallbacks = sa.Table("engines_managers_fallbacks", SQLAlchemyRedisModelBase.metadata,
    sa.Column("engines_managers_id", sa.Integer, sa.ForeignKey("engines_managers.id", ondelete='CASCADE', onupdate='CASCADE'), primary_key=True),
    sa.Column("fallback_id", sa.Integer, sa.ForeignKey("engines_managers.id", ondelete='CASCADE', onupdate='CASCADE'), primary_key=True),
    mysql_engine='innodb'
)
