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
from myreco.exceptions import ModelBaseError
from jsonschema import ValidationError
import sqlalchemy as sa


class EnginesManagersVariablesModelBase(sa.ext.declarative.AbstractConcreteBase):
    __tablename__ = 'engines_managers_variables'
    __use_redis__ = False

    id = sa.Column(sa.Integer, primary_key=True)
    is_filter = sa.Column(sa.Boolean, default=False)
    override = sa.Column(sa.Boolean, default=False)
    override_value_json = sa.Column(sa.Text)

    @sa.ext.declarative.declared_attr
    def inside_engine_name(cls):
        return sa.Column(sa.String(255), nullable=False)

    @sa.ext.declarative.declared_attr
    def variable_id(cls):
        return sa.Column(sa.ForeignKey('variables.id', ondelete='CASCADE', onupdate='CASCADE'))

    @sa.ext.declarative.declared_attr
    def engine_manager_id(cls):
        return sa.Column(sa.ForeignKey('engines_managers.id', ondelete='CASCADE', onupdate='CASCADE'))

    @sa.ext.declarative.declared_attr
    def variable(cls):
        return sa.orm.relationship('VariablesModel')


class EnginesManagersModelBase(sa.ext.declarative.AbstractConcreteBase):
    __tablename__ = 'engines_managers'
    __schema__ = get_model_schema(__file__)

    id = sa.Column(sa.Integer, primary_key=True)

    @sa.ext.declarative.declared_attr
    def engine_id(cls):
        return sa.Column(sa.ForeignKey('engines.id'), nullable=False)

    @sa.ext.declarative.declared_attr
    def store_id(cls):
        return sa.Column(sa.ForeignKey('stores.id'), nullable=False)

    @sa.ext.declarative.declared_attr
    def engine(cls):
        return sa.orm.relationship('EnginesModel')

    @sa.ext.declarative.declared_attr
    def engine_variables(cls):
        return sa.orm.relationship('EnginesManagersVariablesModel', uselist=True)

    @sa.ext.declarative.declared_attr
    def fallbacks(cls):
        return sa.orm.relationship('EnginesManagersModel',
        uselist=True, remote_side='EnginesManagersModel.id',
        secondary='engines_managers_fallbacks',
        primaryjoin='engines_managers_fallbacks.c.engines_managers_id == EnginesManagersModel.id',
        secondaryjoin='engines_managers_fallbacks.c.fallback_id == EnginesManagersModel.id')

    def __init__(self, session, input_=None, **kwargs):
        super().__init__(session, input_=input_, **kwargs)
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
                engines_variables_map = {var['name']: var['schema'] for var in engine['variables']}
                available_filters_map = {fil['name']: fil['schema'] \
                    for fil in engine['item_type']['available_filters']}
                key_func = lambda v: v['name']
                message = 'Invalid {}' + " with 'inside_engine_name' value '{}'".format(var_name)

                if not engine_variable.is_filter:
                    if var_name not in engines_variables_map:
                        message = message.format('engine variable')
                        schema = {'available_variables': sorted(engine['variables'], key=key_func)}
                        raise ValidationError(message, instance=input_, schema=schema)

                else:
                    if var_name not in available_filters_map:
                        message = message.format('filter')
                        schema = {
                            'available_filters': \
                                sorted(engine['item_type']['available_filters'], key=key_func)
                        }
                        raise ValidationError(message, instance=input_, schema=schema)

    def _setattr(self, attr_name, value, session, input_):
        if attr_name == 'engine_id':
            value = {'id': value}
            attr_name = 'engine'

        if attr_name == 'engine_variables':
            for engine_var in value:
                if 'variable_id' in engine_var:
                    var = {'id': engine_var.pop('variable_id')}
                    engine_var['variable'] = var

        super()._setattr(attr_name, value, session, input_)

    def _format_output_json(self, dict_inst):
        for fallback in dict_inst.get('fallbacks'):
            fallback.pop('fallbacks')


def build_engines_managers_fallbacks_table(metadata, **kwargs):
    return sa.Table("engines_managers_fallbacks", metadata,
        sa.Column("engines_managers_id", sa.Integer, sa.ForeignKey("engines_managers.id", ondelete='CASCADE', onupdate='CASCADE'), primary_key=True),
        sa.Column("fallback_id", sa.Integer, sa.ForeignKey("engines_managers.id", ondelete='CASCADE', onupdate='CASCADE'), primary_key=True),
        **kwargs)
