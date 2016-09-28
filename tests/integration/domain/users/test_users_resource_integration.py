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


from myreco.domain.users.models import UsersModel, GrantsModel, URIsModel, MethodsModel
from myreco.base.models.sqlalchemy_redis import SQLAlchemyRedisModelBase
from myreco.base.http_api import HttpAPI
from myreco.base.models.base import get_model_schema
from unittest import mock
from base64 import b64encode
from pytest_falcon.plugin import Client

import pytest
import json
import os.path


@pytest.fixture
def model_base():
    return SQLAlchemyRedisModelBase


@pytest.fixture
def init_(session):
    uris = [{'uri': '/test2'}, {'uri': '/test3'}, {'uri': '/users/test'}]
    URIsModel.insert(session, uris[0])
    URIsModel.insert(session, uris[1])
    URIsModel.insert(session, uris[2])

    user = {
        'name': 'test',
        'email': 'test',
        'password': 'test',
        'admin': True
    }
    UsersModel.insert(session, user)

    grants = [{
        'uri': {'uri': '/test'},
        'method': {'method': 'post'}
    }]
    GrantsModel.insert(session, grants)

    methods = [{'method': 'put'}, {'method': 'get'}]
    MethodsModel.insert(session, methods[0])
    MethodsModel.insert(session, methods[1])


    grants = [{
        'uri_id': 3,
        'method_id': 3
    }]
    GrantsModel.insert(session, grants)


@pytest.fixture
def app(session, init_):
    return HttpAPI([UsersModel], session.bind)


@pytest.fixture
def headers():
    return {
        'Authorization': b64encode('test:test'.encode()).decode()
    }


class TestUsersResourcePost(object):
    def test_post_valid_grants_update(self, client, headers, session):
        URIsModel.insert(session, {'uri': '/users/test2'})
        user = [{
            'name': 'test2',
            'email': 'test2',
            'password': 'test',
            'grants': [{
                'uri_id': 2,
                'method_id': 2
            }]
        }]
        resp = client.post('/users', data=json.dumps(user), headers=headers)

        assert resp.status_code == 201
        assert json.loads(resp.body) == [{
            'id': 'test2:test',
            'name': 'test2',
            'email': 'test2',
            'password': 'test',
            'grants': [{
                'method_id': 2,
                'uri_id': 2,
                'method': {'id': 2, 'method': 'post'},
                'uri': {'id': 2, 'uri': '/test3'}
            },{
                'method_id': 1,
                'uri_id': 5,
                'method': {'id': 1, 'method': 'patch'},
                'uri': {'id': 5, 'uri': '/users/test2'}
            }],
            'stores': [],
            'admin': False
        }]

    def test_post_valid_with_grants_insert_and_uri_and_method_update(
            self, client, headers, session):
        GrantsModel.insert(session, {'uri': {'uri': '/users/test2'}, 'method_id': 1})
        user = [{
            'name': 'test2',
            'email': 'test2',
            'password': 'test',
            'grants': [{
                'uri': {'id': 2, '_update': True},
                'method': {'id': 1, '_update': True}
            }]
        }]
        resp = client.post('/users', data=json.dumps(user), headers=headers)

        assert resp.status_code == 201
        assert json.loads(resp.body) == [{
            'id': 'test2:test',
            'name': 'test2',
            'email': 'test2',
            'password': 'test',
            'grants': [{
                'method_id': 1,
                'uri_id': 2,
                'method': {'id': 1, 'method': 'patch'},
                'uri': {'id': 2, 'uri': '/test3'}
            },{
                'uri_id': 5,
                'method': {'id': 1, 'method': 'patch'},
                'method_id': 1,
                'uri': {'id': 5, 'uri': '/users/test2'}
            }],
            'stores': [],
            'admin': False
        }]

    def test_post_valid_with_grants_uri_and_method_insert(
            self, client, headers):
        user = [{
            'name': 'test2',
            'email': 'test2',
            'password': 'test',
            'grants': [{
                'uri': {'uri': '/test4'},
                'method': {'method': 'delete'}
            }]
        }]
        resp = client.post('/users', data=json.dumps(user), headers=headers)

        assert resp.status_code == 201
        assert json.loads(resp.body) == [{
            'id': 'test2:test',
            'name': 'test2',
            'email': 'test2',
            'password': 'test',
            'grants': [{
                'method_id': 5,
                'uri_id': 5,
                'method': {'id': 5, 'method': 'delete'},
                'uri': {'id': 5, 'uri': '/test4'}
            },{
                'uri_id': 6,
                'method': {
                    'id': 1,
                    'method': 'patch'
                },
                'method_id': 1,
                'uri': {
                    'id': 6,
                    'uri': '/users/test2'
                }
            }],
            'stores': [],
            'admin': False
        }]

    def test_post_invalid_json(self, client, headers, root_path):
        user = [{
            'name': 'test2',
            'email': 'test2',
            'password': 'test',
            'grants': [{
                'test': 1,
                'method_id': 1
            }]
        }]
        resp = client.post('/users', data=json.dumps(user), headers=headers)

        assert resp.status_code == 400
        result = json.loads(resp.body)
        message = result['error'].pop('message')
        expected_schema = get_model_schema(root_path + '/../myreco/domain/users/models.py')

        assert message == \
                "{'method_id': 1, 'test': 1} is not valid under any of the given schemas" \
            or message == \
                "{'test': 1, 'method_id': 1} is not valid under any of the given schemas"
        assert result == {
            'error': {
                'input': {'method_id': 1, 'test': 1},
                'schema': expected_schema['definitions']['grants']
            }
        }


