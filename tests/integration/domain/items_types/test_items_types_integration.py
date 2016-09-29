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
from myreco.base.http_api import HttpAPI
from myreco.domain.items_types.models import ItemsTypesModel
from myreco.domain.users.models import UsersModel
from unittest import mock
from base64 import b64encode
from fakeredis import FakeStrictRedis
import pytest
import json


@pytest.fixture
def model_base():
    return SQLAlchemyRedisModelBase


@pytest.fixture
def app(session):
    user = {
        'name': 'test',
        'email': 'test',
        'password': 'test',
        'admin': True
    }
    UsersModel.insert(session, user)

    return HttpAPI([ItemsTypesModel], session.bind, FakeStrictRedis())


@pytest.fixture
def headers():
    return {
        'Authorization': b64encode('test:test'.encode()).decode()
    }


class TestItemsTypesModelPost(object):

    def test_post_without_body(self, client, headers):
        resp = client.post('/items_types/', headers=headers)
        assert resp.status_code == 400
        assert json.loads(resp.body) == {'error': 'Request body is missing'}

    def test_post_with_invalid_body(self, client, headers):
        resp = client.post('/items_types/', headers=headers, body='[{}]')
        assert resp.status_code == 400
        assert json.loads(resp.body) ==  {
            'error': {
                'input': {},
                'message': "'name' is a required property",
                'schema': {
                    'type': 'object',
                    'additionalProperties': False,
                    'required': ['name', 'id_names', 'schema'],
                    'properties': {
                        'name': {'type': 'string'},
                        'id_names': {
                            'type': 'array',
                            'minItems': 1,
                            'items': {'type': 'string'}
                        },
                        'schema': {'$ref': 'http://json-schema.org/draft-04/schema#'}
                    }
                }
            }
        }

    def test_post(self, client, headers):
        body = [{
            'name': 'test',
            'id_names': ['test'],
            'schema': {}
        }]
        resp = client.post('/items_types/', headers=headers, body=json.dumps(body))
        body[0]['id'] = 1

        assert resp.status_code == 201
        assert json.loads(resp.body) ==  body


class TestItemsTypesModelGet(object):

    def test_get_not_found(self, client, headers):
        resp = client.get('/items_types/', headers=headers)
        assert resp.status_code == 404

    def test_get_invalid_with_body(self, client, headers):
        resp = client.get('/items_types/', headers=headers, body='{}')
        assert resp.status_code == 400
        assert json.loads(resp.body) == {'error': 'Request body is not acceptable'}

    def test_get(self, client, headers):
        body = [{
            'name': 'test',
            'id_names': ['test'],
            'schema': {}
        }]
        client.post('/items_types/', headers=headers, body=json.dumps(body))
        body[0]['id'] = 1

        resp = client.get('/items_types/', headers=headers)
        assert resp.status_code == 200
        assert json.loads(resp.body) ==  body


class TestItemsTypesModelUriTemplatePatch(object):

    def test_patch_without_body(self, client, headers):
        resp = client.patch('/items_types/1/', headers=headers, body='')
        assert resp.status_code == 400
        assert json.loads(resp.body) == {'error': 'Request body is missing'}

    def test_patch_with_invalid_body(self, client, headers):
        resp = client.patch('/items_types/1/', headers=headers, body='{}')
        assert resp.status_code == 400
        assert json.loads(resp.body) ==  {
            'error': {
                'input': {},
                'message': '{} does not have enough properties',
                'schema': {
                    'type': 'object',
                    'additionalProperties': False,
                    'minProperties': 1,
                    'properties': {
                        'name': {'type': 'string'},
                        'id_names': {
                            'type': 'array',
                            'minItems': 1,
                            'items': {'type': 'string'}
                        },
                        'schema': {'$ref': 'http://json-schema.org/draft-04/schema#'}
                    }
                }
            }
        }

    def test_patch_not_found(self, client, headers):
        body = {
            'name': 'test',
            'id_names': ['test'],
            'schema': {}
        }
        resp = client.patch('/items_types/1/', headers=headers, body=json.dumps(body))
        assert resp.status_code == 404

    def test_patch(self, client, headers):
        body = [{
            'name': 'test',
            'id_names': ['test'],
            'schema': {}
        }]
        obj = json.loads(client.post('/items_types/', headers=headers, body=json.dumps(body)).body)[0]

        body = {
            'name': 'test2'
        }
        resp = client.patch('/items_types/1/', headers=headers, body=json.dumps(body))
        obj['name'] = 'test2'

        assert resp.status_code == 200
        assert json.loads(resp.body) ==  obj


class TestItemsTypesModelUriTemplateDelete(object):

    def test_delete_with_body(self, client, headers):
        resp = client.delete('/items_types/1/', headers=headers, body='{}')
        assert resp.status_code == 400
        assert json.loads(resp.body) == {'error': 'Request body is not acceptable'}

    def test_delete(self, client, headers):
        body = [{
            'name': 'test',
            'id_names': ['test'],
            'schema': {}
        }]
        client.post('/items_types/', headers=headers, body=json.dumps(body))

        resp = client.get('/items_types/1/', headers=headers)
        assert resp.status_code == 200

        resp = client.delete('/items_types/1/', headers=headers)
        assert resp.status_code == 204

        resp = client.get('/items_types/1/', headers=headers)
        assert resp.status_code == 404


class TestItemsTypesModelUriTemplateGet(object):

    def test_get_with_body(self, client, headers):
        resp = client.get('/items_types/1/', headers=headers, body='{}')
        assert resp.status_code == 400
        assert json.loads(resp.body) == {'error': 'Request body is not acceptable'}

    def test_get_not_found(self, client, headers):
        resp = client.get('/items_types/1/', headers=headers)
        assert resp.status_code == 404

    def test_get(self, client, headers):
        body = [{
            'name': 'test',
            'id_names': ['test'],
            'schema': {}
        }]
        client.post('/items_types/', headers=headers, body=json.dumps(body))

        resp = client.get('/items_types/1/', headers=headers)
        body[0]['id'] = 1
        assert resp.status_code == 200
        assert json.loads(resp.body) == body[0]
