from myreco.base.http_api import HttpAPI
from myreco.base.resource import FalconModelResource
from unittest import mock

import pytest
import sqlalchemy as sa
import json


@pytest.fixture
def app(model1, session):
    app_ = HttpAPI(session.bind, session.redis_bind)
    app_.req_options.auto_parse_form_urlencoded = True
    return app_


@pytest.fixture
def model1(model_base):
    class model2(model_base):
        __tablename__ = 'model2'
        __table_args__ = {'mysql_engine':'innodb'}
        id = sa.Column(sa.Integer, primary_key=True)

    class model1(model_base):
        __tablename__ = 'model1'
        __table_args__ = {'mysql_engine':'innodb'}
        id = sa.Column(sa.Integer, primary_key=True)
        m2_id = sa.Column(sa.ForeignKey('model2.id'))

    return model1


@pytest.fixture
def resource1(model1, app):
    return FalconModelResource(app, ['post', 'get'], model1)


@pytest.fixture
def resource1_with_schema(model1, app):
    return FalconModelResource(app, ['post'], model1, post_input_json_schema={'type': 'object'})


class TestHttpAPIErrorHandlingPOST(object):
    def test_integrity_error_handling_with_duplicated_key(self, client, resource1):
        data = json.dumps([{'id':1},{'id':1}])
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

    def test_integrity_error_handling_with_foreign_key(self, client, resource1):
        data = json.dumps([{'m2_id':1}])
        resp = client.post('/model1/', data=data)

        assert resp.status_code == 400
        assert json.loads(resp.body) == {
            'error': {
                'details': [],
                'params': {'m2_id': 1},
                'database message': {
                    'message':  'Cannot add or update a child row: ' \
                                'a foreign key constraint fails ' \
                                '(`myreco_test`.`model1`, ' \
                                'CONSTRAINT `model1_ibfk_1` FOREIGN ' \
                                'KEY (`m2_id`) REFERENCES `model2` ' \
                                '(`id`))',
                    'code': 1452
                }
            }
        }

    def test_json_validation_error_handling(self, client, resource1_with_schema):
        resp = client.post('/model1/', data='"test"')

        assert resp.status_code == 400
        assert json.loads(resp.body) == {
            'error': {
                'instance': 'test',
                'message': "'test' is not of type 'object'",
                'schema': {
                    'type': 'object'
                }
            }
        }

    def test_json_error_handling(self, client, resource1_with_schema):
        resp = client.post('/model1/', data='test')

        assert resp.status_code == 400
        assert json.loads(resp.body) == {
            'error': {
                'instance': 'test',
                'message': 'Expecting value: line 1 column 1 (char 0)'
            }
        }

    def test_generic_error_handling(self, client, resource1):
        resource1.model.insert = mock.MagicMock(side_effect=Exception)
        resp = client.post('/model1/', data='"test"')

        assert resp.status_code == 500
        assert json.loads(resp.body) == {
            'error': {
                'message': 'Something unexpected happened'
            }
        }
