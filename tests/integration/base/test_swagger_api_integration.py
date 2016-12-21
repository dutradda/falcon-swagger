from falconswagger.swagger_api import SwaggerAPI
from unittest import mock
from jsonschema import Draft4Validator
from pytest_falcon.plugin import Client
import pytest
import sqlalchemy as sa
import json


@pytest.fixture
def model1(model_base):
    class model2(model_base):
        __tablename__ = 'model2'
        __table_args__ = {'mysql_engine': 'innodb'}
        id = sa.Column(sa.Integer, primary_key=True)

    class model1(model_base):
        __tablename__ = 'model1'
        __table_args__ = {'mysql_engine': 'innodb'}
        id = sa.Column(sa.Integer, primary_key=True)
        m2_id = sa.Column(sa.ForeignKey('model2.id'))
        model2_ = sa.orm.relationship('model2')

        __schema__ = {
            '/model1/': {
                'post': {
                    'operationId': 'post_by_body',
                    'responses': {'200': {'description': 'test'}},
                    'parameters': [{
                        'name': 'body',
                        'in': 'body',
                        'schema': {'type': 'array'}
                    }]
                },
                'put': {
                    'operationId': 'put_by_body',
                    'responses': {'200': {'description': 'test'}},
                    'parameters': [{
                        'name': 'body',
                        'in': 'body',
                        'schema': {'type': 'array'}
                    }]
                }
            }
        }

        @classmethod
        def get_test(cls, req, resp, **kwargs):
            pass

    return model1


@pytest.fixture
def app(model1, session):
    app_ = SwaggerAPI([model1], session.bind, session.redis_bind, title='Test API')
    return app_


@pytest.fixture
def model1_with_schema(model_base):
    class model2(model_base):
        __tablename__ = 'model2'
        __table_args__ = {'mysql_engine': 'innodb'}
        id = sa.Column(sa.Integer, primary_key=True)

    class model1(model_base):
        __tablename__ = 'model1'
        __table_args__ = {'mysql_engine': 'innodb'}
        id = sa.Column(sa.Integer, primary_key=True)
        m2_id = sa.Column(sa.ForeignKey('model2.id'))
        model2_ = sa.orm.relationship('model2')

        __schema__ = {
            '/model1/': {
                'post': {
                    'operationId': 'get_test',
                    'responses': {'200': {'description': 'test'}},
                    'parameters': [{
                        'name': 'body',
                        'in': 'body',
                        'schema': {'type': 'array'}
                    }]
                }
            }
        }

        @classmethod
        def get_test(cls, req, resp, **kwargs):
            pass

    return model1


@pytest.fixture
def client_with_schema(model1_with_schema, session):
    app_ = SwaggerAPI([model1_with_schema], session.bind, session.redis_bind, title='Test API')
    return Client(app_)


class TestSwaggerAPIErrorHandlingPOST(object):

    def test_integrity_error_handling_with_duplicated_key(self, model1, client):
        data = json.dumps([{'id': 1}, {'id': 1}])
        resp = client.post('/model1/', data=data)

        assert resp.status_code == 400
        assert json.loads(resp.body) == {
            'error': {
                'details': [],
                'params': [{'id': 1, 'm2_id': None}, {'id': 1, 'm2_id': None}],
                'database message': {
                    'message': "Duplicate entry '1' for key 'PRIMARY'",
                    'code': 1062
                }
            }
        }

    def test_integrity_error_handling_with_foreign_key(self, model1, client):
        data = json.dumps([{'m2_id': 1}])
        resp = client.post('/model1/', data=data)

        assert resp.status_code == 400
        assert json.loads(resp.body) == {
            'error': {
                'details': [],
                'params': {'m2_id': 1},
                'database message': {
                    'message':  'Cannot add or update a child row: '
                                'a foreign key constraint fails '
                                '(`falconswagger_test`.`model1`, '
                                'CONSTRAINT `model1_ibfk_1` FOREIGN '
                                'KEY (`m2_id`) REFERENCES `model2` '
                                '(`id`))',
                    'code': 1452
                }
            }
        }

    def test_json_validation_error_handling(self, model1_with_schema, client_with_schema):
        resp = client_with_schema.post('/model1/', data='"test"')

        assert resp.status_code == 400
        assert json.loads(resp.body) == {
            'error': {
                'input': 'test',
                'message': "'test' is not of type 'array'",
                'schema': {
                    'type': 'array'
                }
            }
        }

    def test_json_error_handling(self, model1_with_schema, client_with_schema):
        resp = client_with_schema.post('/model1/', data='test')

        assert resp.status_code == 400
        assert json.loads(resp.body) == {
            'error': {
                'input': 'test',
                'message': 'Expecting value: line 1 column 1 (char 0)'
            }
        }

    def test_model_base_error_handling_with_post_and_with_nested_delete(self, model1, client):
        data = [{'model2_': {'id': 1, '_operation': 'delete'}}]
        resp = client.post('/model1/', data=json.dumps(data))

        assert resp.status_code == 400
        assert json.loads(resp.body) == {
            'error': {
                'input': data,
                'message': "Can't execute nested 'delete' operation"
            }
        }

    def test_model_base_error_handling_with_post_and_with_nested_remove(self, model1, client):
        data = [{'model2_': {'id': 1, '_operation': 'remove'}}]
        resp = client.post('/model1/', data=json.dumps(data))

        assert resp.status_code == 400
        assert json.loads(resp.body) == {
            'error': {
                'input': data,
                'message': "Can't execute nested 'remove' operation"
            }
        }

    def test_model_base_error_handling_with_post_and_with_nested_update(self, model1, client):
        data = [{'model2_': {'id': 1, '_operation': 'update'}}]
        resp = client.post('/model1/', data=json.dumps(data))

        assert resp.status_code == 400
        assert json.loads(resp.body) == {
            'error': {
                'input': data,
                'message': "Can't execute nested 'update' operation"
            }
        }

    def test_model_base_error_handling_with_put_and_with_nested_delete(self, model1, client):
        resp = client.post('/model1/', data='[{}]')
        assert resp.status_code == 201
        data = [{'id': 1, 'model2_': {'id': 1, '_operation': 'delete'}}]
        resp = client.put('/model1/', body=json.dumps(data))

        assert resp.status_code == 400
        assert json.loads(resp.body) == {
            'error': {
                'input': data,
                'message': "Can't execute nested 'delete' operation"
            }
        }

    def test_model_base_error_handling_with_put_and_with_nested_remove(self, model1, client):
        data = [{'model2_': {'id': 1, '_operation': 'remove'}}]
        resp = client.post('/model1/', data=json.dumps(data))

        assert resp.status_code == 400
        assert json.loads(resp.body) == {
            'error': {
                'input': data,
                'message': "Can't execute nested 'remove' operation"
            }
        }

    def test_model_base_error_handling_with_put_and_with_nested_update(self, model1, client):
        data = [{'model2_': {'id': 1, '_operation': 'update'}}]
        resp = client.post('/model1/', data=json.dumps(data))

        assert resp.status_code == 400
        assert json.loads(resp.body) == {
            'error': {
                'input': data,
                'message': "Can't execute nested 'update' operation"
            }
        }

    def test_generic_error_handling(self, model1, client):
        model1.insert = mock.MagicMock(side_effect=Exception)
        resp = client.post('/model1/', data='[{}]')

        assert resp.status_code == 500
        assert json.loads(resp.body) == {
            'error': {
                'message': 'Something unexpected happened'
            }
        }
