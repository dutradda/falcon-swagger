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
    SQLAlchemyRedisModelBase, EnginesManagersModel, PlacementsModel,
    UsersModel, StoresModel, VariablesModel, ItemsTypesModel,
    EnginesModel, EnginesTypesNamesModel)
from myreco.base.http_api import HttpAPI
from base64 import b64encode
from fakeredis import FakeStrictRedis
from unittest import mock
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

    EnginesTypesNamesModel.insert(session, {'name': 'visual_similarity'})
    EnginesTypesNamesModel.insert(session, {'name': 'top_seller'})

    schema_json = json.dumps({
        'type': 'object',
        'properties': {
            'filter_test': {'type': 'string'},
            'item_id': {'type': 'integer'}
        }
    })

    item_type = {
        'name': 'products',
        'id_names_json': '["sku"]',
        'schema_json': schema_json
    }
    ItemsTypesModel.insert(session, item_type)
    item_type = {
        'name': 'categories',
        'id_names_json': '["id"]',
        'schema_json': schema_json
    }
    ItemsTypesModel.insert(session, item_type)
    item_type = {
        'name': 'invalid',
        'id_names_json': '["id"]',
        'schema_json': '{"type": "object", "properties": {"item_id": {"type": "string"}}}'
    }
    ItemsTypesModel.insert(session, item_type)

    engine = {
        'name': 'Visual Similarity',
        'configuration_json': json.dumps(
            {'item_id_name': 'item_id', 'aggregators_ids_name': 'filter_test'}),
        'store_id': 1,
        'type_name_id': 1,
        'item_type_id': 1
    }
    EnginesModel.insert(session, engine)
    engine = {
        'name': 'Categories Top Seller',
        'configuration_json': json.dumps(
            {'item_id_name': 'item_id', 'aggregators_ids_name': 'filter_test'}),
        'store_id': 1,
        'type_name_id': 1,
        'item_type_id': 2
    }
    EnginesModel.insert(session, engine)
    engine = {
        'name': 'Invalid Top Seller',
        'configuration_json': '{"days_interval": 7}',
        'store_id': 1,
        'type_name_id': 2,
        'item_type_id': 3
    }
    EnginesModel.insert(session, engine)

    VariablesModel.insert(session, {'name': 'test', 'store_id': 1})
    VariablesModel.insert(session, {'name': 'test2', 'store_id': 1})

    engine_manager = {
        'store_id': 1,
        'engine_id': 1,
        'engine_variables': [{
            '_operation': 'insert',
            'variable_id': 1,
            'inside_engine_name': 'filter_test'
        }]
    }
    EnginesManagersModel.insert(session, engine_manager)

    return HttpAPI([PlacementsModel], session.bind, FakeStrictRedis())


@pytest.fixture
def headers():
    return {
        'Authorization': b64encode('test:test'.encode()).decode()
    }



