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
from myreco.domain.users.model import GrantsModel, URIsModel, MethodsModel
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
def resource(app, session):
    resource_ = UsersResource(app)
    user = {
        'name': 'test',
        'email': 'test',
        'password_hash': 'test'
    }
    resource_.model.insert(session, user)

    grants = [{
        'uri': {'uri': '/test'},
        'method': {'method': 'post'}
    }]
    GrantsModel.insert(session, grants)

    uri = {'uri': '/test2'}
    URIsModel.insert(session, uri)

    method = {'method': 'get'}
    MethodsModel.insert(session, method)

    return resource_


@pytest.fixture
def headers():
    return {
        'Authorization': b64encode('test:test'.encode()).decode()
    }


class TestUsersResourcePost(object):
    def test_post_valid_grants_update(self, resource, client, headers):
        user = {
            'name': 'test2',
            'email': 'test2',
            'password_hash': 'test',
            'grants': [{
                'uri_id': 1,
                'method_id': 1,
                '_update': True
            }]
        }
        resp = client.post('/users', data=json.dumps(user), headers=headers)

        assert resp.status_code == 201
        assert json.loads(resp.body) == {
            'id': 2,
            'name': 'test2',
            'email': 'test2',
            'password_hash': 'test',
            'grants': [{
                'method_id': 1,
                'uri_id': 1,
                'method': {'id': 1, 'method': 'post'},
                'uri': {'id': 1, 'uri': '/test'}
            }],
            'stores': []
        }

    def test_post_valid_with_grants_insert_and_uri_and_method_update(
            self, resource, client, headers):
        user = {
            'name': 'test2',
            'email': 'test2',
            'password_hash': 'test',
            'grants': [{
                'uri': {'id': 2, '_update': True},
                'method': {'id': 2, '_update': True}
            }]
        }
        resp = client.post('/users', data=json.dumps(user), headers=headers)

        assert resp.status_code == 201
        assert json.loads(resp.body) == {
            'id': 2,
            'name': 'test2',
            'email': 'test2',
            'password_hash': 'test',
            'grants': [{
                'method_id': 2,
                'uri_id': 2,
                'method': {'id': 2, 'method': 'get'},
                'uri': {'id': 2, 'uri': '/test2'}
            }],
            'stores': []
        }

    def test_post_valid_with_grants_uri_and_method_insert(
            self, resource, client, headers):
        user = {
            'name': 'test2',
            'email': 'test2',
            'password_hash': 'test',
            'grants': [{
                'uri': {'uri': '/test3'},
                'method': {'method': 'put'}
            }]
        }
        resp = client.post('/users', data=json.dumps(user), headers=headers)

        print(resp.body)
        assert resp.status_code == 201
        assert json.loads(resp.body) == {
            'id': 2,
            'name': 'test2',
            'email': 'test2',
            'password_hash': 'test',
            'grants': [{
                'method_id': 3,
                'uri_id': 3,
                'method': {'id': 3, 'method': 'put'},
                'uri': {'id': 3, 'uri': '/test3'}
            }],
            'stores': []
        }

    def test_post_invalid_json(self, resource, client, headers):
        user = {
            'name': 'test2',
            'email': 'test2',
            'password_hash': 'test',
            'grants': [{
                'uri_id': 1,
                'method_id': 1
            }]
        }
        resp = client.post('/users', data=json.dumps(user), headers=headers)

        assert resp.status_code == 400
        result = json.loads(resp.body)
        message = result['error'].pop('message')
        assert message == \
                "{'method_id': 1, 'uri_id': 1} is not valid under any of the given schemas" \
            or message == \
                "{'uri_id': 1, 'method_id': 1} is not valid under any of the given schemas"
        assert result == {
            'error': {
                'input': {'method_id': 1, 'uri_id': 1},
                'schema': {
                    'oneOf': [
                        {
                            'type': 'object',
                            'additionalProperties': False,
                            'required': ['uri_id', 'method_id', '_update'],
                            'properties': {
                                '_update': {'enum': [True]},
                                'method_id': {'type': 'integer'},
                                'uri_id': {'type': 'integer'}
                            }
                        },{
                            'type': 'object',
                            'additionalProperties': False,
                            'required': ['uri', 'method'],
                            'properties': {
                                'method': {'$ref': '#/definitions/method'},
                                'uri': {'$ref': '#/definitions/uri'}
                            }
                        }
                    ]
                }
            }
        }