class TestUsersResourcePutInsert(object):
    def test_put_with_ambiguous_ids(self, client, headers, root_path):
        user = {
            'name': 'test2',
            'email': 'test22',
            'password': 'test',
            'grants': [{
                'uri_id': 1,
                'method_id': 1,
                '_update': True
            }]
        }
        resp = client.put('/users/test2', body=json.dumps(user), headers=headers)
        expected_schema = get_model_schema(root_path + '/../myreco/domain/users/models.py')
        expected_schema = {
            'definitions': expected_schema['definitions'],
            '$ref': '#/definitions/schema_with_grants'
        }

        assert resp.status_code == 400
        assert json.loads(resp.body) == {
            'error': {
                'schema': expected_schema,
                'input': {
                    'body': {
                        'grants': [{
                            'method_id': 1,
                            'uri_id': 1,
                            '_update': True
                        }],
                    'name': 'test2',
                    'email': 'test22',
                    'password': 'test'
                },
                'uri': {'email': 'test2'}
            },
            'message': "Ambiguous value for 'email'"}
        }

    def test_put_with_insert_and_grants_update(self, client, headers):
        user = {
            'name': 'test2',
            'email': 'test2',
            'password': 'test',
            'grants': [{
                'uri_id': 1,
                'method_id': 1
            }]
        }
        resp = client.put('/users/test2', body=json.dumps(user), headers=headers)

        assert resp.status_code == 201
        assert json.loads(resp.body) == {
            'id': 'test2:test',
            'name': 'test2',
            'email': 'test2',
            'password': 'test',
            'stores': [],
            'admin': False,
            'grants': [{
                'method_id': 1,
                'uri_id': 1,
                'method': {'id': 1, 'method': 'patch'},
                'uri': {'id': 1, 'uri': '/test2'}
            },{
                'uri_id': 5,
                'method': {
                    'id': 1,
                    'method': 'patch'
                },
                'method_id': 1,
                'uri': {
                    'id': 5,
                    'uri': '/users/test2'
                }
            }]
        }

    def test_put_with_insert_and_grants_insert(self, client, headers):
        user = {
            'name': 'test2',
            'email': 'test2',
            'password': 'test',
            'grants': [{
                'uri': {'uri': '/test4'},
                'method': {'method': 'delete'}
            }]
        }
        resp = client.put('/users/test2', body=json.dumps(user), headers=headers)

        assert resp.status_code == 201
        assert json.loads(resp.body) == {
            'id': 'test2:test',
            'name': 'test2',
            'email': 'test2',
            'password': 'test',
            'stores': [],
            'admin': False,
            'grants': [{
                'method_id': 5,
                'uri_id': 5,
                'method': {'id': 5, 'method': 'delete'},
                'uri': {'id': 5, 'uri': '/test4'}
            },{
                'uri_id': 6,
                'method': {
                    'id': 1,
                    'method': 'patch'
                },
                'method_id': 1,
                'uri': {
                    'id': 6,
                    'uri': '/users/test2'
                }
            }]
        }


