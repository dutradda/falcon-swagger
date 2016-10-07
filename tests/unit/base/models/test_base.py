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


from myreco.base.models.base import ModelBaseMeta, ModelBase
from myreco.base.router import ModelRouter
from myreco.exceptions import ModelBaseError
from falcon.errors import HTTPNotFound, HTTPMethodNotAllowed
from jsonschema import ValidationError
from unittest import mock
import pytest


class TestModelBaseErrors(object):
    def test_without_schema_and_without_key(self):
        model = ModelBaseMeta('TestModel', (ModelBase,), {})
        assert model.__key__ == 'test'
        assert not hasattr(model, '__schema__')

    def test_without_schema_and_with_key(self):
        model = ModelBaseMeta('TestModel', (ModelBase,), {'__key__': 'test123'})
        assert model.__key__ == 'test123'

    def test_with_schema_without_operation_id(self):
        schema = {
            '/test': {
                'post': {
                    'responses': {'200': {'description': 'test'}}
                }
            }
        }
        with pytest.raises(ValidationError) as exc_info:
            ModelBaseMeta('TestModel', (ModelBase,), {'__schema__': schema})
        assert exc_info.value.message == "'operationId' is a required property"

    def test_with_schema_with_operation_with_parameters_with_invalid_operationId(self):
        schema = {
            '/test': {
                'post': {
                    'responses': {'200': {'description': 'test'}},
                    'operationId': 'test',
                    'parameters': [{
                        'name': 'test',
                        'in': 'query',
                        'type': 'array'
                    }]
                }
            }
        }
        with pytest.raises(ModelBaseError) as exc_info:
            ModelBaseMeta('TestModel', (ModelBase,), {'__schema__': schema})
        assert exc_info.value.args[0] == "'operationId' 'test' was not found"

    def test_raises_method_not_allowed_error(self):
        schema = {
            '/test': {
                'post': {
                    'responses': {'200': {'description': 'test'}},
                    'operationId': 'post_by_body',
                    'parameters': [{
                        'name': 'test',
                        'in': 'query',
                        'type': 'array'
                    }]
                }
            }
        }
        req = mock.MagicMock(path='/test', method='GET')
        model = ModelBaseMeta('TestModel', (ModelBase,), {'__schema__': schema})
        router = ModelRouter()
        router.add_model(model)
        with pytest.raises(HTTPMethodNotAllowed) as exc_info:
            route, _ = router.get_route_and_params(req)
        assert exc_info.value.headers == {'Allow': 'POST'}


class TestModelBase(object):
    def test_resp_add_link(self):
        schema = {
            '/test': {
                'post': {
                    'responses': {'200': {'description': 'test'}},
                    'operationId': 'post_by_body',
                    'parameters': [{
                        'name': 'test',
                        'in': 'query',
                        'type': 'array'
                    }]
                }
            }
        }
        req = mock.MagicMock(path='/test', method='POST', params={})
        resp = mock.MagicMock()
        model = ModelBaseMeta('TestModel', (ModelBase,), {'__schema__': schema})
        model.insert = mock.MagicMock(return_value=[{}])
        router = ModelRouter()
        router.add_model(model)
        route, _ = router.get_route_and_params(req)
        route(req, resp)
        assert resp.add_link.call_args_list == [mock.call('/test/_schema/', 'schema')]


