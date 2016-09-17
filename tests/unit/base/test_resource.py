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


from myreco.base.resource import FalconModelResource
from falcon.errors import HTTPMethodNotAllowed, HTTPNotFound
from falcon import HTTP_CREATED, HTTP_NO_CONTENT
from unittest import mock

import pytest
import sqlalchemy as sa


@pytest.fixture
def api():
    return mock.MagicMock()


@pytest.fixture
def model(model_base):
    class test(model_base):
        __tablename__ = 'test'
        id_names = ['id_test']
        id_test = sa.Column(sa.Integer, primary_key=True)
    return test


@pytest.fixture
def resource(api, model):
    return FalconModelResource(api, [], model)


class TestFalconModelResource(object):
    def test_if_init_register_routes_corretly(self, api, resource):
        assert api.add_route.call_args_list == [
            mock.call('/test/', resource),
            mock.call('/test/{id_test}/', resource)
        ]

    def test_if_init_register_routes_corretly_with_api_prefix(self, model, api):
        resource = FalconModelResource(api, [], model, '/testing')

        assert api.add_route.call_args_list == [
            mock.call('/testing/test/', resource),
            mock.call('/testing/test/{id_test}/', resource)
        ]

    def test_on_post_raises_method_not_allowed(self, resource):
        with pytest.raises(HTTPMethodNotAllowed):
            resource.on_post(mock.MagicMock(), mock.MagicMock())

    def test_on_put_raises_method_not_allowed(self, resource):
        with pytest.raises(HTTPMethodNotAllowed):
            resource.on_put(mock.MagicMock(), mock.MagicMock())

    def test_on_patch_raises_method_not_allowed(self, resource):
        with pytest.raises(HTTPMethodNotAllowed):
            resource.on_patch(mock.MagicMock(), mock.MagicMock())

    def test_on_delete_raises_method_not_allowed(self, resource):
        with pytest.raises(HTTPMethodNotAllowed):
            resource.on_delete(mock.MagicMock(), mock.MagicMock())

    def test_on_get_raises_method_not_allowed(self, resource):
        with pytest.raises(HTTPMethodNotAllowed):
            resource.on_get(mock.MagicMock(), mock.MagicMock())


class TestFalconModelResourcePost(object):
    def test_on_post_with_id_raises_not_found(self, model, api):
        resource = FalconModelResource(api, ['post'], model)

        with pytest.raises(HTTPNotFound):
            resource.on_post(mock.MagicMock(method='post'), mock.MagicMock(), id_test=1)

    def test_on_post_created_with_object(self, model, api):
        model.insert = mock.MagicMock(return_value=[{'id_test': 1}])
        resource = FalconModelResource(api, ['post'], model, '/testing')
        resp = mock.MagicMock()
        req = mock.MagicMock(method='post')
        req.context = {'body': {}, 'session': mock.MagicMock()}

        resource.on_post(req, resp)

        assert resp.status == HTTP_CREATED
        assert resp.body == {'id_test': 1}

    def test_on_post_created_with_list(self, model, api):
        model.insert = mock.MagicMock(return_value=[{'id_test': 1}])
        resource = FalconModelResource(api, ['post'], model)
        resp = mock.MagicMock()
        req = mock.MagicMock(method='post')
        req.context = {'body': [], 'session': mock.MagicMock()}

        resource.on_post(req, resp)

        assert resp.status == HTTP_CREATED
        assert resp.body == [{'id_test': 1}]

    def test_on_post_with_id_raises_not_found(self, model, api):
        model.update = mock.MagicMock(return_value=[])
        resource = FalconModelResource(api, ['post'], model)
        req = mock.MagicMock(method='post')

        with pytest.raises(HTTPNotFound):
            resource.on_post(req, mock.MagicMock(), id_test=1)


class TestFalconModelResourcePut(object):
    def test_on_put_with_update_no_result_raises_not_found(self, model, api):
        model.update = mock.MagicMock(return_value=[])
        resource = FalconModelResource(api, ['put'], model)
        req = mock.MagicMock(method='put')

        with pytest.raises(HTTPNotFound):
            resource.on_put(req, mock.MagicMock())

    def test_on_put_created(self, model, api):
        model.update = mock.MagicMock(return_value=[])
        model.insert = mock.MagicMock(return_value=[{'id_test': 1}])
        resource = FalconModelResource(api, ['put'], model)
        resp = mock.MagicMock()
        req = mock.MagicMock(method='put')

        resource.on_put(req, resp, id_test=1)

        assert resp.status == HTTP_CREATED
        assert resp.body == {'id_test': 1}

    def test_on_put_with_id(self, model, api):
        model.update = mock.MagicMock(return_value=[{'id_test': 1}])
        resource = FalconModelResource(api, ['put'], model)
        resp = mock.MagicMock()
        req = mock.MagicMock(method='put')

        resource.on_put(req, resp, id_test=1)
        assert resp.body == {'id_test': 1}

    def test_on_put_with_list(self, model, api):
        model.update = mock.MagicMock(return_value=[{'id_test': 1}])
        resource = FalconModelResource(api, ['put'], model)
        resp = mock.MagicMock()
        req = mock.MagicMock(method='put')

        resource.on_put(req, resp)
        assert resp.body == [{'id_test': 1}]


