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


from myreco.base.middlewares import SessionMiddleware
from myreco.base.models.sqlalchemy_redis import SQLAlchemyRedisModelBase
from unittest import mock

import pytest


@pytest.fixture
def bind():
    return mock.MagicMock()


@pytest.fixture
def redis_bind():
    return mock.MagicMock()


@pytest.fixture
def sqlalchemy_middleware(bind, redis_bind):
    return SessionMiddleware(bind, redis_bind)


class TestFalconSQLAlchemyRedisMiddleware(object):
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