class TestPlacementsModelPost(object):

    def test_post_without_body(self, client, headers):
        resp = client.post('/placements/', headers=headers)
        assert resp.status_code == 400
        assert json.loads(resp.body) == {'error': 'Request body is missing'}

    def test_post_with_invalid_body(self, client, headers):
        resp = client.post('/placements/', headers=headers, body='[{}]')
        assert resp.status_code == 400
        assert json.loads(resp.body) ==  {
            'error': {
                'input': {},
                'message': "'name' is a required property",
                'schema': {
                    'type': 'object',
                    'additionalProperties': False,
                    'required': ['name', 'variations', 'store_id'],
                    'properties': {
                        'ab_testing': {'type': 'boolean'},
                        'name': {'type': 'string'},
                        'store_id': {'type': 'integer'},
                        'variations': {'$ref': '#/definitions/variations'}
                    }
                }
            }
        }

    def test_post(self, client, headers):
        body = [{
            'store_id': 1,
            'name': 'Placement Test',
            'variations': [{
                '_operation': 'insert',
                'engines_managers': [{'id': 1}]
            }]
        }]
        resp = client.post('/placements/', headers=headers, body=json.dumps(body))
        assert resp.status_code == 201
        assert json.loads(resp.body) ==  [{
            'ab_testing': False,
            'hash': '603de7791bc268d86c705e417448d3c6efbb3439',
            'name': 'Placement Test',
            'small_hash': '603de',
            'store_id': 1,
            'variations': [{
                'engines_managers': [{
                    'engine': {
                        'configuration': {
                            'aggregators_ids_name': 'filter_test',
                            'item_id_name': 'item_id'
                        },
                        'id': 1,
                        'item_type': {
                            'id': 1,
                            'schema': {
                                'type': 'object',
                                'properties': {
                                    'filter_test': {'type': 'string'},
                                    'item_id': {'type': 'integer'}
                                },
                            },
                            'available_filters': [{
                                'name': 'filter_test',
                                'schema': {'type': 'string'}
                            },{
                                'name': 'item_id',
                                'schema': {'type': 'integer'}
                            }],
                            'name': 'products',
                            'id_names': [
                                'sku'
                            ]
                        },
                        'item_type_id': 1,
                        'name': 'Visual Similarity',
                        'store': {
                            'country': 'test',
                            'id': 1,
                            'name': 'test'
                        },
                        'store_id': 1,
                        'type_name': {
                            'id': 1,
                            'name': 'visual_similarity'
                        },
                        'type_name_id': 1,
                        'variables': [{
                            'name': 'item_id', 'schema': {'type': 'integer'}
                        },{
                            'name': 'filter_test', 'schema': {'type': 'string'}
                        }],
                    },
                    'engine_id': 1,
                    'engine_variables': [{
                        'is_filter': False,
                        'engine_manager_id': 1,
                        'id': 1,
                        'inside_engine_name': 'filter_test',
                        'override': False,
                        'override_value_json': None,
                        'variable': {
                            'id': 1,
                            'name': 'test',
                            'store_id': 1
                        },
                        'variable_id': 1
                    }],
                    'fallbacks': [],
                    'id': 1,
                    'store_id': 1
                }],
                'id': 1,
                'placement_hash': '603de7791bc268d86c705e417448d3c6efbb3439',
                'weight': None
            }]
        }]



class TestPlacementsModelGet(object):

    def test_get_not_found(self, client, headers):
        resp = client.get('/placements/', headers=headers)
        assert resp.status_code == 404

    def test_get_invalid_with_body(self, client, headers):
        resp = client.get('/placements/', headers=headers, body='{}')
        assert resp.status_code == 400
        assert json.loads(resp.body) == {'error': 'Request body is not acceptable'}

    def test_get(self, client, headers):
        body = [{
            'store_id': 1,
            'name': 'Placement Test',
            'variations': [{
                '_operation': 'insert',
                'engines_managers': [{'id': 1}]
            }]
        }]
        client.post('/placements/', headers=headers, body=json.dumps(body))

        resp = client.get('/placements/', headers=headers)
        assert resp.status_code == 200
        assert json.loads(resp.body) ==  [{
            'ab_testing': False,
            'hash': '603de7791bc268d86c705e417448d3c6efbb3439',
            'name': 'Placement Test',
            'small_hash': '603de',
            'store_id': 1,
            'variations': [{
                'engines_managers': [{
                    'engine': {
                        'configuration': {
                            'aggregators_ids_name': 'filter_test',
                            'item_id_name': 'item_id'
                        },
                        'id': 1,
                        'item_type': {
                            'id': 1,
                            'schema': {
                                'type': 'object',
                                'properties': {
                                    'filter_test': {'type': 'string'},
                                    'item_id': {'type': 'integer'}
                                },
                            },
                            'available_filters': [{
                                'name': 'filter_test',
                                'schema': {'type': 'string'}
                            },{
                                'name': 'item_id',
                                'schema': {'type': 'integer'}
                            }],
                            'name': 'products',
                            'id_names': [
                                'sku'
                            ]
                        },
                        'item_type_id': 1,
                        'name': 'Visual Similarity',
                        'store': {
                            'country': 'test',
                            'id': 1,
                            'name': 'test'
                        },
                        'store_id': 1,
                        'type_name': {
                            'id': 1,
                            'name': 'visual_similarity'
                        },
                        'type_name_id': 1,
                        'variables': [{
                            'name': 'item_id', 'schema': {'type': 'integer'}
                        },{
                            'name': 'filter_test', 'schema': {'type': 'string'}
                        }],
                    },
                    'engine_id': 1,
                    'engine_variables': [{
                        'is_filter': False,
                        'engine_manager_id': 1,
                        'id': 1,
                        'inside_engine_name': 'filter_test',
                        'override': False,
                        'override_value_json': None,
                        'variable': {
                            'id': 1,
                            'name': 'test',
                            'store_id': 1
                        },
                        'variable_id': 1
                    }],
                    'fallbacks': [],
                    'id': 1,
                    'store_id': 1
                }],
                'id': 1,
                'placement_hash': '603de7791bc268d86c705e417448d3c6efbb3439',
                'weight': None
            }]
        }]


