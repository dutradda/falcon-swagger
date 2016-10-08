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
from myreco.base.hooks import AuthorizationHook, before_operation
from base64 import b64decode
import sqlalchemy as sa


class GrantsModelBase(sa.ext.declarative.AbstractConcreteBase):
    __tablename__ = 'grants'
    __use_redis__ = False

    @sa.ext.declarative.declared_attr
    def uri_id(cls):
        return sa.Column(sa.ForeignKey('uris.id'), primary_key=True)

    @sa.ext.declarative.declared_attr
    def method_id(cls):
        return sa.Column(sa.ForeignKey('methods.id'), primary_key=True)

    @sa.ext.declarative.declared_attr
    def uri(cls):
        return sa.orm.relationship('URIsModel')

    @sa.ext.declarative.declared_attr
    def method(cls):
        return sa.orm.relationship('MethodsModel')


class URIsModelBase(sa.ext.declarative.AbstractConcreteBase):
    __tablename__ = 'uris'
    __use_redis__ = False

    id = sa.Column(sa.Integer, primary_key=True)
    uri = sa.Column(sa.String(255), unique=True, nullable=False)


class MethodsModelBase(sa.ext.declarative.AbstractConcreteBase):
    __tablename__ = 'methods'
    __use_redis__ = False

    id = sa.Column(sa.Integer, primary_key=True)
    method = sa.Column(sa.String(10), unique=True, nullable=False)


class UsersModelBase(sa.ext.declarative.AbstractConcreteBase):
    __tablename__ = 'users'
    __schema__ = get_model_schema(__file__)
    __realm__= 'myreco'

    id = sa.Column(sa.String(255), primary_key=True)
    name = sa.Column(sa.String(255), unique=True, nullable=False)
    email = sa.Column(sa.String(255), unique=True, nullable=False)
    password = sa.Column(sa.String(255), nullable=False)
    admin = sa.Column(sa.Boolean, default=False)

    @sa.ext.declarative.declared_attr
    def grants(cls):
        grants_primaryjoin = 'UsersModel.id == users_grants.c.user_id'
        grants_secondaryjoin = 'and_('\
            'GrantsModel.uri_id == users_grants.c.grant_uri_id, '\
            'GrantsModel.method_id == users_grants.c.grant_method_id)'

        return sa.orm.relationship(
            'GrantsModel', uselist=True, secondary='users_grants',
            primaryjoin=grants_primaryjoin, secondaryjoin=grants_secondaryjoin)

    @sa.ext.declarative.declared_attr
    def stores(cls):
        return sa.orm.relationship('StoresModel', uselist=True, secondary='users_stores')

    @classmethod
    def authorize(cls, session, authorization, uri_template, path, method):
        authorization = b64decode(authorization).decode()
        if not ':' in authorization:
            return

        user = cls.get(session, {'id': authorization})
        user = user[0] if user else user
        if user and user.get('admin'):
            session.user = user
            return True

        elif user:
            for grant in user['grants']:
                grant_uri = grant['uri']['uri']
                if grant_uri == uri_template or grant_uri == path \
                        and grant['method']['method'] == method:
                    session.user = user
                    return True

    @classmethod
    def insert(cls, session, objs, commit=True, todict=True):
        objs = cls._to_list(objs)
        cls._set_objs_ids_and_grant(objs, session)
        return type(cls).insert(cls, session, objs, commit, todict)

    @classmethod
    def _set_objs_ids_and_grant(cls, objs, session):
        objs = cls._to_list(objs)
        method = cls.get_model('methods').get(session, ids={'method': 'patch'}, todict=False)

        for obj in objs:
            user_uri = '/users/{}'.format(obj['email'])
            uri = cls.get_model('uris').get(session, ids={'uri': user_uri}, todict=False)

            if uri and method:
                uri = uri[0]
                method = method[0]
                grant = cls.get_model('grants').get(session, {'uri_id': uri.id, 'method_id': method.id})
                if grant:
                    grant = {'uri_id': uri.id, 'method_id': method.id}
                else:
                    grant = {'uri_id': uri.id, 'method_id': method.id, '_operation': 'insert'}
            elif uri:
                uri = uri[0]
                grant = {
                    'uri_id': uri.id,
                    'method': {'method': 'patch', '_operation': 'insert'},
                    '_operation': 'insert'
                }
            elif method:
                method = method[0]
                grant = {
                    'method': {'id': method.id},
                    'uri': {'uri': user_uri, '_operation': 'insert'},
                    '_operation': 'insert'
                }
            else:
                grant = {
                    'method': {'method': 'patch', '_operation': 'insert'},
                    'uri': {'uri': user_uri, '_operation': 'insert'},
                    '_operation': 'insert'
                }

            obj['id'] = '{}:{}'.format(obj['email'], obj['password'])
            grants = obj.get('grants', [])
            grants.append(grant)
            obj['grants'] = grants

    @classmethod
    def update(cls, session, objs, commit=True, todict=True, ids=None, ids_keys=None):
        if not ids:
            ids = []
            objs = cls._to_list(objs)
            for obj in objs:
                id_ = obj.get('id')
                email = obj.get('email')
                if id_ is not None:
                    ids.append({'id': id_})
                    ids_keys = ('id',)
                elif email is not None:
                    ids.append({'email': email})
                    ids_keys = ('email',)

        insts = type(cls).update(cls, session, objs, commit=False,
                            todict=False, ids=ids, ids_keys=ids_keys)
        cls._set_insts_ids(insts)

        if commit:
            session.commit()
        return cls._build_todict_list(insts) if todict else insts

    @classmethod
    def _set_insts_ids(cls, insts):
        insts = cls._to_list(insts)
        for inst in insts:
            inst.id = '{}:{}'.format(inst.email, inst.password)


UsersModelBase = before_operation(AuthorizationHook())(UsersModelBase)


def build_users_grants_table(metadata, **kwargs):
    return sa.Table(
        'users_grants', metadata,
        sa.Column('user_id', sa.String(255), sa.ForeignKey('users.id', ondelete='CASCADE', onupdate='CASCADE'), primary_key=True),
        sa.Column('grant_uri_id', sa.Integer, sa.ForeignKey('grants.uri_id', ondelete='CASCADE', onupdate='CASCADE'), primary_key=True),
        sa.Column('grant_method_id', sa.Integer, sa.ForeignKey('grants.method_id', ondelete='CASCADE', onupdate='CASCADE'), primary_key=True),
        **kwargs)


def build_users_stores_table(metadata, **kwargs):
    return sa.Table(
        'users_stores', metadata,
        sa.Column('user_id', sa.String(255), sa.ForeignKey('users.id', ondelete='CASCADE', onupdate='CASCADE'), primary_key=True),
        sa.Column('store_id', sa.Integer, sa.ForeignKey('stores.id', ondelete='CASCADE', onupdate='CASCADE'), primary_key=True),
        **kwargs)