class TestUsersResourcePutUpdateOne(object):
    def test_put_update_and_grants_update(self, client, headers):
        user = {
            'name': 'test2',
            'password': 'test',
            'email': 'test2',
            'grants': [{
                'uri_id': 1,
                'method_id': 1
            }]
        }
        resp = client.put('/users/test2', body=json.dumps(user), headers=headers)
        assert resp.status_code == 201

        user = {
            'name': 'test2_updated',
            'email': 'test2',
            'password': 'test_updated',
            'grants': [{
                'uri_id': 3,
                'method_id': 3,
                '_update': True
            }]
        }
        resp = client.put('/users/test2', body=json.dumps(user), headers=headers)

        assert resp.status_code == 200
        assert json.loads(resp.body) == {
            'id': 'test2:test_updated',
            'name': 'test2_updated',
            'email': 'test2',
            'password': 'test_updated',
            'stores': [],
            'admin': False,
            'grants': [{
                'method_id': 1,
                'uri_id': 1,
                'method': {'id': 1, 'method': 'patch'},
                'uri': {'id': 1, 'uri': '/test2'}
            },{
                'method_id': 3,
                'uri_id': 3,
                'method': {'id': 3, 'method': 'put'},
                'uri': {'id': 3, 'uri': '/users/test'}
            },{
                'uri_id': 5,
                'method': {
                    'id': 1,
                    'method': 'patch'
                },
                'method_id': 1,
                'uri': {
                    'id': 5,
                    'uri': '/users/test2'
                }
            }]
        }

    def test_put_update_and_grants_remove(self, client, headers):
        user = {
            'name': 'test2',
            'email': 'test2',
            'password': 'test',
            'grants': [{
                'uri_id': 1,
                'method_id': 1
            }]
        }
        resp = client.put('/users/test2', body=json.dumps(user), headers=headers)
        assert resp.status_code == 201

        user = {
            'name': 'test2_updated',
            'email': 'test2',
            'password': 'test_updated',
            'grants': [{
                'uri_id': 1,
                'method_id': 1,
                '_remove': True
            }]
        }
        resp = client.put('/users/test2', body=json.dumps(user), headers=headers)

        assert resp.status_code == 200
        assert json.loads(resp.body) == {
            'id': 'test2:test_updated',
            'name': 'test2_updated',
            'email': 'test2',
            'password': 'test_updated',
            'stores': [],
            'grants': [{
                'uri_id': 5,
                'method': {
                    'id': 1,
                    'method': 'patch'
                },
                'method_id': 1,
                'uri': {
                    'id': 5,
                    'uri': '/users/test2'
                }
            }],
            'admin': False
        }

    def test_put_update_and_grants_update_and_grants_remove(self, client, headers):
        user = {
            'name': 'test2',
            'email': 'test2',
            'password': 'test',
            'grants': [{
                'uri_id': 1,
                'method_id': 1
            }]
        }
        resp = client.put('/users/test2', body=json.dumps(user), headers=headers)
        assert resp.status_code == 201

        user = {
            'name': 'test2_updated',
            'email': 'test2',
            'password': 'test_updated',
            'grants': [{
                'uri_id': 3,
                'method_id': 3,
                '_update': True
            },{
                'uri_id': 1,
                'method_id': 1,
                '_remove': True
            }]
        }
        resp = client.put('/users/test2', body=json.dumps(user), headers=headers)

        assert resp.status_code == 200
        assert json.loads(resp.body) == {
            'id': 'test2:test_updated',
            'name': 'test2_updated',
            'email': 'test2',
            'password': 'test_updated',
            'stores': [],
            'admin': False,
            'grants': [{
                'method_id': 3,
                'uri_id': 3,
                'method': {'id': 3, 'method': 'put'},
                'uri': {'id': 3, 'uri': '/users/test'}
            },{
                'uri_id': 5,
                'method': {
                    'id': 1,
                    'method': 'patch'
                },
                'method_id': 1,
                'uri': {
                    'id': 5,
                    'uri': '/users/test2'
                }
            }]
        }

    def test_put_update_primary_key_with_redis(self, session, init_, headers):
        redis = mock.MagicMock()
        redis.hmget.return_value = [None]
        client = Client(HttpAPI([UsersModel], session.bind, redis))
        user = {
            'name': 'test2',
            'password': 'test',
            'email': 'test2',
            'grants': [{
                'uri_id': 1,
                'method_id': 1
            }]
        }
        resp = client.put('/users/test2', body=json.dumps(user), headers=headers)
        assert resp.status_code == 201

        user = {
            'name': 'test2_updated',
            'email': 'test2',
            'password': 'test_updated',
            'grants': [{
                'uri_id': 1,
                'method_id': 1,
                '_update': True
            }]
        }
        session.redis_bind = mock.MagicMock()
        resp = client.put('/users/test2', body=json.dumps(user), headers=headers)

        assert resp.status_code == 200
        assert json.loads(resp.body) == {
            'id': 'test2:test_updated',
            'name': 'test2_updated',
            'email': 'test2',
            'password': 'test_updated',
            'stores': [],
            'admin': False,
            'grants': [{
                'method_id': 1,
                'uri_id': 1,
                'method': {'id': 1, 'method': 'patch'},
                'uri': {'id': 1, 'uri': '/test2'}
            },{
                'uri_id': 5,
                'method': {
                    'id': 1,
                    'method': 'patch'
                },
                'method_id': 1,
                'uri': {
                    'id': 5,
                    'uri': '/users/test2'
                }
            }]
        }
        assert redis.hdel.call_args_list == [mock.call('users', "('test2:test',)")]


