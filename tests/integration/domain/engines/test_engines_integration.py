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
from myreco.domain.engines.models import EnginesModel, EnginesTypesNamesModel
from myreco.domain.items_types.models import ItemsTypesModel
from myreco.domain.stores.model import StoresModel
from myreco.domain.users.models import UsersModel
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

    EnginesTypesNamesModel.insert(session, {'name': 'top_seller'})

    item_type = {
        'name': 'products',
        'id_names_json': '["sku"]',
        'schema_json': '{}'
    }
    ItemsTypesModel.insert(session, item_type)

    return HttpAPI([EnginesModel], session.bind, FakeStrictRedis())


@pytest.fixture
def headers():
    return {
        'Authorization': b64encode('test:test'.encode()).decode()
    }



class TestEnginesModelPost(object):

    def test_post_without_body(self, client, headers):
        resp = client.post('/engines/', headers=headers)
        assert resp.status_code == 400
        assert json.loads(resp.body) == {'error': 'Request body is missing'}

    def test_post_with_invalid_body(self, client, headers):
        resp = client.post('/engines/', headers=headers, body='[{}]')
        assert resp.status_code == 400
        assert json.loads(resp.body) ==  {
            'error': {
                'input': {},
                'message': "'configuration' is a required property",
                'schema': {
                    'type': 'object',
                    'additionalProperties': False,
                    'required': ['configuration', 'store_id', 'type_name_id', 'item_type_id'],
                    'properties': {
                        'name': {'type': 'string'},
                        'configuration': {'$ref': 'http://json-schema.org/draft-04/schema#'},
                        'store_id': {'type': 'integer'},
                        'type_name_id': {'type': 'integer'},
                        'item_type_id': {'type': 'integer'},
                         'filters': {
                            'minItems': 1,
                            'type': 'array',
                            'items': {
                                'type': 'object',
                                'required': ['name'],
                                'additionalProperties': False,
                                'properties': {
                                    '_operation': {'enum': ['insert']},
                                    'name': {'type': 'string'}
                                }
                            }
                        }
                    }
                }
            }
        }

    def test_post_with_invalid_filter(self, client, headers):
        body = [{
            'name': 'Seven Days Top Seller',
            'configuration': {"days_interval": 7},
            'store_id': 1,
            'type_name_id': 1,
            'item_type_id': 1,
            'filters': [{'name': 'test', '_operation': 'insert'}]
        }]
        resp = client.post('/engines/', headers=headers, body=json.dumps(body))
        assert resp.status_code == 400
        assert json.loads(resp.body) ==  {
            'error': {
                'input': {
                    'filters_names': [
                        'test'
                    ]
                },
                'schema': {
                    'available_filters': []
                },
                'message': "invalid filter 'test'"
            }
        }

    def test_post(self, client, headers):
        body = [{
            'name': 'Seven Days Top Seller',
            'configuration': {"days_interval": 7},
            'store_id': 1,
            'type_name_id': 1,
            'item_type_id': 1
        }]
        resp = client.post('/engines/', headers=headers, body=json.dumps(body))
        body[0]['id'] = 1
        body[0]['filters'] = []
        body[0]['variables'] = ['input_list']
        body[0]['store'] = {'id': 1, 'name': 'test', 'country': 'test'}
        body[0]['type_name'] = {'id': 1, 'name': 'top_seller'}
        body[0]['item_type'] = item_type = {
            'id': 1,
            'name': 'products',
            'id_names': ["sku"],
            'schema': {},
            'available_filters': []
        }

        assert resp.status_code == 201
        assert json.loads(resp.body) ==  body


class TestEnginesModelGet(object):

    def test_get_not_found(self, client, headers):
        resp = client.get('/engines/', headers=headers)
        assert resp.status_code == 404

    def test_get_invalid_with_body(self, client, headers):
        resp = client.get('/engines/', headers=headers, body='{}')
        assert resp.status_code == 400
        assert json.loads(resp.body) == {'error': 'Request body is not acceptable'}

    def test_get(self, client, headers):
        body = [{
            'name': 'Seven Days Top Seller',
            'configuration': {"days_interval": 7},
            'store_id': 1,
            'type_name_id': 1,
            'item_type_id': 1
        }]
        client.post('/engines/', headers=headers, body=json.dumps(body))
        body[0]['id'] = 1
        body[0]['filters'] = []
        body[0]['variables'] = ['input_list']
        body[0]['store'] = {'id': 1, 'name': 'test', 'country': 'test'}
        body[0]['type_name'] = {'id': 1, 'name': 'top_seller'}
        body[0]['item_type'] = item_type = {
            'id': 1,
            'name': 'products',
            'id_names': ["sku"],
            'schema': {},
            'available_filters': []
        }

        resp = client.get('/engines/', headers=headers)
        assert resp.status_code == 200
        assert json.loads(resp.body) ==  body