class TestFalconModelResourcePatch(object):
    def test_on_patch_with_update_no_result_raises_not_found(self, model, api):
        model.update = mock.MagicMock(return_value=[])
        resource = FalconModelResource(api, ['patch'], model)
        req = mock.MagicMock(method='patch')

        with pytest.raises(HTTPNotFound):
            resource.on_patch(req, mock.MagicMock())

    def test_on_patch_with_id(self, model, api):
        model.update = mock.MagicMock(return_value=[{'id_test': 1}])
        resource = FalconModelResource(api, ['patch'], model)
        resp = mock.MagicMock()
        req = mock.MagicMock(method='patch')

        resource.on_patch(req, resp, id_test=1)
        assert resp.body == {'id_test': 1}

    def test_on_patch_with_id_no_result_found(self, model, api):
        model.update = mock.MagicMock(return_value=[])
        resource = FalconModelResource(api, ['patch'], model)
        resp = mock.MagicMock()
        req = mock.MagicMock(method='patch')

        with pytest.raises(HTTPNotFound):
            resource.on_patch(req, resp, id_test=1)

    def test_on_patch_with_list(self, model, api):
        model.update = mock.MagicMock(return_value=[{'id_test': 1}])
        resource = FalconModelResource(api, ['patch'], model)
        resp = mock.MagicMock()
        req = mock.MagicMock(method='patch')

        resource.on_patch(req, resp)
        assert resp.body == [{'id_test': 1}]


class TestFalconModelResourceDelete(object):
    def test_on_delete_with_id(self, model, api):
        resource = FalconModelResource(api, ['delete'], model)
        resp = mock.MagicMock()
        req = mock.MagicMock(method='delete')

        resource.on_delete(req, resp, id_test=1)
        assert resp.status == HTTP_NO_CONTENT

    def test_on_delete_with_list(self, model, api):
        resource = FalconModelResource(api, ['delete'], model)
        resp = mock.MagicMock()
        req = mock.MagicMock(method='delete')

        resource.on_delete(req, resp)
        assert resp.status == HTTP_NO_CONTENT


class TestFalconModelResourceGet(object):
    def test_on_get_with_no_result_raises_not_found(self, model):
        model.get = mock.MagicMock(return_value=[])
        resource = FalconModelResource(mock.MagicMock(), ['get'], model)

        with pytest.raises(HTTPNotFound):
            resource.on_get(mock.MagicMock(method='get'), mock.MagicMock())

    def test_on_get_with_id(self, model, api):
        model.get = mock.MagicMock(return_value=[{'id_test': 1}])
        resource = FalconModelResource(api, ['get'], model)
        resp = mock.MagicMock()
        req = mock.MagicMock(method='get')

        resource.on_get(req, resp, id_test=1)
        assert resp.body == {'id_test': 1}

    def test_on_get_with_id_raises_not_found(self, model, api):
        model.get = mock.MagicMock(return_value=[])
        resource = FalconModelResource(api, ['get'], model)
        resp = mock.MagicMock()
        req = mock.MagicMock(method='get')

        with pytest.raises(HTTPNotFound):
            resource.on_get(req, resp, id_test=1)

    def test_on_get_with_list(self, model, api):
        model.get = mock.MagicMock(return_value=[{'id_test': 1}])
        resource = FalconModelResource(api, ['get'], model)
        resp = mock.MagicMock()
        req = mock.MagicMock(method='get')

        resource.on_get(req, resp)
        assert resp.body == [{'id_test': 1}]

    def test_on_get_with_list_raises_not_found(self, model, api):
        model.get = mock.MagicMock(return_value=[])
        resource = FalconModelResource(api, ['get'], model)
        resp = mock.MagicMock()
        req = mock.MagicMock(method='get')

        with pytest.raises(HTTPNotFound):
            resource.on_get(req, resp)

    def test_on_get_without_id_and_body(self, model, api):
        model.get = mock.MagicMock(return_value=[{'id_test': 1}])
        resource = FalconModelResource(api, ['get'], model)
        resp = mock.MagicMock()
        req = mock.MagicMock(method='get', context={'body': {}, 'session': mock.MagicMock()})

        resource.on_get(req, resp)
        assert resp.body == [{'id_test': 1}]
