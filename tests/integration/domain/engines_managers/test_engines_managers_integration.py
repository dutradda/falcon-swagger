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
from myreco.domain.engines_managers.models import EnginesManagersModel
from myreco.domain.items_types.models import ItemsTypesModel
from myreco.domain.stores.model import StoresModel
from myreco.domain.users.models import UsersModel
from myreco.domain.variables.model import VariablesModel
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

    return HttpAPI([EnginesManagersModel], session.bind, FakeStrictRedis())


@pytest.fixture
def headers():
    return {
        'Authorization': b64encode('test:test'.encode()).decode()
    }



class TestEnginesManagersModelPost(object):

    def test_post_without_body(self, client, headers):
        resp = client.post('/engines_managers/', headers=headers)
        assert resp.status_code == 400
        assert json.loads(resp.body) == {'error': 'Request body is missing'}

    def test_post_with_invalid_body(self, client, headers):
        resp = client.post('/engines_managers/', headers=headers, body='[{}]')
        assert resp.status_code == 400
        assert json.loads(resp.body) ==  {
            'error': {
                'input': {},
                'message': "'engine_id' is a required property",
                'schema': {
                    'type': 'object',
                    'additionalProperties': False,
                    'required': ['engine_id', 'store_id', 'engine_variables'],
                    'properties': {
                        'store_id': {'type': 'integer'},
                        'engine_id': {'type': 'integer'},
                        'fallbacks': {'$ref': '#/definitions/fallbacks'},
                        'engine_variables': {'$ref': '#/definitions/engine_variables'}
                    }
                }
            }
        }

    def test_post_with_invalid_variable_engine(self, client, headers):
        body = [{
            'store_id': 1,
            'engine_id': 1,
            'engine_variables': [{
                '_operation': 'insert',
                'variable_id': 1,
                'inside_engine_name': 'test'
            }]
        }]
        resp = client.post('/engines_managers/', headers=headers, body=json.dumps(body))
        assert resp.status_code == 400
        assert json.loads(resp.body) ==  {
            'error': {
                'message': "Invalid engine variable with 'inside_engine_name' value 'test'",
                'input': [{
                    'engine_id': 1,
                    'store_id': 1,
                    'engine_variables': [{
                        '_operation': 'insert',
                        'inside_engine_name': 'test',
                        'variable_id': 1
                    }]
                }],
                'schema': {
                    'available_variables': [{
                        'name': 'filter_test',
                        'schema': {"type": "string"}
                    },{
                        'name': 'item_id',
                        'schema': {"type": "integer"}
                    }]
                }
            }
        }

    def test_post_with_invalid_filter(self, client, headers):
        body = [{
            'store_id': 1,
            'engine_id': 1,
            'engine_variables': [{
                '_operation': 'insert',
                'variable_id': 1,
                'inside_engine_name': 'test',
                'is_filter': True
            }]
        }]
        resp = client.post('/engines_managers/', headers=headers, body=json.dumps(body))
        assert resp.status_code == 400
        assert json.loads(resp.body) ==  {
            'error': {
                'message': "Invalid filter with 'inside_engine_name' value 'test'",
                'input': [{
                    'engine_id': 1,
                    'store_id': 1,
                    'engine_variables': [{
                        '_operation': 'insert',
                        'inside_engine_name': 'test',
                        'is_filter': True,
                        'variable_id': 1
                    }]
                }],
                'schema': {
                    'available_filters': [{
                        'name': 'filter_test',
                        'schema': {"type": "string"}
                    },{
                        'name': 'item_id',
                        'schema': {"type": "integer"}
                    }]
                }
            }
        }

    def test_post_with_insert_engine_variable_engine_var(self, client, headers):
        body = [{
            'store_id': 1,
            'engine_id': 1,
            'engine_variables': [{
                '_operation': 'insert',
                'variable_id': 1,
                'inside_engine_name': 'filter_test'
            }]
        }]
        resp = client.post('/engines_managers/', headers=headers, body=json.dumps(body))

        assert resp.status_code == 201
        assert json.loads(resp.body) == [{
            'fallbacks': [],
            'id': 1,
            'engine_variables': [
                {
                    'variable': {
                        'id': 1,
                        'name': 'test',
                        'store_id': 1
                    },
                    'id': 1,
                    'inside_engine_name': 'filter_test',
                    'engine_manager_id': 1,
                    'override': False,
                    'override_value_json': None,
                    'variable_id': 1,
                    'is_filter': False
                }
            ],
            'engine': {
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
                'store_id': 1,
                'name': 'Visual Similarity',
                'item_type_id': 1,
                'type_name': {
                    'id': 1,
                    'name': 'visual_similarity'
                },
                'id': 1,
                'variables': [{
                    'name': 'item_id', 'schema': {'type': 'integer'}
                },{
                    'name': 'filter_test', 'schema': {'type': 'string'}
                }],
                'type_name_id': 1,
                'configuration': {
                    'aggregators_ids_name': 'filter_test',
                    'item_id_name': 'item_id'
                },
                'store': {
                    'id': 1,
                    'country': 'test',
                    'name': 'test'
                }
            },
            'store_id': 1,
            'engine_id': 1
        }]

    def test_post_with_insert_engine_variable_engine_filter(self, client, headers):
        body = [{
            'store_id': 1,
            'engine_id': 1,
            'engine_variables': [{
                '_operation': 'insert',
                'variable_id': 1,
                'is_filter': True,
                'inside_engine_name': 'filter_test'
            }]
        }]
        resp = client.post('/engines_managers/', headers=headers, body=json.dumps(body))

        assert resp.status_code == 201
        assert json.loads(resp.body) == [{
            'fallbacks': [],
            'id': 1,
            'engine_variables': [
                {
                    'variable': {
                        'id': 1,
                        'name': 'test',
                        'store_id': 1
                    },
                    'id': 1,
                    'inside_engine_name': 'filter_test',
                    'engine_manager_id': 1,
                    'override': False,
                    'override_value_json': None,
                    'variable_id': 1,
                    'is_filter': True
                }
            ],
            'engine': {
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
                'store_id': 1,
                'name': 'Visual Similarity',
                'item_type_id': 1,
                'type_name': {
                    'id': 1,
                    'name': 'visual_similarity'
                },
                'id': 1,
                'variables': [{
                    'name': 'item_id', 'schema': {'type': 'integer'}
                },{
                    'name': 'filter_test', 'schema': {'type': 'string'}
                }],
                'type_name_id': 1,
                'configuration': {
                    'aggregators_ids_name': 'filter_test',
                    'item_id_name': 'item_id'
                },
                'store': {
                    'id': 1,
                    'country': 'test',
                    'name': 'test'
                }
            },
            'store_id': 1,
            'engine_id': 1
        }]

    def test_post_with_fallback(self, client, headers):
        body = [{
            'store_id': 1,
            'engine_id': 1,
            'engine_variables': [{
                '_operation': 'insert',
                'variable_id': 1,
                'inside_engine_name': 'item_id'
            }]
        }]
        client.post('/engines_managers/', headers=headers, body=json.dumps(body))

        body = [{
            'store_id': 1,
            'engine_id': 1,
            'engine_variables': [{
                '_operation': 'insert',
                'variable_id': 1,
                'inside_engine_name': 'item_id'
            }],
            'fallbacks': [{'id': 1}]
        }]
        resp = client.post('/engines_managers/', headers=headers, body=json.dumps(body))

        assert resp.status_code == 201
        assert json.loads(resp.body) == [{
            'fallbacks': [{
                'id': 1,
                'engine_variables': [
                    {
                        'variable': {
                            'id': 1,
                            'name': 'test',
                            'store_id': 1
                        },
                        'id': 1,
                        'inside_engine_name': 'item_id',
                        'engine_manager_id': 1,
                        'override': False,
                        'override_value_json': None,
                        'variable_id': 1,
                        'is_filter': False
                    }
                ],
                'engine': {
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
                    'store_id': 1,
                    'name': 'Visual Similarity',
                    'item_type_id': 1,
                    'type_name': {
                        'id': 1,
                        'name': 'visual_similarity'
                    },
                    'id': 1,
                    'variables': [{
                        'name': 'item_id', 'schema': {'type': 'integer'}
                    },{
                        'name': 'filter_test', 'schema': {'type': 'string'}
                    }],
                    'type_name_id': 1,
                    'configuration': {
                        'aggregators_ids_name': 'filter_test',
                        'item_id_name': 'item_id'
                    },
                    'store': {
                        'id': 1,
                        'country': 'test',
                        'name': 'test'
                    }
                },
                'store_id': 1,
                'engine_id': 1
            }],
            'id': 2,
            'engine_variables': [
                {
                    'variable': {
                        'id': 1,
                        'name': 'test',
                        'store_id': 1
                    },
                    'id': 2,
                    'inside_engine_name': 'item_id',
                    'engine_manager_id': 2,
                    'override': False,
                    'override_value_json': None,
                    'variable_id': 1,
                    'is_filter': False
                }
            ],
            'engine': {
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
                'store_id': 1,
                'name': 'Visual Similarity',
                'item_type_id': 1,
                'type_name': {
                    'id': 1,
                    'name': 'visual_similarity'
                },
                'id': 1,
                'variables': [{
                    'name': 'item_id', 'schema': {'type': 'integer'}
                },{
                    'name': 'filter_test', 'schema': {'type': 'string'}
                }],
                'type_name_id': 1,
                'configuration': {
                    'aggregators_ids_name': 'filter_test',
                    'item_id_name': 'item_id'
                },
                'store': {
                    'id': 1,
                    'country': 'test',
                    'name': 'test'
                }
            },
            'store_id': 1,
            'engine_id': 1
        }]