class TestModelBaseBuildsQueryStringParameters(object):
    def test_if_operation_builds_query_string_parameters_with_array_without_items_as_string(self):
        schema = {
            '/test': {
                'post': {
                    'responses': {'200': {'description': 'test'}},
                    'operationId': 'post_by_body',
                    'parameters': [{
                        'name': 'test',
                        'in': 'query',
                        'type': 'array'
                    }]
                }
            }
        }
        model = ModelBaseMeta('TestModel', (ModelBase,), {'__schema__': schema})
        model.insert = mock.MagicMock(return_value=[{}])
        req = mock.MagicMock(
            context={'session': mock.MagicMock()},
            params={'test': '1,2,3,4'},
            path='/test',
            method='POST')
        req.get_header.return_value = None
        resp = mock.MagicMock()
        router = ModelRouter()
        router.add_model(model)
        route, _ = router.get_route_and_params(req)
        route(req, resp)
        kwargs_expected = {'test': ['1', '2', '3', '4']}

        assert model.insert.call_args_list == [
            mock.call(req.context['session'], req.context['parameters']['body'], **kwargs_expected)
        ]

    def test_if_operation_builds_query_string_parameters_with_array_without_items_as_list(self):
        schema = {
            '/test': {
                'post': {
                    'responses': {'200': {'description': 'test'}},
                    'operationId': 'post_by_body',
                    'parameters': [{
                        'name': 'test',
                        'in': 'query',
                        'type': 'array'
                    }]
                }
            }
        }
        model = ModelBaseMeta('TestModel', (ModelBase,), {'__schema__': schema})
        model.insert = mock.MagicMock(return_value=[{}])
        req = mock.MagicMock(
            context={'session': mock.MagicMock()},
            params={'test': ['1', '2', '3', '4']},
            path='/test',
            method='POST')
        resp = mock.MagicMock()
        router = ModelRouter()
        router.add_model(model)
        route, _ = router.get_route_and_params(req)
        route(req, resp)
        kwargs_expected = {'test': ['1', '2', '3', '4']}

        assert model.insert.call_args_list == [
            mock.call(req.context['session'], req.context['parameters']['body'], **kwargs_expected)
        ]

    def test_if_operation_builds_query_string_parameters_with_array_with_items_as_string(self):
        schema = {
            '/test': {
                'post': {
                    'responses': {'200': {'description': 'test'}},
                    'operationId': 'post_by_body',
                    'parameters': [{
                        'name': 'test',
                        'in': 'query',
                        'type': 'array',
                        'items': {}
                    }]
                }
            }
        }
        model = ModelBaseMeta('TestModel', (ModelBase,), {'__schema__': schema})
        model.insert = mock.MagicMock(return_value=[{}])
        req = mock.MagicMock(
            context={'session': mock.MagicMock()},
            params={'test': '1,2,3,4'},
            path='/test',
            method='POST')
        resp = mock.MagicMock()
        router = ModelRouter()
        router.add_model(model)
        route, _ = router.get_route_and_params(req)
        route(req, resp)
        kwargs_expected = {'test': ['1', '2', '3', '4']}

        assert model.insert.call_args_list == [
            mock.call(req.context['session'], req.context['parameters']['body'], **kwargs_expected)
        ]

    def test_if_operation_builds_query_string_parameters_with_array_with_items_with_type_as_list(self):
        schema = {
            '/test': {
                'post': {
                    'responses': {'200': {'description': 'test'}},
                    'operationId': 'post_by_body',
                    'parameters': [{
                        'name': 'test',
                        'in': 'query',
                        'type': 'array',
                        'items': {'type': 'number'}
                    }]
                }
            }
        }
        model = ModelBaseMeta('TestModel', (ModelBase,), {'__schema__': schema})
        model.insert = mock.MagicMock(return_value=[{}])
        req = mock.MagicMock(
            context={'session': mock.MagicMock()},
            params={'test': ['1', '2', '3', '4']},
            path='/test',
            method='POST')
        resp = mock.MagicMock()
        router = ModelRouter()
        router.add_model(model)
        route, _ = router.get_route_and_params(req)
        route(req, resp)
        kwargs_expected = {'test': [1., 2., 3., 4.]}

        assert model.insert.call_args_list == [
            mock.call(req.context['session'], req.context['parameters']['body'], **kwargs_expected)
        ]

    def test_if_operation_builds_query_string_parameters_with_array_with_items_with_type_as_string(self):
        schema = {
            '/test': {
                'post': {
                    'responses': {'200': {'description': 'test'}},
                    'operationId': 'post_by_body',
                    'parameters': [{
                        'name': 'test',
                        'in': 'query',
                        'type': 'array',
                        'items': {'type': 'number'}
                    }]
                }
            }
        }
        model = ModelBaseMeta('TestModel', (ModelBase,), {'__schema__': schema})
        model.insert = mock.MagicMock(return_value=[{}])
        req = mock.MagicMock(
            context={'session': mock.MagicMock()},
            params={'test': '1,2,3,4'},
            path='/test',
            method='POST')
        resp = mock.MagicMock()
        router = ModelRouter()
        router.add_model(model)
        route, _ = router.get_route_and_params(req)
        route(req, resp)
        kwargs_expected = {'test': [1., 2., 3., 4.]}

        assert model.insert.call_args_list == [
            mock.call(req.context['session'], req.context['parameters']['body'], **kwargs_expected)
        ]


