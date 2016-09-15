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
from myreco.domain.stores.model import StoresModel
from base64 import b64decode
import sqlalchemy as sa
import re


class UsersModel(SQLAlchemyRedisModelBase):
    __tablename__ = 'users'
    __table_args__ = {'mysql_engine':'innodb'}

    id = sa.Column(sa.String(255), primary_key=True)
    name = sa.Column(sa.String(255), unique=True, nullable=False)
    email = sa.Column(sa.String(255), unique=True, nullable=False)
    password = sa.Column(sa.String(255), nullable=False)

    grants_primaryjoin = 'UsersModel.id == users_grants.c.user_id'
    grants_secondaryjoin = 'and_('\
            'GrantsModel.uri_id == users_grants.c.grant_uri_id, '\
            'GrantsModel.method_id == users_grants.c.grant_method_id)'

    grants = sa.orm.relationship(
        'GrantsModel', uselist=True, secondary='users_grants',
        primaryjoin=grants_primaryjoin, secondaryjoin=grants_secondaryjoin)
    stores = sa.orm.relationship('StoresModel', uselist=True, secondary='users_stores')

    @classmethod
    def authorize(cls, session, authorization, uri, path, method):
        authorization = b64decode(authorization).decode()
        if not ':' in authorization:
            return

        user = cls.get(session, authorization)
        user = user[0] if user else user
        if user and not user.get('grants'):
            session.user = user
            return True

        elif user:
            for grant in user['grants']:
                grant_uri = grant['uri']['uri']
                if bool(grant_uri == uri) != bool(grant_uri == path) \
                        and grant['method']['method'] == method:
                    session.user = user
                    return True

    @classmethod
    def insert(cls, session, objs, commit=True, todict=True):
        cls._set_objs_ids(objs)
        return type(cls).insert(cls, session, objs, commit, todict)

    @classmethod
    def _set_objs_ids(cls, objs):
        objs = cls._to_list(objs)
        for obj in objs:
            obj['id'] = '{}:{}'.format(obj['email'], obj['password'])

    @classmethod
    def update(cls, session, objs, commit=True, todict=True):
        insts = SQLAlchemyRedisModelBase.update(cls, session, objs, commit=False, todict=False)
        cls._set_insts_ids(insts)

        if commit:
            session.commit()

        return cls._build_todict_list(insts) if todict else insts

    @classmethod
    def _set_insts_ids(cls, insts):
        insts = cls._to_list(insts)
        for inst in insts:
            inst.id = '{}:{}'.format(inst,email, inst.password)


class GrantsModel(SQLAlchemyRedisModelBase):
    __tablename__ = 'grants'
    __table_args__ = {'mysql_engine':'innodb'}
    id_names = ('uri_id', 'method_id')

    uri_id = sa.Column(sa.ForeignKey('uris.id'), primary_key=True)
    method_id = sa.Column(sa.ForeignKey('methods.id'), primary_key=True)

    uri = sa.orm.relationship('URIsModel')
    method = sa.orm.relationship('MethodsModel')


class URIsModel(SQLAlchemyRedisModelBase):
    __tablename__ = 'uris'
    __table_args__ = {'mysql_engine':'innodb'}

    id = sa.Column(sa.Integer, primary_key=True)
    uri = sa.Column(sa.String(255), unique=True, nullable=False)


class MethodsModel(SQLAlchemyRedisModelBase):
    __tablename__ = 'methods'
    __table_args__ = {'mysql_engine':'innodb'}

    id = sa.Column(sa.Integer, primary_key=True)
    method = sa.Column(sa.String(10), unique=True, nullable=False)


users_grants = sa.Table(
    'users_grants', SQLAlchemyRedisModelBase.metadata,
    sa.Column('user_id', sa.String(255), sa.ForeignKey(
        'users.id', ondelete='CASCADE', onupdate='CASCADE')),
    sa.Column('grant_uri_id', sa.Integer, sa.ForeignKey('grants.uri_id', ondelete='CASCADE')),
    sa.Column('grant_method_id', sa.Integer, sa.ForeignKey('grants.method_id', ondelete='CASCADE')),
    mysql_engine='innodb')


users_stores = sa.Table(
    'users_stores', SQLAlchemyRedisModelBase.metadata,
    sa.Column('user_id', sa.String(255), sa.ForeignKey('users.id', ondelete='CASCADE')),
    sa.Column('store_id', sa.Integer, sa.ForeignKey('stores.id', ondelete='CASCADE')),
    mysql_engine='innodb')