class TestEnginesManagersModelGet(object):

    def test_get_not_found(self, client, headers):
        resp = client.get('/engines_managers/', headers=headers)
        assert resp.status_code == 404

    def test_get_invalid_with_body(self, client, headers):
        resp = client.get('/engines_managers/', headers=headers, body='{}')
        assert resp.status_code == 400
        assert json.loads(resp.body) == {'error': 'Request body is not acceptable'}

    def test_get(self, client, headers):
        body = [{
            'store_id': 1,
            'engine_id': 1,
            'engine_variables': [{
                '_operation': 'insert',
                'variable_id': 1,
                'inside_engine_name': 'filter_test'
            }]
        }]
        client.post('/engines_managers/', headers=headers, body=json.dumps(body))

        resp = client.get('/engines_managers/', headers=headers)
        assert resp.status_code == 200
        assert json.loads(resp.body) ==  [{
            'fallbacks': [],
            'id': 1,
            'engine_variables': [
                {
                    'variable': {
                        'id': 1,
                        'name': 'test',
                        'store_id': 1
                    },
                    'id': 1,
                    'inside_engine_name': 'filter_test',
                    'engine_manager_id': 1,
                    'override': False,
                    'override_value_json': None,
                    'variable_id': 1,
                    'is_filter': False
                }
            ],
            'engine': {
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
                'store_id': 1,
                'name': 'Visual Similarity',
                'item_type_id': 1,
                'type_name': {
                    'id': 1,
                    'name': 'visual_similarity'
                },
                'id': 1,
                'variables': [{
                    'name': 'item_id', 'schema': {'type': 'integer'}
                },{
                    'name': 'filter_test', 'schema': {'type': 'string'}
                }],
                'type_name_id': 1,
                'configuration': {
                    'aggregators_ids_name': 'filter_test',
                    'item_id_name': 'item_id'
                },
                'store': {
                    'id': 1,
                    'country': 'test',
                    'name': 'test'
                }
            },
            'store_id': 1,
            'engine_id': 1
        }]


