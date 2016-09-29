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
from myreco.exceptions import ModelBaseError
from jsonschema import Draft4Validator
from collections import defaultdict
import sqlalchemy as sa
import json


class ItemsTypesModel(SQLAlchemyRedisModelBase):
    __tablename__ = 'items_types'
    __table_args__ = {'mysql_engine': 'innodb'}

    id = sa.Column(sa.Integer, primary_key=True)
    name = sa.Column(sa.Integer, unique=True, nullable=False)
    id_names_json = sa.Column(sa.String(255), nullable=False)
    schema_json = sa.Column(sa.Text, nullable=False)
    engine_id = sa.Column(sa.ForeignKey('engines.id'), nullable=False)

    @classmethod
    def insert(cls, session, objs, commit=True, todict=True):
        cls._format_input_json(objs)
        return type(cls).insert(cls, session, objs, commit, todict)

    @classmethod
    def _format_input_json(cls, objs):
        objs = cls._to_list(objs)
        for obj in ojbs:
            id_names = obj.pop('id_names', None)
            if id_names:
                obj['id_names_json'] = json.dumps(id_names)

            schema = obj.pop('schema', None)
            if schema:
                obj['schema_json'] = json.dumps(schema)

    @classmethod
    def update(cls, session, objs, commit=True, todict=True):
        cls._format_input_json(objs)
        return type(cls).update(cls, session, objs, commit, todict)

    @classmethod
    def get(cls, session, ids=None, limit=None, offset=None, **kwargs):
        objs = type(cls).get(cls, session, ids, limit, offset, **kwargs)
        cls._format_output_json(objs)
        return objs

    @classmethod
    def _format_output_json(cls, objs):
        objs = cls._to_list(objs)
        for obj in ojbs:
            obj['id_names'] = json.loads(obj.pop('id_names_json'))
            obj['schema'] = json.loads(obj.pop('schema_json'))
