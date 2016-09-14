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


from myreco.domain.users.model import UsersModel
from myreco.base.model import SQLAlchemyRedisModelBase
from unittest import mock

import pytest
from base64 import b64encode


@pytest.fixture
def model_base():
    return SQLAlchemyRedisModelBase


class TestUsersModel(object):
    def test_user_authorized_without_uri_and_methods(self, session, redis):
        user = {
            'name': 'test',
            'email': 'test@test',
            'password_hash': '123'
        }
        UsersModel.insert(session, user)
        authorization = b64encode('{}:{}'.format(user['email'], user['password_hash']).encode())
        redis.hmget.return_value = [None]

        assert UsersModel.authorize(session, authorization, None, None) is True

    def test_user_authorized_with_uri_and_methods(self, session, redis):
        user = {
            'name': 'test',
            'email': 'test@test',
            'password_hash': '123',
            'grants': [{'uri': {'uri': '/test'}, 'method': {'method': 'POST'}}]
        }
        UsersModel.insert(session, user)
        authorization = b64encode('{}:{}'.format(user['email'], user['password_hash']).encode())
        redis.hmget.return_value = [None]

        assert UsersModel.authorize(session, authorization, '/test', 'POST') is True

    def test_user_not_authorized_with_wrong_uri(self, session, redis):
        user = {
            'name': 'test',
            'email': 'test@test',
            'password_hash': '123',
            'grants': [{'uri': {'uri': '/test'}, 'method': {'method': 'POST'}}]
        }
        UsersModel.insert(session, user)
        authorization = b64encode('{}:{}'.format(user['email'], user['password_hash']).encode())
        redis.hmget.return_value = [None]

        assert UsersModel.authorize(session, authorization, '/tes', 'POST') is None

    def test_user_not_authorized_without_user(self, session, redis):
        authorization = b64encode('test:test'.encode())
        redis.hmget.return_value = [None]

        assert UsersModel.authorize(session, authorization, '/tes', 'POST') is None

    def test_user_not_authorized_with_authorization_without_colon(self, session, redis):
        authorization = b64encode('test'.encode())
        redis.hmget.return_value = [None]

        assert UsersModel.authorize(session, authorization, '/tes', 'POST') is None
