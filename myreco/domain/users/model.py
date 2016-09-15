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
from base64 import b64decode
import sqlalchemy as sa
import re


class UsersModel(SQLAlchemyRedisModelBase):
    __tablename__ = 'users'
    __table_args__ = {'mysql_engine':'innodb'}
    id_names = ('email', 'password_hash')

    id = sa.Column(sa.Integer, primary_key=True)
    name = sa.Column(sa.String(255), unique=True, nullable=False)
    email = sa.Column(sa.String(255), unique=True, nullable=False)
    password_hash = sa.Column(sa.String(255), nullable=False)
    primaryjoin = 'UsersModel.id == users_grants.c.user_id'
    secondaryjoin = 'and_('\
            'GrantsModel.uri_id == users_grants.c.grant_uri_id, '\
            'GrantsModel.method_id == users_grants.c.grant_method_id)'
    grants = sa.orm.relationship(
        'GrantsModel', uselist=True, secondary='users_grants',
        primaryjoin=primaryjoin, secondaryjoin=secondaryjoin)

    @classmethod
    def authorize(cls, session, authorization, uri, method):
        authorization = b64decode(authorization).decode()
        if not ':' in authorization:
            return

        user, pass_hash = authorization.split(':')
        user = cls.get(session, (user, pass_hash))
        user = user[0] if user else user
        if user and not user.get('grants'):
            return True

        elif user:
            for grant in user['grants']:
                if re.match(grant['uri']['regex'], uri) and grant['method']['method'] == method:
                    return True


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
    regex = sa.Column(sa.String(255), unique=True, nullable=False)


class MethodsModel(SQLAlchemyRedisModelBase):
    __tablename__ = 'methods'
    __table_args__ = {'mysql_engine':'innodb'}

    id = sa.Column(sa.Integer, primary_key=True)
    method = sa.Column(sa.String(10), unique=True, nullable=False)


users_grants = sa.Table(
    'users_grants', SQLAlchemyRedisModelBase.metadata,
    sa.Column('user_id', sa.Integer, sa.ForeignKey('users.id', ondelete='CASCADE')),
    sa.Column('grant_uri_id', sa.Integer, sa.ForeignKey('grants.uri_id', ondelete='CASCADE')),
    sa.Column('grant_method_id', sa.Integer, sa.ForeignKey('grants.method_id', ondelete='CASCADE')),
    mysql_engine='innodb')