class TestEnginesModelUriTemplatePatch(object):

    def test_patch_without_body(self, client, headers):
        resp = client.patch('/engines/1/', headers=headers, body='')
        assert resp.status_code == 400
        assert json.loads(resp.body) == {'error': 'Request body is missing'}

    def test_patch_with_invalid_body(self, client, headers):
        resp = client.patch('/engines/1/', headers=headers, body='{}')
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
                        'configuration': {'$ref': 'http://json-schema.org/draft-04/schema#'},
                        'store_id': {'type': 'integer'},
                        'type_name_id': {'type': 'integer'},
                        'item_type_id': {'type': 'integer'},
                         'filters': {
                            'minItems': 1,
                            'type': 'array',
                            'items': {
                                'type': 'object',
                                'required': ['name'],
                                'additionalProperties': False,
                                'properties': {
                                    '_operation': {'enum': ['insert']},
                                    'name': {'type': 'string'}
                                }
                            }
                        }
                    }
                }
            }
        }

    def test_patch_with_invalid_configuration(self, client, headers):
        body = [{
            'name': 'Seven Days Top Seller',
            'configuration': {"days_interval": 7},
            'store_id': 1,
            'type_name_id': 1,
            'item_type_id': 1
        }]
        client.post('/engines/', headers=headers, body=json.dumps(body))

        body = {
            'configuration': {}
        }
        resp = client.patch('/engines/1/', headers=headers, body=json.dumps(body))
        assert resp.status_code == 400
        assert json.loads(resp.body) ==  {
            'error': {
                'input': {},
                'message': "'days_interval' is a required property",
                'schema': {
                    'type': 'object',
                    'additionalProperties': False,
                    'required': ['days_interval'],
                    'properties': {
                        'days_interval': {'type': 'integer'}
                    }
                }
            }
        }

    def test_patch_not_found(self, client, headers):
        body = {
            'name': 'test',
            'store_id': 1
        }
        resp = client.patch('/engines/1/', headers=headers, body=json.dumps(body))
        assert resp.status_code == 404

    def test_patch(self, client, headers):
        body = [{
            'name': 'Seven Days Top Seller',
            'configuration': {"days_interval": 7},
            'store_id': 1,
            'type_name_id': 1,
            'item_type_id': 1
        }]
        obj = json.loads(client.post('/engines/', headers=headers, body=json.dumps(body)).body)[0]

        body = {
            'name': 'test2'
        }
        resp = client.patch('/engines/1/', headers=headers, body=json.dumps(body))
        obj['name'] = 'test2'

        assert resp.status_code == 200
        assert json.loads(resp.body) ==  obj


class TestEnginesModelUriTemplateDelete(object):

    def test_delete_with_body(self, client, headers):
        resp = client.delete('/engines/1/', headers=headers, body='{}')
        assert resp.status_code == 400
        assert json.loads(resp.body) == {'error': 'Request body is not acceptable'}

    def test_delete(self, client, headers):
        body = [{
            'name': 'Seven Days Top Seller',
            'configuration': {"days_interval": 7},
            'store_id': 1,
            'type_name_id': 1,
            'item_type_id': 1
        }]
        client.post('/engines/', headers=headers, body=json.dumps(body))
        resp = client.get('/engines/1/', headers=headers)
        assert resp.status_code == 200

        resp = client.delete('/engines/1/', headers=headers)
        assert resp.status_code == 204

        resp = client.get('/engines/1/', headers=headers)
        assert resp.status_code == 404


class TestEnginesModelUriTemplateGet(object):

    def test_get_with_body(self, client, headers):
        resp = client.get('/engines/1/', headers=headers, body='{}')
        assert resp.status_code == 400
        assert json.loads(resp.body) == {'error': 'Request body is not acceptable'}

    def test_get_not_found(self, client, headers):
        resp = client.get('/engines/1/', headers=headers)
        assert resp.status_code == 404

    def test_get(self, client, headers):
        body = [{
            'name': 'Seven Days Top Seller',
            'configuration': {"days_interval": 7},
            'store_id': 1,
            'type_name_id': 1,
            'item_type_id': 1
        }]
        client.post('/engines/', headers=headers, body=json.dumps(body))

        resp = client.get('/engines/1/', headers=headers)
        body[0]['id'] = 1
        body[0]['filters'] = []
        body[0]['variables'] = ['input_list']
        body[0]['store'] = {'id': 1, 'name': 'test', 'country': 'test'}
        body[0]['type_name'] = {'id': 1, 'name': 'top_seller'}
        body[0]['item_type'] = item_type = {
            'id': 1,
            'name': 'products',
            'id_names': ["sku"],
            'schema': {},
            'available_filters': []
        }

        assert resp.status_code == 200
        assert json.loads(resp.body) == body[0]
