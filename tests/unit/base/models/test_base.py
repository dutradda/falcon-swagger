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


from falconswagger.models.orm.redis_base import ModelRedisBaseMeta, ModelRedisBase
from falconswagger.models.base import ModelBaseMeta
from falconswagger.middlewares import SwaggerMiddleware
from falconswagger.exceptions import ModelBaseError
from falcon.errors import HTTPNotFound, HTTPMethodNotAllowed
from jsonschema import ValidationError
from unittest import mock
import pytest


class TestModelBaseErrors(object):
    def test_without_schema_and_without_key(self):
        ModelBaseMeta.__all_models__.clear()
        model = ModelRedisBaseMeta('TestModel', (ModelRedisBase,), {})
        assert model.__key__ == 'test'
        assert not hasattr(model, '__schema__')

    def test_without_schema_and_with_key(self):
        ModelBaseMeta.__all_models__.clear()
        model = ModelRedisBaseMeta('TestModel', (ModelRedisBase,), {'__key__': 'test123'})
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
            ModelRedisBaseMeta('TestModel', (ModelRedisBase,), {'__schema__': schema})
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
            ModelRedisBaseMeta('TestModel', (ModelRedisBase,), {'__schema__': schema})
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
        req = mock.MagicMock(uri_template='/test', method='GET')
        model = ModelRedisBaseMeta('TestModel', (ModelRedisBase,), {'__schema__': schema})
        mid = SwaggerMiddleware([model])
        with pytest.raises(HTTPMethodNotAllowed) as exc_info:
            mid.process_resource(req, mock.MagicMock(), model, {})
        assert exc_info.value.headers == {'Allow': 'POST, OPTIONS'} or \
            exc_info.value.headers == {'Allow': 'OPTIONS, POST'}


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
        ModelBaseMeta.__all_models__.clear()
        model = ModelRedisBaseMeta('TestModel', (ModelRedisBase,), {'__schema__': schema})
        model.insert = mock.MagicMock(return_value=[{}])
        req = mock.MagicMock(
            context={'session': mock.MagicMock()},
            params={'test': '1,2,3,4'},
            uri_template='/test',
            method='POST')
        req.get_header.return_value = None
        resp = mock.MagicMock()
        mid = SwaggerMiddleware([model])
        mid.process_resource(req, mock.MagicMock(), model, {})
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
        ModelBaseMeta.__all_models__.clear()
        model = ModelRedisBaseMeta('TestModel', (ModelRedisBase,), {'__schema__': schema})
        model.insert = mock.MagicMock(return_value=[{}])
        req = mock.MagicMock(
            context={'session': mock.MagicMock()},
            params={'test': ['1', '2', '3', '4']},
            uri_template='/test',
            method='POST')
        req.get_header.return_value = None
        resp = mock.MagicMock()
        mid = SwaggerMiddleware([model])
        mid.process_resource(req, mock.MagicMock(), model, {})
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
        ModelBaseMeta.__all_models__.clear()
        model = ModelRedisBaseMeta('TestModel', (ModelRedisBase,), {'__schema__': schema})
        model.insert = mock.MagicMock(return_value=[{}])
        req = mock.MagicMock(
            context={'session': mock.MagicMock()},
            params={'test': '1,2,3,4'},
            uri_template='/test',
            method='POST')
        req.get_header.return_value = None
        resp = mock.MagicMock()
        mid = SwaggerMiddleware([model])
        mid.process_resource(req, mock.MagicMock(), model, {})
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
        ModelBaseMeta.__all_models__.clear()
        model = ModelRedisBaseMeta('TestModel', (ModelRedisBase,), {'__schema__': schema})
        model.insert = mock.MagicMock(return_value=[{}])
        req = mock.MagicMock(
            context={'session': mock.MagicMock()},
            params={'test': ['1', '2', '3', '4']},
            uri_template='/test',
            method='POST')
        req.get_header.return_value = None
        resp = mock.MagicMock()
        mid = SwaggerMiddleware([model])
        mid.process_resource(req, mock.MagicMock(), model, {})
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
        ModelBaseMeta.__all_models__.clear()
        model = ModelRedisBaseMeta('TestModel', (ModelRedisBase,), {'__schema__': schema})
        model.insert = mock.MagicMock(return_value=[{}])
        req = mock.MagicMock(
            context={'session': mock.MagicMock()},
            params={'test': '1,2,3,4'},
            uri_template='/test',
            method='POST')
        req.get_header.return_value = None
        resp = mock.MagicMock()
        mid = SwaggerMiddleware([model])
        mid.process_resource(req, mock.MagicMock(), model, {})
        kwargs_expected = {'test': [1., 2., 3., 4.]}

        assert model.insert.call_args_list == [
            mock.call(req.context['session'], req.context['parameters']['body'], **kwargs_expected)
        ]


