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


from myreco.base.middlewares import FalconRoutesMiddleware, FalconSQLAlchemyRedisMiddleware
from myreco.base.routes import Route
from myreco.base.models.sqlalchemy_redis import SQLAlchemyRedisModelBase
from myreco.exceptions import JSONError
from unittest import mock
from falcon import HTTPMethodNotAllowed, HTTPNotFound

import pytest


@pytest.fixture
def route():
    return Route('/test', 'POST', mock.MagicMock())


@pytest.fixture
def routes_middleware(route):
    return FalconRoutesMiddleware(set([route]))


class TestFalconRoutesMiddlewareProcessResource(object):

    def test_process_resource_without_methods(self):
        middleware = FalconRoutesMiddleware(set())
        req = mock.MagicMock()
        resp, resource, params = mock.MagicMock(), mock.MagicMock(), mock.MagicMock()
        with pytest.raises(HTTPMethodNotAllowed):
            middleware.process_resource(req, resp, resource, params)

    def test_process_resource_with_invalid_json(self, routes_middleware):
        req = mock.MagicMock(method='POST', uri_template='/test')
        req.stream.read().decode.return_value = 'test'
        resp = mock.MagicMock()
        resource = mock.MagicMock()
        params = mock.MagicMock()

        with pytest.raises(JSONError):
            routes_middleware.process_resource(
                req, resp, resource, params)

    def test_process_resource_with_valid_json(self, routes_middleware, route):
        req = mock.MagicMock(
            method='POST', uri_template='/test', context=dict())
        req.stream.read().decode.return_value = '"test"'
        resp = mock.MagicMock()
        resource = mock.MagicMock()
        params = mock.MagicMock()

        routes_middleware.process_resource(req, resp, resource, params)
        assert req.context['body'] == 'test'

    def test_process_resource_with_validator(self):
        validator = mock.MagicMock()
        route = Route('/test', 'POST', mock.MagicMock(), validator)
        middleware = FalconRoutesMiddleware(set([route]))
        req = mock.MagicMock(
            method='POST', uri_template='/test', context=dict())
        req.stream.read().decode.return_value = '"test"'
        resp = mock.MagicMock()
        resource = mock.MagicMock()
        params = mock.MagicMock()

        middleware.process_resource(req, resp, resource, params)
        assert validator.validate.call_args_list == [mock.call('test')]

    def test_if_process_resource_adds_schema_link(self):
        validator = mock.MagicMock()
        route = Route('/test', 'POST', mock.MagicMock(), validator)
        middleware = FalconRoutesMiddleware(set([route]))
        req = mock.MagicMock(
            method='POST', uri_template='/test', context=dict())
        req.stream.read().decode.return_value = '"test"'
        resp = mock.MagicMock()
        resource = mock.MagicMock()
        params = mock.MagicMock()

        middleware.process_resource(req, resp, resource, params)
        assert resp.add_link.call_args_list == [
            mock.call('/test/schemas/', 'schemas')]

    def test_process_resource_with_empty_body(self, routes_middleware):
        req = mock.MagicMock(
            method='POST', uri_template='/test', context=dict())
        req.stream.read().decode.return_value = ''
        resp = mock.MagicMock()
        resource = mock.MagicMock()
        params = mock.MagicMock()

        routes_middleware.process_resource(req, resp, resource, params)
        assert req.context['body'] == {}

    def test_if_raises_not_found(self, routes_middleware):
        req = mock.MagicMock(
            method='POST', uri_template='/', context=dict())
        req.stream.read().decode.return_value = ''
        resp = mock.MagicMock()
        resource = mock.MagicMock()
        params = mock.MagicMock()

        with pytest.raises(HTTPNotFound):
            routes_middleware.process_resource(req, resp, resource, params)


class TestFalconRoutesMiddlewareProcessResponse(object):

    def test_process_response(self, routes_middleware):
        req = mock.MagicMock()
        resp = mock.MagicMock(body='test')
        resource = mock.MagicMock()

        routes_middleware.process_response(req, resp, resource)
        assert resp.body == '"test"'

    def test_process_response_with_empty_body(self, routes_middleware):
        req = mock.MagicMock()
        resp = mock.MagicMock(body='')
        resource = mock.MagicMock()

        routes_middleware.process_response(req, resp, resource)
        assert resp.body == ''


@pytest.fixture
def bind():
    return mock.MagicMock()


@pytest.fixture
def redis_bind():
    return mock.MagicMock()


@pytest.fixture
def sqlalchemy_middleware(bind, redis_bind, route):
    return FalconSQLAlchemyRedisMiddleware(bind, redis_bind, set([route]))


@mock.patch('myreco.base.middlewares.json', new=mock.MagicMock())
class TestFalconSQLAlchemyRedisMiddleware(object):
    def test_init_without_routes(self):
        assert FalconSQLAlchemyRedisMiddleware(None)._routes == dict()

    @mock.patch('myreco.base.middlewares.Session')
    def test_process_resource(self, session, sqlalchemy_middleware, bind, redis_bind):
        req = mock.MagicMock(
            method='POST', uri_template='/test', context=dict())
        resp = mock.MagicMock()
        resource = SQLAlchemyRedisModelBase
        params = mock.MagicMock()

        sqlalchemy_middleware.process_resource(req, resp, resource, params)

        assert session.call_args_list == [
            mock.call(bind=bind, redis_bind=redis_bind)]
        assert req.context['session'] == session.return_value

    def test_process_response(self, sqlalchemy_middleware):
        session = mock.MagicMock()
        req = mock.MagicMock(
            method='POST', uri_template='/test', context={'session': session})
        resp = mock.MagicMock()
        resource = SQLAlchemyRedisModelBase
        params = mock.MagicMock()

        sqlalchemy_middleware.process_response(req, resp, resource)
        assert session.close.call_count == 1

    def test_process_response_without_session(self, sqlalchemy_middleware):
        req = mock.MagicMock(
            method='POST', uri_template='/test', context=dict())
        resp = mock.MagicMock()
        resource = SQLAlchemyRedisModelBase
        params = mock.MagicMock()

        sqlalchemy_middleware.process_response(req, resp, resource)
        assert 'session' not in req.context