class TestPlacementsModelUriTemplatePatch(object):

    def test_patch_without_body(self, client, headers):
        resp = client.patch('/placements/1/', headers=headers, body='')
        assert resp.status_code == 400
        assert json.loads(resp.body) == {'error': 'Request body is missing'}

    def test_patch_with_invalid_body(self, client, headers):
        resp = client.patch('/placements/1/', headers=headers, body='{}')
        assert resp.status_code == 400
        assert json.loads(resp.body) == {
            'error': {
                'input': {},
                'message': '{} does not have enough properties',
                'schema': {
                    'additionalProperties': False,
                    'minProperties': 1,
                    'properties': {
                        'ab_testing': {'type': 'boolean'},
                        'name': {'type': 'string'},
                        'store_id': {'type': 'integer'},
                        'variations': {'$ref': '#/definitions/variations'}
                    },
                    'type': 'object'
                }
            }
        }

    def test_patch_not_found(self, client, headers):
        body = {
            'name': 'test'
        }
        resp = client.patch('/engines/1/', headers=headers, body=json.dumps(body))
        assert resp.status_code == 404

    def test_patch_valid(self, client, headers):
        body = [{
            'store_id': 1,
            'name': 'Placement Test',
            'variations': [{
                '_operation': 'insert',
                'engines_managers': [{'id': 1}]
            }]
        }]
        obj = json.loads(client.post('/placements/', headers=headers, body=json.dumps(body)).body)[0]

        body = {
            'variations': [{
                '_operation': 'update',
                'id': 1,
                'engines_managers': [{'id': 1, '_operation': 'remove'}]
            }]
        }
        resp = client.patch('/placements/{}/'.format(obj['small_hash']),
            headers=headers, body=json.dumps(body))

        assert resp.status_code == 200
        assert json.loads(resp.body) ==  {
            'ab_testing': False,
            'hash': '603de7791bc268d86c705e417448d3c6efbb3439',
            'name': 'Placement Test',
            'small_hash': '603de',
            'store_id': 1,
            'variations': [{
                'engines_managers': [],
                'id': 1,
                'placement_hash': '603de7791bc268d86c705e417448d3c6efbb3439',
                'weight': None
            }]
        }


class TestPlacementsModelUriTemplateDelete(object):

    def test_delete_with_body(self, client, headers):
        resp = client.delete('/placements/1/', headers=headers, body='{}')
        assert resp.status_code == 400
        assert json.loads(resp.body) == {'error': 'Request body is not acceptable'}

    def test_delete_valid(self, client, headers):
        body = [{
            'store_id': 1,
            'name': 'Placement Test',
            'variations': [{
                '_operation': 'insert',
                'engines_managers': [{'id': 1}]
            }]
        }]
        obj = json.loads(client.post('/placements/', headers=headers, body=json.dumps(body)).body)[0]
        resp = client.get('/placements/{}/'.format(obj['small_hash']), headers=headers)
        assert resp.status_code == 200

        resp = client.delete('/placements/{}/'.format(obj['small_hash']), headers=headers)
        assert resp.status_code == 204

        resp = client.get('/placements/{}/'.format(obj['small_hash']), headers=headers)
        assert resp.status_code == 404