class TestModelBaseBuildsUriTemplateParameters(object):
    def test_if_operation_builds_uri_template_parameters_with_array_without_items_as_string(self):
        schema = {
            '/{test}': {
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
        ModelBaseMeta.__all_models__.clear()
        model = ModelRedisBaseMeta('TestModel', (ModelRedisBase,), {'__schema__': schema})
        model.get = mock.MagicMock(return_value=[{}])
        req = mock.MagicMock(
            context={'session': mock.MagicMock()},
            uri_template='/{test}',
            method='GET')
        req.get_header.return_value = None
        resp = mock.MagicMock()
        mid = SwaggerMiddleware([model])
        mid.process_resource(req, mock.MagicMock(), model, {'test': '1,2,3,4'})
        kwargs_expected = {'test': ['1', '2', '3', '4']}

        assert model.get.call_args_list == [
            mock.call(req.context['session'], kwargs_expected)
        ]

    def test_if_operation_builds_uri_template_parameters_with_array_with_items_as_string(self):
        schema = {
            '/{test}': {
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
        ModelBaseMeta.__all_models__.clear()
        model = ModelRedisBaseMeta('TestModel', (ModelRedisBase,), {'__schema__': schema})
        model.get = mock.MagicMock(return_value=[{}])
        req = mock.MagicMock(
            context={'session': mock.MagicMock()},
            uri_template='/{test}',
            method='GET')
        req.get_header.return_value = None
        resp = mock.MagicMock()
        mid = SwaggerMiddleware([model])
        mid.process_resource(req, mock.MagicMock(), model, {'test': '1,2,3,4'})
        kwargs_expected = {'test': ['1', '2', '3', '4']}

        assert model.get.call_args_list == [
            mock.call(req.context['session'], kwargs_expected)
        ]

    def test_if_operation_builds_uri_template_parameters_with_array_with_items_with_type_as_string(self):
        schema = {
            '/{test}': {
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
        ModelBaseMeta.__all_models__.clear()
        model = ModelRedisBaseMeta('TestModel', (ModelRedisBase,), {'__schema__': schema})
        model.get = mock.MagicMock(return_value=[{}])
        req = mock.MagicMock(
            context={'session': mock.MagicMock()},
            uri_template='/{test}',
            method='GET')
        req.get_header.return_value = None
        resp = mock.MagicMock()
        mid = SwaggerMiddleware([model])
        mid.process_resource(req, mock.MagicMock(), model, {'test': '1,2,3,4'})
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
        ModelBaseMeta.__all_models__.clear()
        model = ModelRedisBaseMeta('TestModel', (ModelRedisBase,), {'__schema__': schema})
        model.insert = mock.MagicMock(return_value=[{}])
        req = mock.MagicMock(
            context={'session': mock.MagicMock()},
            uri_template='/test',
            method='POST')
        req.get_header.return_value = '1,2,3,4'
        resp = mock.MagicMock()
        mid = SwaggerMiddleware([model])
        mid.process_resource(req, mock.MagicMock(), model, {})
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
        ModelBaseMeta.__all_models__.clear()
        model = ModelRedisBaseMeta('TestModel', (ModelRedisBase,), {'__schema__': schema})
        model.insert = mock.MagicMock(return_value=[{}])
        req = mock.MagicMock(
            context={'session': mock.MagicMock()},
            uri_template='/test',
            method='POST')
        req.get_header.return_value = '1,2,3,4'
        resp = mock.MagicMock()
        mid = SwaggerMiddleware([model])
        mid.process_resource(req, mock.MagicMock(), model, {})
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
        ModelBaseMeta.__all_models__.clear()
        model = ModelRedisBaseMeta('TestModel', (ModelRedisBase,), {'__schema__': schema})
        model.insert = mock.MagicMock(return_value=[{}])
        req = mock.MagicMock(
            context={'session': mock.MagicMock()},
            uri_template='/test',
            method='POST')
        req.get_header.return_value = '1,2,3,4'
        resp = mock.MagicMock()
        mid = SwaggerMiddleware([model])
        mid.process_resource(req, mock.MagicMock(), model, {})
        kwargs_expected = {'test': [1., 2., 3., 4.]}

        assert model.insert.call_args_list == [
            mock.call(req.context['session'], req.context['parameters']['body'], **kwargs_expected)
        ]