class TestUsersResourcePutUpdateMany(object):
    def test_put_update_and_grants_update(self, client, headers):
        user = {
            'name': 'test2',
            'email': 'test2',
            'password': 'test',
            'grants': [{
                'uri_id': 1,
                'method_id': 1
            }]
        }
        resp = client.put('/users/test2', body=json.dumps(user), headers=headers)
        assert resp.status_code == 201

        users = [{
            'id': 'test2:test',
            'name': 'test2_updated',
            'email': 'test2_updated',
            'password': 'test_updated',
            'grants': [{
                'uri_id': 3,
                'method_id': 3,
                '_update': True
            }]
        }]
        resp = client.put('/users', body=json.dumps(users), headers=headers)

        assert resp.status_code == 200
        assert json.loads(resp.body) == [{
            'id': 'test2_updated:test_updated',
            'name': 'test2_updated',
            'email': 'test2_updated',
            'password': 'test_updated',
            'stores': [],
            'admin': False,
            'grants': [{
                'method_id': 1,
                'uri_id': 1,
                'method': {'id': 1, 'method': 'patch'},
                'uri': {'id': 1, 'uri': '/test2'}
            },{
                'method_id': 3,
                'uri_id': 3,
                'method': {'id': 3, 'method': 'put'},
                'uri': {'id': 3, 'uri': '/users/test'}
            },{
                'uri_id': 5,
                'method': {
                    'id': 1,
                    'method': 'patch'
                },
                'method_id': 1,
                'uri': {
                    'id': 5,
                    'uri': '/users/test2'
                }
            }]
        }]

    def test_put_update_and_grants_remove(self, client, headers):
        user = {
            'name': 'test2',
            'email': 'test2',
            'password': 'test',
            'grants': [{
                'uri_id': 1,
                'method_id': 1
            }]
        }
        resp = client.put('/users/test2', body=json.dumps(user), headers=headers)
        assert resp.status_code == 201

        users = [{
            'id': 'test2:test',
            'name': 'test2_updated',
            'email': 'test2_updated',
            'password': 'test_updated',
            'grants': [{
                'uri_id': 1,
                'method_id': 1,
                '_remove': True
            }]
        }]
        resp = client.put('/users', body=json.dumps(users), headers=headers)

        assert resp.status_code == 200
        assert json.loads(resp.body) == [{
            'id': 'test2_updated:test_updated',
            'name': 'test2_updated',
            'email': 'test2_updated',
            'password': 'test_updated',
            'stores': [],
            'grants': [{
                'uri_id': 5,
                'method': {
                    'id': 1,
                    'method': 'patch'
                },
                'method_id': 1,
                'uri': {
                    'id': 5,
                    'uri': '/users/test2'
                }
            }],
            'admin': False
        }]

    def test_put_update_and_grants_update_and_grants_remove(self, client, headers):
        user = {
            'name': 'test2',
            'email': 'test2',
            'password': 'test',
            'grants': [{
                'uri_id': 1,
                'method_id': 1
            }]
        }
        resp = client.put('/users/test2', body=json.dumps(user), headers=headers)
        assert resp.status_code == 201

        users = [{
            'id': 'test2:test',
            'name': 'test2_updated',
            'email': 'test2_updated',
            'password': 'test_updated',
            'grants': [{
                'uri_id': 3,
                'method_id': 3,
                '_update': True
            },{
                'uri_id': 1,
                'method_id': 1,
                '_remove': True
            }]
        }]
        resp = client.put('/users', body=json.dumps(users), headers=headers)

        assert resp.status_code == 200
        assert json.loads(resp.body) == [{
            'id': 'test2_updated:test_updated',
            'name': 'test2_updated',
            'email': 'test2_updated',
            'password': 'test_updated',
            'stores': [],
            'admin': False,
            'grants': [{
                'method_id': 3,
                'uri_id': 3,
                'method': {'id': 3, 'method': 'put'},
                'uri': {'id': 3, 'uri': '/users/test'}
            },{
                'uri_id': 5,
                'method': {'id': 1, 'method': 'patch'},
                'method_id': 1,
                'uri': {'id': 5, 'uri': '/users/test2'}
            }]
        }]


