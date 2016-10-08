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
from myreco.base.json_builder import JsonBuilder
from myreco.domain.engines.types.base import EngineTypeChooser
from myreco.exceptions import ModelBaseError
from falcon.errors import HTTPNotFound
import sqlalchemy as sa
import hashlib
import json


class PlacementsModelBase(sa.ext.declarative.AbstractConcreteBase):
    __tablename__ = 'placements'
    __schema__ = get_model_schema(__file__)

    hash = sa.Column(sa.String(255), primary_key=True)
    small_hash = sa.Column(sa.String(255), unique=True, nullable=False)
    name = sa.Column(sa.String(255), unique=True, nullable=False)
    ab_testing = sa.Column(sa.Boolean, default=False)

    @sa.ext.declarative.declared_attr
    def store_id(cls):
        return sa.Column(sa.ForeignKey('stores.id'), primary_key=True)

    @sa.ext.declarative.declared_attr
    def variations(cls):
        return sa.orm.relationship('VariationsModel', uselist=True, passive_deletes=True)

    def __init__(self, session, input_=None, **kwargs):
        super().__init__(session, input_=input_, **kwargs)
        self._set_hash()

    def _set_hash(self):
        if self.name and not self.hash:
            hash_ = hashlib.new('ripemd160')
            hash_.update(self.name.encode())
            self.hash = hash_.hexdigest()

    def __setattr__(self, name, value):
        if name == 'hash':
            self.small_hash = value[:5]

        super().__setattr__(name, value)

    @classmethod
    def get_recommendations(cls, req, resp):
        placement = cls._get_placement(req, resp)
        recommendations = []

        for engine_manger in placement['variations'][0]['engines_managers']:
            engine_vars = dict()
            engine = engine_manger['engine']
            for engine_var in engine_manger['engine_variables']:
                var_name = engine_var['variable']['name']
                if var_name in req.params:
                    schema = cls._get_variable_schema(engine, engine_var)
                    engine_vars[var_name] = JsonBuilder(req.params[var_name], schema)

            engine_type = EngineTypeChooser(engine['type_name']['name'])(engine['configuration'])
            recommendations.extend(engine_type.get_recommendations(**engine_vars))

        if not recommendations:
            raise HTTPNotFound()

        resp.body = json.dumps(recommendations)

    @classmethod
    def _get_placement(cls, req, resp):
        small_hash = req.context['parameters']['uri_template']['small_hash']
        session = req.context['session']
        placements = cls.get(session, {'small_hash': small_hash})

        if not placements:
            raise HTTPNotFound()

        return placements[0]

    @classmethod
    def _get_variable_schema(self, engine, engine_var):
        if engine_var['is_filter']:
            variables = engine['item_type']['available_filters']
        else:
            variables = engine['variables']

        for var in variables:
            if var['name'] == engine_var['inside_engine_name']:
                return var['schema']


class VariationsModelBase(sa.ext.declarative.AbstractConcreteBase):
    __tablename__ = 'variations'
    __use_redis__ = False

    id = sa.Column(sa.Integer, primary_key=True)
    weight = sa.Column(sa.Float)

    @sa.ext.declarative.declared_attr
    def placement_hash(cls):
        return sa.Column(sa.ForeignKey('placements.hash', ondelete='CASCADE', onupdate='CASCADE'), nullable=False)

    @sa.ext.declarative.declared_attr
    def engines_managers(cls):
        return sa.orm.relationship('EnginesManagersModel',
                uselist=True, secondary='variations_engines_managers')


class ABTestUsersModelBase(sa.ext.declarative.AbstractConcreteBase):
    __tablename__ = 'ab_test_users'
    __use_redis__ = False

    id = sa.Column(sa.Integer, primary_key=True)

    @sa.ext.declarative.declared_attr
    def variation_id(cls):
        return sa.Column(sa.ForeignKey('variations.id'), nullable=False)


def build_variations_engines_managers_table(metadata, **kwargs):
    return sa.Table(
        'variations_engines_managers', metadata,
        sa.Column('variation_id', sa.Integer, sa.ForeignKey('variations.id', ondelete='CASCADE', onupdate='CASCADE'), primary_key=True),
        sa.Column('engines_managers_id', sa.Integer, sa.ForeignKey('engines_managers.id', ondelete='CASCADE', onupdate='CASCADE'), nullable=False),
        **kwargs)
