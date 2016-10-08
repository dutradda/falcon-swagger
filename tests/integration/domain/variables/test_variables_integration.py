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


from tests.integration.fixtures_models import (
    UsersModel, SQLAlchemyRedisModelBase, StoresModel, VariablesModel)
from myreco.base.http_api import HttpAPI
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

    store = {
        'name': 'test',
        'country': 'test'
    }
    StoresModel.insert(session, store)
    return HttpAPI([VariablesModel], session.bind, FakeStrictRedis())


@pytest.fixture
def headers():
    return {
        'Authorization': b64encode('test:test'.encode()).decode()
    }



class TestVariablesModelPost(object):

    def test_post_without_body(self, client, headers):
        resp = client.post('/variables/', headers=headers)
        assert resp.status_code == 400
        assert json.loads(resp.body) == {'error': 'Request body is missing'}

    def test_post_with_invalid_body(self, client, headers):
        resp = client.post('/variables/', headers=headers, body='[{}]')
        assert resp.status_code == 400
        assert json.loads(resp.body) ==  {
            'error': {
                'input': {},
                'message': "'name' is a required property",
                'schema': {
                    'type': 'object',
                    'additionalProperties': False,
                    'required': ['name', 'store_id'],
                    'properties': {
                        'name': {'type': 'string'},
                        'store_id': {'type': 'integer'}
                    }
                }
            }
        }

    def test_post(self, client, headers):
        body = [{
            'name': 'test',
            'store_id': 1
        }]
        resp = client.post('/variables/', headers=headers, body=json.dumps(body))
        body[0]['id'] = 1

        assert resp.status_code == 201
        assert json.loads(resp.body) ==  body


class TestVariablesModelGet(object):

    def test_get_not_found(self, client, headers):
        resp = client.get('/variables/', headers=headers)
        assert resp.status_code == 404

    def test_get_invalid_with_body(self, client, headers):
        resp = client.get('/variables/', headers=headers, body='{}')
        assert resp.status_code == 400
        assert json.loads(resp.body) == {'error': 'Request body is not acceptable'}

    def test_get(self, client, headers):
        body = [{
            'name': 'test',
            'store_id': 1
        }]
        client.post('/variables/', headers=headers, body=json.dumps(body))
        body[0]['id'] = 1

        resp = client.get('/variables/', headers=headers)
        assert resp.status_code == 200
        assert json.loads(resp.body) ==  body


class TestVariablesModelUriTemplatePatch(object):

    def test_patch_without_body(self, client, headers):
        resp = client.patch('/variables/1/', headers=headers, body='')
        assert resp.status_code == 400
        assert json.loads(resp.body) == {'error': 'Request body is missing'}

    def test_patch_with_invalid_body(self, client, headers):
        resp = client.patch('/variables/1/', headers=headers, body='{}')
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
                        'store_id': {'type': 'integer'}
                    }
                }
            }
        }

    def test_patch_not_found(self, client, headers):
        body = {
            'name': 'test',
            'store_id': 1
        }
        resp = client.patch('/variables/1/', headers=headers, body=json.dumps(body))
        assert resp.status_code == 404

    def test_patch(self, client, headers):
        body = [{
            'name': 'test',
            'store_id': 1
        }]
        obj = json.loads(client.post('/variables/', headers=headers, body=json.dumps(body)).body)[0]

        body = {
            'name': 'test2'
        }
        resp = client.patch('/variables/1/', headers=headers, body=json.dumps(body))
        obj['name'] = 'test2'

        assert resp.status_code == 200
        assert json.loads(resp.body) ==  obj


class TestVariablesModelUriTemplateDelete(object):

    def test_delete_with_body(self, client, headers):
        resp = client.delete('/variables/1/', headers=headers, body='{}')
        assert resp.status_code == 400
        assert json.loads(resp.body) == {'error': 'Request body is not acceptable'}

    def test_delete(self, client, headers):
        body = [{
            'name': 'test',
            'store_id': 1
        }]
        client.post('/variables/', headers=headers, body=json.dumps(body))

        resp = client.get('/variables/1/', headers=headers)
        assert resp.status_code == 200

        resp = client.delete('/variables/1/', headers=headers)
        assert resp.status_code == 204

        resp = client.get('/variables/1/', headers=headers)
        assert resp.status_code == 404


class TestVariablesModelUriTemplateGet(object):

    def test_get_with_body(self, client, headers):
        resp = client.get('/variables/1/', headers=headers, body='{}')
        assert resp.status_code == 400
        assert json.loads(resp.body) == {'error': 'Request body is not acceptable'}

    def test_get_not_found(self, client, headers):
        resp = client.get('/variables/1/', headers=headers)
        assert resp.status_code == 404

    def test_get(self, client, headers):
        body = [{
            'name': 'test',
            'store_id': 1
        }]
        client.post('/variables/', headers=headers, body=json.dumps(body))

        resp = client.get('/variables/1/', headers=headers)
        body[0]['id'] = 1
        assert resp.status_code == 200
        assert json.loads(resp.body) == body[0]
