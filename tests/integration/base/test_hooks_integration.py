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


from myreco.base.hooks import AuthorizationHook, before_action
from myreco.base.http_api import HttpAPI
from myreco.base.routes import Route
from unittest import mock


import pytest
import json
import sqlalchemy as sa


@pytest.fixture
def model(model_base):
    def auth_func(session, auth_token, uri, path, method):
        if auth_token == '1' and uri == '/' and method == 'GET':
            return True
        if auth_token == '2':
            return False

    def action(req, resp):
        pass

    class model(model_base):
        __tablename__ = 'model'
        _build_routes_from_schema = False
        id = sa.Column(sa.Integer, primary_key=True)

        __routes__ = {Route('/', 'GET', action, hooks=[before_action(AuthorizationHook(auth_func, 'test'))])}

    return model


@pytest.fixture
def app(model):
    return HttpAPI(mock.MagicMock(), models={model})


class TestAuthorizationHook(object):

    def test_without_header(self, app, model, client):
        resp = client.get('/')
        assert resp.status_code == 401
        assert resp.headers.get('WWW-Authenticate') == 'Basic realm="test"'
        assert resp.body == json.dumps(
            {'error': 'Authorization header is required'})

    def test_with_invalid_authorization(self, app, model, client):
        resp = client.get('/', headers={'Authorization': '3'})
        assert resp.status_code == 401
        assert resp.headers.get('WWW-Authenticate') == 'Basic realm="test"'
        assert resp.body == json.dumps({'error': 'Invalid authorization'})

    def test_with_expired_authorization(self, app, model, client):
        resp = client.get('/', headers={'Authorization': '2'})
        assert resp.status_code == 403
        assert resp.headers.get('WWW-Authenticate') == 'Basic realm="test"'
        assert resp.body == json.dumps(
            {'error': 'Please refresh your authorization'})

    def test_with_valid_authorization(self, app, model, client):
        resp = client.get('/', headers={'Authorization': '1'})
        assert resp.status_code == 200
        assert resp.headers.get('WWW-Authenticate') == None
        assert resp.body == ''

    def test_with_valid_authorization_using_basic(self, app, model, client):
        resp = client.get('/', headers={'Authorization': 'Basic 1'})
        assert resp.status_code == 200
        assert resp.headers.get('WWW-Authenticate') == None
        assert resp.body == ''