class TestEnginesManagersModelUriTemplatePatch(object):

    def test_patch_without_body(self, client, headers):
        resp = client.patch('/engines_managers/1/', headers=headers, body='')
        assert resp.status_code == 400
        assert json.loads(resp.body) == {'error': 'Request body is missing'}

    def test_patch_with_invalid_body(self, client, headers):
        resp = client.patch('/engines_managers/1/', headers=headers, body='{}')
        assert resp.status_code == 400
        assert json.loads(resp.body) ==  {
            'error': {
                'input': {},
                'schema': {
                    'additionalProperties': False,
                    'minProperties': 1,
                    'properties': {
                        'engine_id': {
                            'type': 'integer'
                        },
                        'store_id': {
                            'type': 'integer'
                        },
                        'fallbacks': {
                            '$ref': '#/definitions/fallbacks'
                        },
                        'engine_variables': {
                            '$ref': '#/definitions/engine_variables'
                        }
                    },
                    'type': 'object'
                },
                'message': '{} does not have enough properties'
            }
        }


    def test_patch_with_invalid_engine_variable(self, client, headers):
        body = [{
            'store_id': 1,
            'engine_id': 1,
            'engine_variables': [{
                '_operation': 'insert',
                'variable_id': 1,
                'inside_engine_name': 'filter_test'
            }]
        }]
        resp = client.post('/engines_managers/', headers=headers, body=json.dumps(body))

        body = {
            'engine_variables': [{
                '_operation': 'update',
                'id': 1,
                'inside_engine_name': 'invalid'
            }]
        }
        resp = client.patch('/engines_managers/1/', headers=headers, body=json.dumps(body))
        assert resp.status_code == 400
        assert json.loads(resp.body) ==  {
            'error': {
                'message': "Invalid engine variable with 'inside_engine_name' value 'invalid'",
                'input': {
                    'id': 1,
                    'engine_variables': [{
                        '_operation': 'update',
                        'id': 1,
                        'inside_engine_name': 'invalid'
                    }],
                },
                'schema': {
                    'available_variables': [{
                        'name': 'filter_test',
                        'schema': {"type": "string"}
                    },{
                        'name': 'item_id',
                        'schema': {"type": "integer"}
                    }]
                }
            }
        }

    def test_patch_with_invalid_fallback_id(self, client, headers):
        body = [{
            'store_id': 1,
            'engine_id': 1,
            'engine_variables': [{
                '_operation': 'insert',
                'variable_id': 1,
                'inside_engine_name': 'filter_test'
            }]
        }]
        resp = client.post('/engines_managers/', headers=headers, body=json.dumps(body))

        body = {
            'fallbacks': [{'id': 1}]
        }
        resp = client.patch('/engines_managers/1/', headers=headers, body=json.dumps(body))
        assert resp.status_code == 400
        assert json.loads(resp.body) == {
            'error': {
                'input': {'fallbacks': [{'id': 1}], 'id': 1},
                'message': "a Engine Manager can't fallback itself"
            }
        }

    def test_patch_with_invalid_fallback_item_type(self, client, headers):
        body = [{
            'store_id': 1,
            'engine_id': 1,
            'engine_variables': [{
                '_operation': 'insert',
                'variable_id': 1,
                'inside_engine_name': 'filter_test'
            }]
        },{
            'store_id': 1,
            'engine_id': 2,
            'engine_variables': [{
                '_operation': 'insert',
                'variable_id': 1,
                'inside_engine_name': 'item_id'
            }]
        }]
        resp = client.post('/engines_managers/', headers=headers, body=json.dumps(body))

        body = {
            'fallbacks': [{'id': 2}]
        }
        resp = client.patch('/engines_managers/1/', headers=headers, body=json.dumps(body))
        assert resp.status_code == 400
        assert json.loads(resp.body) == {
            'error': {
                'input': {'fallbacks': [{'id': 2}], 'id': 1},
                'message': "Cannot set a fallback with different items types"
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
            'store_id': 1,
            'engine_id': 1,
            'engine_variables': [{
                '_operation': 'insert',
                'variable_id': 1,
                'inside_engine_name': 'item_id'
            }]
        }]
        obj = json.loads(client.post('/engines_managers/', headers=headers, body=json.dumps(body)).body)[0]

        body = {
            'engine_variables': [{
                '_operation': 'update',
                'id': 1,
                'inside_engine_name': 'filter_test'
            }]
        }
        resp = client.patch('/engines_managers/1/', headers=headers, body=json.dumps(body))

        assert resp.status_code == 200
        assert json.loads(resp.body) ==  {
            'fallbacks': [],
            'id': 1,
            'engine_variables': [
                {
                    'variable': {
                        'id': 1,
                        'name': 'test',
                        'store_id': 1
                    },
                    'id': 1,
                    'inside_engine_name': 'filter_test',
                    'engine_manager_id': 1,
                    'override': False,
                    'override_value_json': None,
                    'variable_id': 1,
                    'is_filter': False
                }
            ],
            'engine': {
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
                'store_id': 1,
                'name': 'Visual Similarity',
                'item_type_id': 1,
                'type_name': {
                    'id': 1,
                    'name': 'visual_similarity'
                },
                'id': 1,
                'variables': [{
                    'name': 'item_id', 'schema': {'type': 'integer'}
                },{
                    'name': 'filter_test', 'schema': {'type': 'string'}
                }],
                'type_name_id': 1,
                'configuration': {
                    'aggregators_ids_name': 'filter_test',
                    'item_id_name': 'item_id'
                },
                'store': {
                    'id': 1,
                    'country': 'test',
                    'name': 'test'
                }
            },
            'store_id': 1,
            'engine_id': 1
        }


