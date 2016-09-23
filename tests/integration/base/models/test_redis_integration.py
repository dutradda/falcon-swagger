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


from myreco.base.models.redis import RedisModelsBuilder
from myreco.base.http_api import HttpAPI
from unittest import mock
from fakeredis import FakeStrictRedis
import pytest
import json


@pytest.fixture
def app():
    schema = {
        'type': 'object',
        'required': ['id', 'field1', 'field2'],
        'properties': {
            'id': {'type': 'integer'},
            'field1': {'type': 'string'},
            'field2': {
                'type': 'object',
                'required': ['fid'],
                'properties': {'fid': {'type': 'string'}}
            }
        }
    }
    routes = [{
        'uri_template': '/test',
        'method': {'name': 'POST'},
        'input_schema': schema,
        'output_schema': schema
    },{
        'uri_template': '/test/{id}',
        'method': {'name': 'POST'}
    },{
        'uri_template': '/test',
        'method': {'name': 'PUT'},
        'input_schema': schema,
        'output_schema': schema
    },{
        'uri_template': '/test/{id}',
        'method': {'name': 'PUT'},
        'input_schema': schema,
        'output_schema': schema
    },{
        'uri_template': '/test',
        'method': {'name': 'PATCH'}
    },{
        'uri_template': '/test/{id}',
        'method': {'name': 'PATCH'}
    },{
        'uri_template': '/test',
        'method': {'name': 'DELETE'}
    },{
        'uri_template': '/test/{id}',
        'method': {'name': 'DELETE'}
    },{
        'uri_template': '/test',
        'method': {'name': 'GET'}
    },{
        'uri_template': '/test/{id}',
        'method': {'name': 'GET'}
    }]
    models = [{'name': 'test', 'id_names': ['id'], 'routes': routes}]
    return HttpAPI(RedisModelsBuilder(models), redis_bind=FakeStrictRedis())


class TestRedisModelPost(object):
    def test_post_without_ids(self, client):
        body = {
            'id': 1,
            'field1': 'test',
            'field2': {
                'fid': '1'
            }
        }
        resp = client.post('/test', body=json.dumps(body))
        assert json.loads(resp.body) == body

    def test_post_with_ids(self, client):
        body = {
            'id': 1,
            'field1': 'test',
            'field2': {
                'fid': '1'
            }
        }
        resp = client.post('/test/1/', body=json.dumps(body))
        assert json.loads(resp.body) == body

    def test_put_without_ids(self, client):
        body = {
            'id': 1,
            'field1': 'test',
            'field2': {
                'fid': '1'
            }
        }
        client.post('/test', body=json.dumps(body))
        resp = client.put('/test', body=json.dumps(body))
        assert json.loads(resp.body) == [body]

    def test_put_with_ids(self, client):
        body = {
            'id': 1,
            'field1': 'test',
            'field2': {
                'fid': '1'
            }
        }
        resp = client.put('/test/1/', body=json.dumps(body))
        assert json.loads(resp.body) == body