class TestUsersResourcePatchOne(object):
    def test_patch_one_property(self, client, headers):
        user = [{
            'name': 'test2',
            'email': 'test2',
            'password': 'test'
        }]
        resp = client.post('/users', body=json.dumps(user), headers=headers)
        assert resp.status_code == 201

        users = {'name': 'test2_updated'}
        resp = client.patch('/users/test2', body=json.dumps(users), headers=headers)

        assert resp.status_code == 200
        assert json.loads(resp.body) == {
            'id': 'test2:test',
            'name': 'test2_updated',
            'email': 'test2',
            'password': 'test',
            'stores': [],
            'admin': False,
            'grants': [{
                'uri_id': 5,
                'method': {
                    'id': 1,
                    'method': 'patch'
                },
                'method_id': 1,
                'uri': {
                    'id': 5,
                    'uri': '/users/test2'
                }
            }]
        }

    def test_patch_two_properties(self, client, headers):
        user = [{
            'name': 'test2',
            'email': 'test2',
            'password': 'test'
        }]
        resp = client.post('/users', body=json.dumps(user), headers=headers)
        assert resp.status_code == 201

        users = {
            'email': 'test22',
            'password': 'test2'
        }
        resp = client.patch('/users/test2', body=json.dumps(users), headers=headers)

        assert resp.status_code == 200
        assert json.loads(resp.body) == {
            'id': 'test22:test2',
            'name': 'test2',
            'email': 'test22',
            'password': 'test2',
            'stores': [],
            'admin': False,
            'grants': [{
                'uri_id': 5,
                'method': {
                    'id': 1,
                    'method': 'patch'
                },
                'method_id': 1,
                'uri': {
                    'id': 5,
                    'uri': '/users/test2'
                }
            }]
        }