class TestEnginesManagersModelUriTemplateDelete(object):

    def test_delete_with_body(self, client, headers):
        resp = client.delete('/engines_managers/1/', headers=headers, body='{}')
        assert resp.status_code == 400
        assert json.loads(resp.body) == {'error': 'Request body is not acceptable'}

    def test_delete(self, client, headers):
        body = [{
            'store_id': 1,
            'engine_id': 1,
            'engine_variables': [{
                '_operation': 'insert',
                'variable_id': 1,
                'inside_engine_name': 'filter_test'
            }]
        }]
        client.post('/engines_managers/', headers=headers, body=json.dumps(body))
        resp = client.get('/engines_managers/1/', headers=headers)
        assert resp.status_code == 200

        resp = client.delete('/engines_managers/1/', headers=headers)
        assert resp.status_code == 204

        resp = client.get('/engines_managers/1/', headers=headers)
        assert resp.status_code == 404


class TestEnginesManagersModelUriTemplateGet(object):

    def test_get_with_body(self, client, headers):
        resp = client.get('/engines_managers/1/', headers=headers, body='{}')
        assert resp.status_code == 400
        assert json.loads(resp.body) == {'error': 'Request body is not acceptable'}

    def test_get_not_found(self, client, headers):
        resp = client.get('/engines_managers/1/', headers=headers)
        assert resp.status_code == 404

    def test_get(self, client, headers):
        body = [{
            'store_id': 1,
            'engine_id': 1,
            'engine_variables': [{
                '_operation': 'insert',
                'variable_id': 1,
                'inside_engine_name': 'filter_test'
            }]
        }]
        client.post('/engines_managers/', headers=headers, body=json.dumps(body))

        resp = client.get('/engines_managers/1/', headers=headers)

        assert resp.status_code == 200
        assert json.loads(resp.body) == {
            'fallbacks': [],
            'id': 1,
            'engine_variables': [
                {
                    'variable': {
                        'id': 1,
                        'name': 'test',
                        'store_id': 1
                    },
                    'id': 1,
                    'inside_engine_name': 'filter_test',
                    'engine_manager_id': 1,
                    'override': False,
                    'override_value_json': None,
                    'variable_id': 1,
                    'is_filter': False
                }
            ],
            'engine': {
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
                'store_id': 1,
                'name': 'Visual Similarity',
                'item_type_id': 1,
                'type_name': {
                    'id': 1,
                    'name': 'visual_similarity'
                },
                'id': 1,
                'variables': [{
                    'name': 'item_id', 'schema': {'type': 'integer'}
                },{
                    'name': 'filter_test', 'schema': {'type': 'string'}
                }],
                'type_name_id': 1,
                'configuration': {
                    'aggregators_ids_name': 'filter_test',
                    'item_id_name': 'item_id'
                },
                'store': {
                    'id': 1,
                    'country': 'test',
                    'name': 'test'
                }
            },
            'store_id': 1,
            'engine_id': 1
        }
