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


from myreco.domain.users.resource import UsersResource
from myreco.base.model import SQLAlchemyRedisModelBase
from myreco.base.http_api import HttpAPI
from unittest import mock
from base64 import b64encode

import pytest
import json


@pytest.fixture
def model_base():
    return SQLAlchemyRedisModelBase


@pytest.fixture
def app(session):
    return HttpAPI(session.bind)


@pytest.fixture
def resource(app):
    return UsersResource(app)


class TestUsersResource(object):
    def test_user_authorized_without_uri_and_methods(self, resource, client, session):
        user = {
            'name': 'test',
            'email': 'test@test',
            'password_hash': '123'
        }
        resource.model.insert(session, user)

        authorization = \
            b64encode('{}:{}'.format(user['email'], user['password_hash']).encode()).decode()
        headers = {
            'Authorization': 'Basic {}'.format(authorization)
        }

        resp = client.get('/users/', headers=headers)
        assert resp.status_code == 200
        assert json.loads(resp.body) == [{
            'email': 'test@test',
            'name': 'test',
            'grants': [],
            'id': 1,
            'password_hash': '123'
        }]

    def test_user_authorized_with_uri_and_methods(self, resource, client, session):
        user = {
            'name': 'test',
            'email': 'test@test',
            'password_hash': '123',
            'grants': [{'uri': {'uri': '/users'}, 'method': {'method': 'GET'}}]
        }
        resource.model.insert(session, user)

        authorization = \
            b64encode('{}:{}'.format(user['email'], user['password_hash']).encode()).decode()
        headers = {
            'Authorization': 'Basic {}'.format(authorization)
        }

        resp = client.get('/users/', headers=headers)
        assert resp.status_code == 200
        assert json.loads(resp.body) == [{
            'email': 'test@test',
            'name': 'test',
            'grants': [{
                "uri_id": 1,
                "id": 1,
                "uri": {
                    "id": 1,
                    "uri": "/users"
                },
                "method_id": 1,
                "method": {
                    "id": 1,
                    "method": "GET"
                }
            }],
            'id': 1,
            'password_hash': '123'
        }]

    def test_user_not_authorized_with_wrong_uri(self, session, resource, client):
        user = {
            'name': 'test',
            'email': 'test@test',
            'password_hash': '123',
            'grants': [{'uri': {'uri': '/user'}, 'method': {'method': 'GET'}}]
        }
        resource.model.insert(session, user)

        authorization = \
            b64encode('{}:{}'.format(user['email'], user['password_hash']).encode()).decode()
        headers = {
            'Authorization': 'Basic {}'.format(authorization)
        }

        resp = client.get('/users/', headers=headers)
        assert resp.status_code == 401
        assert resp.body == json.dumps({'error': 'Invalid authorization'})

    def test_user_not_authorized_without_user(self, session, resource, client):
        authorization = b64encode('test:test'.encode()).decode()
        headers = {
            'Authorization': 'Basic {}'.format(authorization)
        }
        resp = client.get('/users/', headers=headers)

        assert resp.status_code == 401
        assert resp.body == json.dumps({'error': 'Invalid authorization'})

    def test_user_not_authorized_without_authorization_header(self, session, resource, client):
        resp = client.get('/users/')

        assert resp.status_code == 401
        assert resp.body == json.dumps({'error': 'Authorization header is required'})
