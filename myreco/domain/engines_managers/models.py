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
import sqlalchemy as sa


class EnginesManagersVariablesModel(SQLAlchemyRedisModelBase):
    __tablename__ = 'engines_managers_variables'
    __table_args__ = {'mysql_engine':'innodb'}

    inside_engine_name = sa.Column(sa.String(255))
    variable_id = sa.Column(sa.ForeignKey('variables.id'), primary_key=True)
    engine_manager_id = sa.Column(sa.ForeignKey('engines_managers.id'), primary_key=True)
    is_filter = sa.Column(sa.Boolean, default=False)
    override = sa.Column(sa.Boolean, default=False)
    override_value = sa.Column(sa.String(255))

    variable = sa.orm.relationship('VariablesModel')


class EnginesManagersModel(SQLAlchemyRedisModelBase):
    __tablename__ = 'engines_managers'
    __table_args__ = {'mysql_engine':'innodb'}

    id = sa.Column(sa.Integer, primary_key=True)
    name = sa.Column(sa.String(255), unique=True, nullable=False)
    engine_id = sa.Column(sa.ForeignKey('engines.id'), nullable=False)
    store_id = sa.Column(sa.ForeignKey('stores.id'), nullable=False)

    engine = sa.orm.relationship('EnginesModel')
    engine_variables = sa.orm.relationship('EnginesManagersVariablesModel', uselist=True)
    fallbacks = sa.orm.relationship('EnginesManagersModel',
                            uselist=True,
                            secondary='engines_managers_fallbacks',
                            primaryjoin='and_('
                                'EnginesManagersModel.id==engines_managers_fallbacks.c.engines_managers_id,'
                                'EnginesModel.id==EnginesManagersModel.engine_id,'
                                'EnginesModel.type_id==engines_managers_fallbacks.c.engine_type_id,'
                                'engines_managers_fallbacks.c.engine_type_id=='
                                    'engines_managers_fallbacks.c.fallback_type_id)',
                            secondaryjoin='and_('
                                'EnginesManagersModel.id==engines_managers_fallbacks.c.fallback_id,'
                                'EnginesModel.id==EnginesManagersModel.engine_id,'
                                'EnginesModel.type_id==engines_managers_fallbacks.c.fallback_type_id,'
                                'engines_managers_fallbacks.c.engine_type_id=='
                                    'engines_managers_fallbacks.c.fallback_type_id)')


engines_managers_fallbacks = sa.Table("engines_managers_fallbacks", SQLAlchemyRedisModelBase.metadata,
    sa.Column("engines_managers_id", sa.Integer, sa.ForeignKey("engines_managers.id", ondelete='CASCADE', onupdate='CASCADE'), primary_key=True),
    sa.Column("fallback_id", sa.Integer, sa.ForeignKey("engines_managers.id", ondelete='CASCADE', onupdate='CASCADE'), primary_key=True),
    sa.Column("engine_type_id", sa.Integer, sa.ForeignKey("engines.type_id", ondelete='CASCADE', onupdate='CASCADE'), primary_key=True),
    sa.Column("fallback_type_id", sa.Integer, sa.ForeignKey("engines.type_id", ondelete='CASCADE', onupdate='CASCADE'), primary_key=True),
    mysql_engine='innodb'
)
