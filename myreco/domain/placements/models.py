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


class PlacementsModel(SQLAlchemyRedisModelBase):
    __tablename__ = 'placements'
    __table_args__ = {'mysql_engine':'innodb'}

    hash = sa.Column(sa.String(255), primary_key=True)
    small_hash = sa.Column(sa.String(255), primary_key=True)
    name = sa.Column(sa.Integer, unique=True, nullable=False)
    ab_testing = sa.Column(sa.Boolean, default=False)
    store_id = sa.Column(sa.ForeignKey('stores.id'), nullable=False)

    variations = sa.orm.relationship('VariationsModel', uselist=True)


class VariationsModel(SQLAlchemyRedisModelBase):
    __tablename__ = 'variations'
    __table_args__ = {'mysql_engine':'innodb'}

    id = sa.Column(sa.Integer, primary_key=True)
    name = sa.Column(sa.Integer, nullable=False)
    placement_small_hash = sa.Column(sa.ForeignKey('placements.small_hash'), nullable=False)

    engines_managers = sa.orm.relationship('EnginesManagersModel',
                uselist=True, secondary='variations_engines_managers',
                primaryjoin='and_('
                    'VariationsModel.id==variations_engines_managers.c.variation_id,'
                    'EnginesManagersModel.id==variations_engines_managers.c.engines_managers_id,'
                    'EnginesModel.id==EnginesManagersModel.engine_id,'
                    'EnginesModel.type_id==variations_engines_managers.c.engine_type_id)',
                secondaryjoin='and_('
                    'VariationsModel.id==variations_engines_managers.c.variation_id,'
                    'EnginesManagersModel.id==variations_engines_managers.c.engines_managers_id,'
                    'EnginesModel.id==EnginesManagersModel.engine_id,'
                    'EnginesModel.type_id==variations_engines_managers.c.engine_type_id)')


class ABTestUsersModel(SQLAlchemyRedisModelBase):
    __tablename__ = 'ab_test_users'
    __table_args__ = {'mysql_engine':'innodb'}

    id = sa.Column(sa.Integer, primary_key=True)
    variation_id = sa.Column(sa.ForeignKey('variations.id'), nullable=False)


variations_engines_managers = sa.Table(
    'variations_engines_managers', SQLAlchemyRedisModelBase.metadata,
    sa.Column('variation_id', sa.Integer, sa.ForeignKey('variations.id', ondelete='CASCADE', onupdate='CASCADE'), primary_key=True),
    sa.Column('engines_managers_id', sa.Integer, sa.ForeignKey('engines_managers.id', ondelete='CASCADE', onupdate='CASCADE'), nullable=False),
    sa.Column('engine_type_id', sa.Integer, sa.ForeignKey('engines.type_id', ondelete='CASCADE', onupdate='CASCADE'), primary_key=True),
    mysql_engine='innodb')