class TestModelBaseBuildsUriTemplateParameters(object):
    def test_if_operation_builds_uri_template_parameters_with_array_without_items_as_string(self):
        schema = {
            '/test': {
                'get': {
                    'responses': {'200': {'description': 'test'}},
                    'operationId': 'get_by_uri_template',
                    'parameters': [{
                        'name': 'test',
                        'in': 'path',
                        'required': True,
                        'type': 'array'
                    }]
                }
            }
        }
        model = ModelBaseMeta('TestModel', (ModelBase,), {'__schema__': schema})
        model.get = mock.MagicMock(return_value=[{}])
        req = mock.MagicMock(
            context={'session': mock.MagicMock()},
            path='/test',
            method='GET')
        resp = mock.MagicMock()
        router = ModelRouter()
        router.add_model(model)
        route, _ = router.get_route_and_params(req)
        route(req, resp, **{'test': '1,2,3,4'})
        kwargs_expected = {'test': ['1', '2', '3', '4']}

        assert model.get.call_args_list == [
            mock.call(req.context['session'], kwargs_expected)
        ]

    def test_if_operation_builds_uri_template_parameters_with_array_with_items_as_string(self):
        schema = {
            '/test': {
                'get': {
                    'responses': {'200': {'description': 'test'}},
                    'operationId': 'get_by_uri_template',
                    'parameters': [{
                        'name': 'test',
                        'in': 'path',
                        'required': True,
                        'type': 'array',
                        'items': {}
                    }]
                }
            }
        }
        model = ModelBaseMeta('TestModel', (ModelBase,), {'__schema__': schema})
        model.get = mock.MagicMock(return_value=[{}])
        req = mock.MagicMock(
            context={'session': mock.MagicMock()},
            path='/test',
            method='GET')
        resp = mock.MagicMock()
        router = ModelRouter()
        router.add_model(model)
        route, _ = router.get_route_and_params(req)
        route(req, resp, **{'test': '1,2,3,4'})
        kwargs_expected = {'test': ['1', '2', '3', '4']}

        assert model.get.call_args_list == [
            mock.call(req.context['session'], kwargs_expected)
        ]

    def test_if_operation_builds_uri_template_parameters_with_array_with_items_with_type_as_string(self):
        schema = {
            '/test': {
                'get': {
                    'responses': {'200': {'description': 'test'}},
                    'operationId': 'get_by_uri_template',
                    'parameters': [{
                        'name': 'test',
                        'in': 'path',
                        'required': True,
                        'type': 'array',
                        'items': {'type': 'number'}
                    }]
                }
            }
        }
        model = ModelBaseMeta('TestModel', (ModelBase,), {'__schema__': schema})
        model.get = mock.MagicMock(return_value=[{}])
        req = mock.MagicMock(
            context={'session': mock.MagicMock()},
            path='/test',
            method='GET')
        resp = mock.MagicMock()
        router = ModelRouter()
        router.add_model(model)
        route, _ = router.get_route_and_params(req)
        route(req, resp, **{'test': '1,2,3,4'})
        kwargs_expected = {'test': [1., 2., 3., 4.]}

        assert model.get.call_args_list == [
            mock.call(req.context['session'], kwargs_expected)
        ]


class TestModelBaseBuildsHeadersParameters(object):
    def test_if_operation_builds_headers_parameters_with_array_without_items_as_string(self):
        schema = {
            '/test': {
                'post': {
                    'responses': {'200': {'description': 'test'}},
                    'operationId': 'post_by_body',
                    'parameters': [{
                        'name': 'test',
                        'in': 'header',
                        'type': 'array'
                    }]
                }
            }
        }
        model = ModelBaseMeta('TestModel', (ModelBase,), {'__schema__': schema})
        model.insert = mock.MagicMock(return_value=[{}])
        req = mock.MagicMock(
            context={'session': mock.MagicMock()},
            path='/test',
            method='POST')
        req.get_header.return_value = '1,2,3,4'
        resp = mock.MagicMock()
        router = ModelRouter()
        router.add_model(model)
        route, _ = router.get_route_and_params(req)
        route(req, resp)
        kwargs_expected = {'test': ['1', '2', '3', '4']}

        assert req.get_header.call_args_list == [mock.call('test')]
        assert model.insert.call_args_list == [
            mock.call(req.context['session'], req.context['parameters']['body'], **kwargs_expected)
        ]

    def test_if_operation_builds_headers_parameters_with_array_with_items_as_string(self):
        schema = {
            '/test': {
                'post': {
                    'responses': {'200': {'description': 'test'}},
                    'operationId': 'post_by_body',
                    'parameters': [{
                        'name': 'test',
                        'in': 'header',
                        'type': 'array',
                        'items': {}
                    }]
                }
            }
        }
        model = ModelBaseMeta('TestModel', (ModelBase,), {'__schema__': schema})
        model.insert = mock.MagicMock(return_value=[{}])
        req = mock.MagicMock(
            context={'session': mock.MagicMock()},
            path='/test',
            method='POST')
        req.get_header.return_value = '1,2,3,4'
        resp = mock.MagicMock()
        router = ModelRouter()
        router.add_model(model)
        route, _ = router.get_route_and_params(req)
        route(req, resp)
        kwargs_expected = {'test': ['1', '2', '3', '4']}

        assert model.insert.call_args_list == [
            mock.call(req.context['session'], req.context['parameters']['body'], **kwargs_expected)
        ]

    def test_if_operation_builds_headers_parameters_with_array_with_items_with_type_as_string(self):
        schema = {
            '/test': {
                'post': {
                    'responses': {'200': {'description': 'test'}},
                    'operationId': 'post_by_body',
                    'parameters': [{
                        'name': 'test',
                        'in': 'header',
                        'type': 'array',
                        'items': {'type': 'number'}
                    }]
                }
            }
        }
        model = ModelBaseMeta('TestModel', (ModelBase,), {'__schema__': schema})
        model.insert = mock.MagicMock(return_value=[{}])
        req = mock.MagicMock(
            context={'session': mock.MagicMock()},
            path='/test',
            method='POST')
        req.get_header.return_value = '1,2,3,4'
        resp = mock.MagicMock()
        router = ModelRouter()
        router.add_model(model)
        route, _ = router.get_route_and_params(req)
        route(req, resp)
        kwargs_expected = {'test': [1., 2., 3., 4.]}

        assert model.insert.call_args_list == [
            mock.call(req.context['session'], req.context['parameters']['body'], **kwargs_expected)
        ]