class TestPlacementsModelUriTemplateGet(object):

    def test_get_with_body(self, client, headers):
        resp = client.get('/placements/1/', headers=headers, body='{}')
        assert resp.status_code == 400
        assert json.loads(resp.body) == {'error': 'Request body is not acceptable'}

    def test_get_not_found(self, client, headers):
        resp = client.get('/placements/1/', headers=headers)
        assert resp.status_code == 404

    def test_get_valid(self, client, headers):
        body = [{
            'store_id': 1,
            'name': 'Placement Test',
            'variations': [{
                '_operation': 'insert',
                'engines_managers': [{'id': 1}]
            }]
        }]
        obj = json.loads(client.post('/placements/', headers=headers, body=json.dumps(body)).body)[0]

        resp = client.get('/placements/{}/'.format(obj['small_hash']), headers=headers)

        assert resp.status_code == 200
        assert json.loads(resp.body) == {
            'ab_testing': False,
            'hash': '603de7791bc268d86c705e417448d3c6efbb3439',
            'name': 'Placement Test',
            'small_hash': '603de',
            'store_id': 1,
            'variations': [{
                'engines_managers': [{
                    'engine': {
                        'configuration': {
                            'aggregators_ids_name': 'filter_test',
                            'item_id_name': 'item_id'
                        },
                        'id': 1,
                        'item_type': {
                            'id': 1,
                            'schema': {
                                'type': 'object',
                                'properties': {
                                    'filter_test': {'type': 'string'},
                                    'item_id': {'type': 'integer'}
                                },
                            },
                            'available_filters': [{
                                'name': 'filter_test',
                                'schema': {'type': 'string'}
                            },{
                                'name': 'item_id',
                                'schema': {'type': 'integer'}
                            }],
                            'name': 'products',
                            'id_names': [
                                'sku'
                            ]
                        },
                        'item_type_id': 1,
                        'name': 'Visual Similarity',
                        'store': {
                            'country': 'test',
                            'id': 1,
                            'name': 'test'
                        },
                        'store_id': 1,
                        'type_name': {
                            'id': 1,
                            'name': 'visual_similarity'
                        },
                        'type_name_id': 1,
                        'variables': [{
                            'name': 'item_id', 'schema': {'type': 'integer'}
                        },{
                            'name': 'filter_test', 'schema': {'type': 'string'}
                        }],
                    },
                    'engine_id': 1,
                    'engine_variables': [{
                        'is_filter': False,
                        'engine_manager_id': 1,
                        'id': 1,
                        'inside_engine_name': 'filter_test',
                        'override': False,
                        'override_value_json': None,
                        'variable': {
                            'id': 1,
                            'name': 'test',
                            'store_id': 1
                        },
                        'variable_id': 1
                    }],
                    'fallbacks': [],
                    'id': 1,
                    'store_id': 1
                }],
                'id': 1,
                'placement_hash': '603de7791bc268d86c705e417448d3c6efbb3439',
                'weight': None
            }]
        }


class TestPlacementsGetRecomendations(object):

    def test_get_recommendations_not_found(self, client, headers):
        body = [{
            'store_id': 1,
            'name': 'Placement Test',
            'variations': [{
                '_operation': 'insert',
                'engines_managers': [{'id': 1}]
            }]
        }]
        obj = json.loads(client.post('/placements/', headers=headers, body=json.dumps(body)).body)[0]
        resp = client.get('/placements/{}/recommendations'.format(obj['small_hash']), headers=headers)
        assert resp.status_code == 404

    def test_get_recommendations_placement_not_found(self, client, headers):
        resp = client.get('/placements/123/recommendations', headers=headers)
        assert resp.status_code == 404

    @mock.patch('myreco.domain.placements.models.EngineTypeChooser')
    def test_get_recommendations(self, engine_chooser, client, headers):
        engine_chooser()().get_recommendations.return_value = [1, 2, 3]
        body = [{
            'store_id': 1,
            'name': 'Placement Test',
            'variations': [{
                '_operation': 'insert',
                'engines_managers': [{'id': 1}]
            }]
        }]
        obj = json.loads(client.post('/placements/', headers=headers, body=json.dumps(body)).body)[0]
        resp = client.get('/placements/{}/recommendations'.format(obj['small_hash']), headers=headers)
        assert resp.status_code == 200
        assert resp.body == json.dumps([1, 2, 3])
