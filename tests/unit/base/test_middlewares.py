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


from myreco.base.middlewares import FalconJsonSchemaMiddleware, FalconSQLAlchemyRedisMiddleware
from myreco.exceptions import JSONError
from unittest import mock

import pytest


@pytest.fixture
def json_schema_middleware():
    return FalconJsonSchemaMiddleware()


class TestFalconJsonSchemaMiddleware(object):
    def test_process_resource_without_methods(self, json_schema_middleware):
        req = mock.MagicMock(method='test')
        req.stream.read().decode.return_value = 'test'
        resp = mock.MagicMock()
        resource = mock.MagicMock(allowed_methods=[])
        params = mock.MagicMock()

        json_schema_middleware.process_resource(req, resp, resource, params)
        assert req.stream.read().decode.call_count == 0

    def test_process_resource_with_invalid_json(self, json_schema_middleware):
        req = mock.MagicMock(method='test')
        req.stream.read().decode.return_value = 'test'
        resp = mock.MagicMock()
        resource = mock.MagicMock(allowed_methods=['TEST'])
        params = mock.MagicMock()

        with pytest.raises(JSONError):
            json_schema_middleware.process_resource(req, resp, resource, params)

    def test_process_resource_with_valid_json(self, json_schema_middleware):
        req = mock.MagicMock(method='test', context=dict())
        req.stream.read().decode.return_value = '"test"'
        resp = mock.MagicMock()
        resource = mock.MagicMock(allowed_methods=['TEST'])
        params = mock.MagicMock()

        json_schema_middleware.process_resource(req, resp, resource, params)
        assert req.context == {'body': 'test'}

    def test_process_resource_with_valid_json_and_with_validator(self, json_schema_middleware):
        req = mock.MagicMock(method='test', context=dict())
        req.stream.read().decode.return_value = '"test"'
        resp = mock.MagicMock()
        resource = mock.MagicMock(allowed_methods=['TEST'])
        params = mock.MagicMock()

        json_schema_middleware.process_resource(req, resp, resource, params)
        assert hasattr(resource, 'on_test_validator')
        assert resource.on_test_validator.validate.call_args_list == [mock.call('test')]

    def test_process_resource_with_valid_json_and_without_validator(self, json_schema_middleware):
        req = mock.MagicMock(method='test', context=dict())
        req.stream.read().decode.return_value = '"test"'
        resp = mock.MagicMock()
        resource = mock.MagicMock(allowed_methods=['TEST'])
        del resource.on_test_validator
        params = mock.MagicMock()

        json_schema_middleware.process_resource(req, resp, resource, params)
        assert not hasattr(resource, 'on_test_validator')

    def test_process_resource_with_empty_body(self, json_schema_middleware):
        req = mock.MagicMock(method='test', context=dict())
        req.stream.read().decode.return_value = ''
        resp = mock.MagicMock()
        resource = mock.MagicMock(allowed_methods=['TEST'])
        params = mock.MagicMock()

        json_schema_middleware.process_resource(req, resp, resource, params)
        assert req.context == {'body': {}}

    def test_process_response(self, json_schema_middleware):
        req = mock.MagicMock()
        resp = mock.MagicMock(body='test')
        resource = mock.MagicMock()

        json_schema_middleware.process_response(req, resp, resource)
        assert resp.body == '"test"'

    def test_process_response_with_empty_body(self, json_schema_middleware):
        req = mock.MagicMock()
        resp = mock.MagicMock(body='')
        resource = mock.MagicMock()

        json_schema_middleware.process_response(req, resp, resource)
        assert resp.body == ''


@pytest.fixture
def bind():
    return mock.MagicMock()


@pytest.fixture
def redis_bind():
    return mock.MagicMock()


@pytest.fixture
def sqlalchemy_middleware(bind, redis_bind):
    return FalconSQLAlchemyRedisMiddleware(bind, redis_bind)


@mock.patch('myreco.base.middlewares.json', new=mock.MagicMock())
class TestFalconSQLAlchemyRedisMiddleware(object):
    @mock.patch('myreco.base.middlewares.Session')
    def test_process_resource(self, session, sqlalchemy_middleware, bind, redis_bind):
        req = mock.MagicMock(method='test', context=dict())
        resp = mock.MagicMock()
        resource = mock.MagicMock(allowed_methods=['TEST'])
        params = mock.MagicMock()

        sqlalchemy_middleware.process_resource(req, resp, resource, params)

        assert session.call_args_list == [mock.call(bind=bind, redis_bind=redis_bind)]
        assert req.context['session'] == session.return_value

    def test_process_response(self, sqlalchemy_middleware):
        req = mock.MagicMock(method='test', context=dict())
        resp = mock.MagicMock()
        resource = mock.MagicMock(allowed_methods=['TEST'])
        params = mock.MagicMock()

        sqlalchemy_middleware.process_response(req, resp, resource)
        assert 'session' not in req.context

    def test_process_response_without_session(self, sqlalchemy_middleware):
        req = mock.MagicMock(method='test', context=dict())
        resp = mock.MagicMock()
        resource = mock.MagicMock(allowed_methods=['TEST'], session=None)
        params = mock.MagicMock()

        sqlalchemy_middleware.process_response(req, resp, resource)
        assert 'session' not in req.context