class TestUsersResourcePatchMany(object):
    def test_patch_one_property(self, client, headers):
        user = [{
            'name': 'test2',
            'email': 'test2',
            'password': 'test'
        }]
        resp = client.post('/users', body=json.dumps(user), headers=headers)
        assert resp.status_code == 201

        users = [{'email': 'test2', 'name': 'test2_updated'}]
        resp = client.patch('/users', body=json.dumps(users), headers=headers)

        assert resp.status_code == 200
        assert json.loads(resp.body) == [{
            'id': 'test2:test',
            'name': 'test2_updated',
            'email': 'test2',
            'password': 'test',
            'stores': [],
            'admin': False,
            'grants': [{
                'uri_id': 5,
                'method': {
                    'id': 1,
                    'method': 'patch'
                },
                'method_id': 1,
                'uri': {
                    'id': 5,
                    'uri': '/users/test2'
                }
            }]
        }]

    def test_patch_two_properties(self, client, headers):
        user = [{
            'name': 'test2',
            'email': 'test2',
            'password': 'test'
        }]
        resp = client.post('/users', body=json.dumps(user), headers=headers)
        assert resp.status_code == 201

        users = {
            'email': 'test2',
            'name': 'test22',
            'password': 'test2'
        }
        resp = client.patch('/users/test2', body=json.dumps(users), headers=headers)

        assert resp.status_code == 200
        assert json.loads(resp.body) == {
            'id': 'test2:test2',
            'name': 'test22',
            'email': 'test2',
            'password': 'test2',
            'stores': [],
            'admin': False,
            'grants': [{
                'uri_id': 5,
                'method': {
                    'id': 1,
                    'method': 'patch'
                },
                'method_id': 1,
                'uri': {
                    'id': 5,
                    'uri': '/users/test2'
                }
            }]
        }


class TestUsersResourceDeleteGet(object):
    def test_delete_one(self, client, headers):
        user = [{
            'name': 'test2',
            'email': 'test2',
            'password': 'test'
        }]
        resp = client.post('/users', body=json.dumps(user), headers=headers)
        assert resp.status_code == 201

        resp = client.get('/users/test2', body='', headers=headers)
        assert resp.status_code == 200

        resp = client.delete('/users/test2', headers=headers)
        assert resp.status_code == 204

        resp = client.get('/users/test2', headers=headers)
        assert resp.status_code == 404

    def test_delete_many(self, client, headers):
        user = [{
            'name': 'test2',
            'email': 'test2',
            'password': 'test'
        }]
        resp = client.post('/users', body=json.dumps(user), headers=headers)
        assert resp.status_code == 201

        resp = client.get('/users', body=json.dumps([{'email': 'test2'}]), headers=headers)
        assert resp.status_code == 200

        resp = client.delete('/users', body=json.dumps([{'email': 'test2'}]), headers=headers)
        assert resp.status_code == 204

        resp = client.get('/users', body=json.dumps([{'email': 'test2'}]), headers=headers)
        assert resp.status_code == 404


class TestUsersResourceSchemas(object):
    def test_get_put_schemas(self, client, headers, root_path):
        resp = client.get('/users/_schema/', headers=headers)
        expected_schema = get_model_schema(root_path + '/../myreco/domain/users/models.py')

        assert resp.status_code == 200
        assert json.loads(resp.body) == expected_schema
