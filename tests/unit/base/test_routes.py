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


from myreco.base.routes import Route
from myreco.base.actions import (DefaultPostActions, DefaultPutActions,
    DefaultPatchActions, DefaultDeleteActions, DefaultGetActions)
from myreco.base.models.sqlalchemy_redis import SQLAlchemyRedisModelRoutesBuilderBase
from jsonschema import ValidationError
from unittest import mock
from io import StringIO
from falcon import HTTPNotFound, HTTP_NOT_FOUND, HTTP_NO_CONTENT, HTTP_CREATED
from collections import OrderedDict

import pytest
import sqlalchemy as sa


class TestRouteRegister(object):

    def test_without_validator_and_output_schema(self):
        route = Route('/test', 'POST', lambda x: x)
        api, model = mock.MagicMock(), mock.MagicMock()
        route.register(api, model)
        assert not api.add_sink.called

    def test_with_validator_and_without_output_schema(self):
        route = Route('/test', 'POST', lambda x: x, mock.MagicMock())
        api, model = mock.MagicMock(), mock.MagicMock()
        route.register(api, model)
        assert api.add_sink.call_args_list == [
            mock.call(route._sink_schemas, '/test/_schemas/post'),
            mock.call(route._sink_input_schema, '/test/_schemas/post/input')
        ]

    def test_without_validator_and_with_output_schema(self):
        route = Route('/test', 'POST', lambda x: x,
                      output_schema=mock.MagicMock())
        api, model = mock.MagicMock(), mock.MagicMock()
        route.register(api, model)
        assert api.add_sink.call_args_list == [
            mock.call(route._sink_schemas, '/test/_schemas/post'),
            mock.call(route._sink_output_schema, '/test/_schemas/post/output')
        ]

    @mock.patch('myreco.base.models.sqlalchemy_redis.dict', new=OrderedDict)
    def test_with_validator_and_output_schema(self):
        route = Route('/test', 'POST', lambda x: x,
                      mock.MagicMock(), mock.MagicMock())
        api, model = mock.MagicMock(), mock.MagicMock()
        route.register(api, model)
        call1 = mock.call(route._sink_schemas, '/test/_schemas/post')
        call2 = mock.call(route._sink_input_schema, '/test/_schemas/post/input')
        call3 = mock.call(route._sink_output_schema, '/test/_schemas/post/output')
        assert api.add_sink.call_args_list == [call1, call2, call3] \
            or api.add_sink.call_args_list == [call1, call3, call2]


@pytest.fixture
def model(model_base):
    class model(model_base):
        __tablename__ = 'model'
        id = sa.Column(sa.Integer, primary_key=True)

    return model


def _get_sorted_key_from_route(route):
    return (route.action.__self__.__class__.__name__, route.action.__name__)


class TestSQLAlchemyRedisModelRoutesBuilderBaseWithDefaultArguments(object):

    def test_without_schemas_dir(self, model):
        routes = SQLAlchemyRedisModelRoutesBuilderBase(model)
        assert routes == set()

    def test_with_schemas_dir_without_matched_files(self, model):
        routes = None
        with mock.patch('myreco.base.models.sqlalchemy_redis.glob') as glob:
            glob.return_value = ['test', 'test2']
            routes = SQLAlchemyRedisModelRoutesBuilderBase(model)
        assert routes == set()

    @mock.patch('myreco.base.models.sqlalchemy_redis.glob')
    @mock.patch('myreco.base.models.sqlalchemy_redis.open')
    def test_with_schemas_dir_with_matched_files_without_uri(self, open_, glob, model):
        routes = None
        glob.return_value = ['post_input.json']
        open_.return_value = StringIO('{"type": "object"}')
        routes = list(SQLAlchemyRedisModelRoutesBuilderBase(model))

        assert routes[0].uri_template == '/model'
        assert routes[0].method == 'POST'
        assert routes[0].action == DefaultPostActions.base_action
        assert routes[0].validator.schema == {'type': 'object'}

    @mock.patch('myreco.base.models.sqlalchemy_redis.glob')
    @mock.patch('myreco.base.models.sqlalchemy_redis.open')
    def test_with_schemas_dir_with_input_output_matched_files(self, open_, glob, model):
        routes = None
        glob.return_value = ['post_input.json', 'post_output.json']
        open_.side_effect = [
            StringIO('{"type": "object"}'), StringIO('{"type": "string"}')]
        routes = list(SQLAlchemyRedisModelRoutesBuilderBase(model))

        assert routes[0].uri_template == '/model'
        assert routes[0].method == 'POST'
        assert routes[0].action == DefaultPostActions.base_action
        assert routes[0].validator.schema == {'type': 'object'}
        assert routes[0].output_schema == {'type': 'string'}

    @mock.patch('myreco.base.models.sqlalchemy_redis.glob')
    @mock.patch('myreco.base.models.sqlalchemy_redis.open')
    def test_with_schemas_dir_with_matched_files_with_uri(self, open_, glob, model):
        routes = None
        glob.return_value = ['%test%__%test2%_post_input.json']
        open_.return_value = StringIO('{"test": "test"}')
        routes = list(SQLAlchemyRedisModelRoutesBuilderBase(model))

        assert routes[0].uri_template == '/model/{test}/{test2}'
        assert routes[0].method == 'POST'
        assert routes[
            0].action == DefaultPostActions.ids_action
        assert routes[0].validator.schema == {'test': 'test'}

    @mock.patch('myreco.base.models.sqlalchemy_redis.glob')
    @mock.patch('myreco.base.models.sqlalchemy_redis.open')
    def test_with_schemas_dir_with_matched_files_with_uri_with_two_methods(self, open_, glob, model):
        routes = None
        glob.return_value = [
            '%test%__%test2%_post_input.json', '%test%_%test2%_put_input.json']
        open_.side_effect = [
            StringIO('{"test": "test"}'), StringIO('{"test": "test"}')]
        routes = list(SQLAlchemyRedisModelRoutesBuilderBase(model))
        routes = sorted(routes, key=_get_sorted_key_from_route)

        assert routes[0].uri_template == '/model/{test}/{test2}'
        assert routes[0].method == 'POST'
        assert routes[0].action == DefaultPostActions.ids_action
        assert routes[0].validator.schema == {'test': 'test'}

        assert routes[1].uri_template == '/model/{test}_{test2}'
        assert routes[1].method == 'PUT'
        assert routes[1].action == DefaultPutActions.ids_action
        assert routes[1].validator.schema == {'test': 'test'}


class TestSQLAlchemyRedisModelRoutesBuilderBaseJustWithGenericRoutes(object):

    def test_with_one_id(self, model):
        routes = SQLAlchemyRedisModelRoutesBuilderBase(
            model, build_from_schemas=False, build_generic=True)
        assert len(routes) == 10
        routes = sorted(routes, key=_get_sorted_key_from_route)

        assert routes[0].uri_template == '/model'
        assert routes[0].method == 'DELETE'
        assert routes[0].action == DefaultDeleteActions.base_action
        assert routes[0].validator is None
        assert routes[0].output_schema is None

        assert routes[1].uri_template == '/model/{id}'
        assert routes[1].method == 'DELETE'
        assert routes[1].action == DefaultDeleteActions.ids_action
        assert routes[1].validator is None
        assert routes[1].output_schema is None

        assert routes[2].uri_template == '/model'
        assert routes[2].method == 'GET'
        assert routes[2].action == DefaultGetActions.base_action
        assert routes[2].validator is None
        assert routes[2].output_schema is None

        assert routes[3].uri_template == '/model/{id}'
        assert routes[3].method == 'GET'
        assert routes[3].action == DefaultGetActions.ids_action
        assert routes[3].validator is None
        assert routes[3].output_schema is None

        assert routes[4].uri_template == '/model'
        assert routes[4].method == 'PATCH'
        assert routes[4].action == DefaultPatchActions.base_action
        assert routes[4].validator is None
        assert routes[4].output_schema is None

        assert routes[5].uri_template == '/model/{id}'
        assert routes[5].method == 'PATCH'
        assert routes[5].action == DefaultPatchActions.ids_action
        assert routes[5].validator is None
        assert routes[5].output_schema is None

        assert routes[6].uri_template == '/model'
        assert routes[6].method == 'POST'
        assert routes[6].action == DefaultPostActions.base_action
        assert routes[6].validator is None
        assert routes[6].output_schema is None

        assert routes[7].uri_template == '/model/{id}'
        assert routes[7].method == 'POST'
        assert routes[7].action == DefaultPostActions.ids_action
        assert routes[7].validator is None
        assert routes[7].output_schema is None

        assert routes[8].uri_template == '/model'
        assert routes[8].method == 'PUT'
        assert routes[8].action == DefaultPutActions.base_action
        assert routes[8].validator is None
        assert routes[8].output_schema is None

        assert routes[9].uri_template == '/model/{id}'
        assert routes[9].method == 'PUT'
        assert routes[9].action == DefaultPutActions.ids_action
        assert routes[9].validator is None
        assert routes[9].output_schema is None

    def test_with_two_ids(self, model_base):
        class model(model_base):
            __tablename__ = 'model'
            id = sa.Column(sa.Integer, primary_key=True)
            id2 = sa.Column(sa.Integer, primary_key=True)

        routes = SQLAlchemyRedisModelRoutesBuilderBase(
            model, build_from_schemas=False, build_generic=True)
        assert len(routes) == 10
        routes = sorted(routes, key=_get_sorted_key_from_route)

        assert routes[0].uri_template == '/model'
        assert routes[0].method == 'DELETE'
        assert routes[0].action == DefaultDeleteActions.base_action
        assert routes[0].validator is None
        assert routes[0].output_schema is None

        assert routes[1].uri_template == '/model/{id}/{id2}'
        assert routes[1].method == 'DELETE'
        assert routes[1].action == DefaultDeleteActions.ids_action
        assert routes[1].validator is None
        assert routes[1].output_schema is None

        assert routes[2].uri_template == '/model'
        assert routes[2].method == 'GET'
        assert routes[2].action == DefaultGetActions.base_action
        assert routes[2].validator is None
        assert routes[2].output_schema is None

        assert routes[3].uri_template == '/model/{id}/{id2}'
        assert routes[3].method == 'GET'
        assert routes[3].action == DefaultGetActions.ids_action
        assert routes[3].validator is None
        assert routes[3].output_schema is None

        assert routes[4].uri_template == '/model'
        assert routes[4].method == 'PATCH'
        assert routes[4].action == DefaultPatchActions.base_action
        assert routes[4].validator is None
        assert routes[4].output_schema is None

        assert routes[5].uri_template == '/model/{id}/{id2}'
        assert routes[5].method == 'PATCH'
        assert routes[5].action == DefaultPatchActions.ids_action
        assert routes[5].validator is None
        assert routes[5].output_schema is None

        assert routes[6].uri_template == '/model'
        assert routes[6].method == 'POST'
        assert routes[6].action == DefaultPostActions.base_action
        assert routes[6].validator is None
        assert routes[6].output_schema is None

        assert routes[7].uri_template == '/model/{id}/{id2}'
        assert routes[7].method == 'POST'
        assert routes[7].action == DefaultPostActions.ids_action
        assert routes[7].validator is None
        assert routes[7].output_schema is None

        assert routes[8].uri_template == '/model'
        assert routes[8].method == 'PUT'
        assert routes[8].action == DefaultPutActions.base_action
        assert routes[8].validator is None
        assert routes[8].output_schema is None

        assert routes[9].uri_template == '/model/{id}/{id2}'
        assert routes[9].method == 'PUT'
        assert routes[9].action == DefaultPutActions.ids_action
        assert routes[9].validator is None
        assert routes[9].output_schema is None


class TestRoutesModelNameUriDeleteAction(object):

    def test_action(self, model):
        model.delete = mock.MagicMock()
        routes = SQLAlchemyRedisModelRoutesBuilderBase(
            model, build_from_schemas=False, build_generic=True)
        routes = sorted(routes, key=_get_sorted_key_from_route)
        context = {
            'model': model,
            'session': mock.MagicMock(),
            'body': [{}]
        }
        req = mock.MagicMock(context=context)
        resp = mock.MagicMock()
        routes[0].action(req, resp)
        assert resp.status == HTTP_NO_CONTENT


class TestRoutesModelNameUriGetAction(object):

    def test_without_body(self, model):
        model.get = mock.MagicMock(return_value=[{'test': 'test'}])
        routes = SQLAlchemyRedisModelRoutesBuilderBase(
            model, build_from_schemas=False, build_generic=True)
        routes = sorted(routes, key=_get_sorted_key_from_route)
        context = {
            'model': model,
            'session': mock.MagicMock(),
            'body': {}
        }
        req = mock.MagicMock(context=context)
        resp = mock.MagicMock()
        routes[2].action(req, resp)
        assert model.get.call_args_list == [mock.call(context['session'])]
        assert resp.body == [{'test': 'test'}]

    def test_with_body(self, model):
        model.get = mock.MagicMock(return_value=[{'test': 'test'}])
        routes = SQLAlchemyRedisModelRoutesBuilderBase(
            model, build_from_schemas=False, build_generic=True)
        routes = sorted(routes, key=_get_sorted_key_from_route)
        context = {
            'model': model,
            'session': mock.MagicMock(),
            'body': [{}]
        }
        req = mock.MagicMock(context=context)
        resp = mock.MagicMock()
        routes[2].action(req, resp)
        assert model.get.call_args_list == [
            mock.call(context['session'], context['body'])]
        assert resp.body == [{'test': 'test'}]


class TestRoutesModelNameUriPatchAction(object):

    def test_raises_not_found(self, model):
        model.update = mock.MagicMock(return_value=[])
        routes = SQLAlchemyRedisModelRoutesBuilderBase(
            model, build_from_schemas=False, build_generic=True)
        routes = sorted(routes, key=_get_sorted_key_from_route)
        context = {
            'model': model,
            'session': mock.MagicMock(),
            'body': {}
        }
        req = mock.MagicMock(context=context)
        resp = mock.MagicMock()
        with pytest.raises(HTTPNotFound):
            routes[4].action(req, resp)

    def test_action(self, model):
        model.update = mock.MagicMock(return_value=[{'test': 'test'}])
        routes = SQLAlchemyRedisModelRoutesBuilderBase(
            model, build_from_schemas=False, build_generic=True)
        routes = sorted(routes, key=_get_sorted_key_from_route)
        context = {
            'model': model,
            'session': mock.MagicMock(),
            'body': [{}]
        }
        req = mock.MagicMock(context=context)
        resp = mock.MagicMock()
        routes[4].action(req, resp)
        assert resp.body == [{'test': 'test'}]


class TestRoutesModelNameUriPostAction(object):

    def test_with_a_object_in_body(self, model):
        model.insert = mock.MagicMock(return_value=[{'test': 'test'}])
        routes = SQLAlchemyRedisModelRoutesBuilderBase(
            model, build_from_schemas=False, build_generic=True)
        routes = sorted(routes, key=_get_sorted_key_from_route)
        context = {
            'model': model,
            'session': mock.MagicMock(),
            'body': {}
        }
        req = mock.MagicMock(context=context)
        resp = mock.MagicMock()
        routes[6].action(req, resp)
        assert resp.body == {'test': 'test'}
        assert resp.status == HTTP_CREATED

    def test_with_a_list_in_body(self, model):
        model.insert = mock.MagicMock(return_value=[{'test': 'test'}])
        routes = SQLAlchemyRedisModelRoutesBuilderBase(
            model, build_from_schemas=False, build_generic=True)
        routes = sorted(routes, key=_get_sorted_key_from_route)
        context = {
            'model': model,
            'session': mock.MagicMock(),
            'body': [{}]
        }
        req = mock.MagicMock(context=context)
        resp = mock.MagicMock()
        routes[6].action(req, resp)
        assert resp.body == [{'test': 'test'}]
        assert resp.status == HTTP_CREATED


class TestRoutesModelNameUriPutAction(object):

    def test_raises_not_found(self, model):
        model.update = mock.MagicMock(return_value=[])
        routes = SQLAlchemyRedisModelRoutesBuilderBase(
            model, build_from_schemas=False, build_generic=True)
        routes = sorted(routes, key=_get_sorted_key_from_route)
        context = {
            'model': model,
            'session': mock.MagicMock(),
            'body': {}
        }
        req = mock.MagicMock(context=context)
        resp = mock.MagicMock()
        with pytest.raises(HTTPNotFound):
            routes[8].action(req, resp)

    def test_action(self, model):
        model.update = mock.MagicMock(return_value=[{'test': 'test'}])
        routes = SQLAlchemyRedisModelRoutesBuilderBase(
            model, build_from_schemas=False, build_generic=True)
        routes = sorted(routes, key=_get_sorted_key_from_route)
        context = {
            'model': model,
            'session': mock.MagicMock(),
            'body': [{}]
        }
        req = mock.MagicMock(context=context)
        resp = mock.MagicMock()
        routes[8].action(req, resp)
        assert resp.body == [{'test': 'test'}]


class TestRoutesPrimariesKeysUriDeleteAction(object):

    def test_action(self, model):
        model.delete = mock.MagicMock()
        routes = SQLAlchemyRedisModelRoutesBuilderBase(
            model, build_from_schemas=False, build_generic=True)
        routes = sorted(routes, key=_get_sorted_key_from_route)
        context = {
            'model': model,
            'session': mock.MagicMock(),
            'body': {}
        }
        req = mock.MagicMock(context=context)
        resp = mock.MagicMock()
        routes[1].action(req, resp, test='test')
        assert model.delete.call_args_list == [
            mock.call(context['session'], {'test': 'test'})]
        assert resp.status == HTTP_NO_CONTENT


class TestRoutesPrimariesKeysUriGetAction(object):

    def test_action(self, model):
        model.get = mock.MagicMock()
        routes = SQLAlchemyRedisModelRoutesBuilderBase(
            model, build_from_schemas=False, build_generic=True)
        routes = sorted(routes, key=_get_sorted_key_from_route)
        context = {
            'model': model,
            'session': mock.MagicMock(),
            'body': {}
        }
        req = mock.MagicMock(context=context)
        resp = mock.MagicMock()
        routes[3].action(req, resp, test='test')
        assert model.get.call_args_list == [
            mock.call(context['session'], {'test': 'test'})]


class TestRoutesPrimariesKeysUriPatchAction(object):

    def test_raises_not_found(self, model):
        model.update = mock.MagicMock(return_value=[])
        routes = SQLAlchemyRedisModelRoutesBuilderBase(
            model, build_from_schemas=False, build_generic=True)
        routes = sorted(routes, key=_get_sorted_key_from_route)
        context = {
            'model': model,
            'session': mock.MagicMock(),
            'body': {}
        }
        req = mock.MagicMock(context=context)
        resp = mock.MagicMock()
        with pytest.raises(HTTPNotFound):
            routes[5].action(req, resp, test='test')

    def test_action(self, model):
        model.update = mock.MagicMock(return_value=[{'test': 'test'}])
        routes = SQLAlchemyRedisModelRoutesBuilderBase(
            model, build_from_schemas=False, build_generic=True)
        routes = sorted(routes, key=_get_sorted_key_from_route)
        context = {
            'model': model,
            'session': mock.MagicMock(),
            'body': {}
        }
        req = mock.MagicMock(context=context)
        resp = mock.MagicMock()
        routes[5].action(req, resp, test='test')
        assert resp.body == {'test': 'test'}
        assert model.update.call_args_list == [
            mock.call(context['session'], {'test': 'test'}, ids={'test': 'test'})]


class TestRoutesPrimariesKeysUriPostAction(object):

    def test_with_a_object_in_body(self, model):
        model.insert = mock.MagicMock(return_value=[{'test': 'test'}])
        routes = SQLAlchemyRedisModelRoutesBuilderBase(
            model, build_from_schemas=False, build_generic=True)
        routes = sorted(routes, key=_get_sorted_key_from_route)
        context = {
            'model': model,
            'session': mock.MagicMock(),
            'body': {}
        }
        req = mock.MagicMock(context=context)
        resp = mock.MagicMock()
        routes[7].action(req, resp, test='test')
        assert resp.body == {'test': 'test'}
        assert resp.status == HTTP_CREATED
        assert model.insert.call_args_list == [
            mock.call(context['session'], {'test': 'test'})]

    def test_with_a_list_in_body(self, model):
        model.insert = mock.MagicMock(return_value=[{'test': 'test'}])
        routes = SQLAlchemyRedisModelRoutesBuilderBase(
            model, build_from_schemas=False, build_generic=True)
        routes = sorted(routes, key=_get_sorted_key_from_route)
        context = {
            'model': model,
            'session': mock.MagicMock(),
            'body': [{}]
        }
        req = mock.MagicMock(context=context)
        resp = mock.MagicMock()
        routes[7].action(req, resp, test='test')
        assert resp.body == [{'test': 'test'}]
        assert resp.status == HTTP_CREATED
        assert model.insert.call_args_list == [
            mock.call(context['session'], [{'test': 'test'}])]


class TestRoutesPrimariesKeysUriPutAction(object):

    def test_with_insert(self, model):
        model.update = mock.MagicMock(return_value=[])
        model.insert = mock.MagicMock(return_value=[{'test': 'test'}])
        routes = SQLAlchemyRedisModelRoutesBuilderBase(
            model, build_from_schemas=False, build_generic=True)
        routes = sorted(routes, key=_get_sorted_key_from_route)
        context = {
            'model': model,
            'session': mock.MagicMock(),
            'body': {},
            'route': mock.MagicMock()
        }
        req = mock.MagicMock(context=context)
        resp = mock.MagicMock()
        routes[9].action(req, resp, test='test')
        assert resp.body == {'test': 'test'}
        assert resp.status == HTTP_CREATED
        assert model.insert.call_args_list == [
            mock.call(context['session'], {'test': 'test'})]

    def test_with_update(self, model):
        model.update = mock.MagicMock(return_value=[{'test': 'test'}])
        routes = SQLAlchemyRedisModelRoutesBuilderBase(
            model, build_from_schemas=False, build_generic=True)
        routes = sorted(routes, key=_get_sorted_key_from_route)
        context = {
            'model': model,
            'session': mock.MagicMock(),
            'body': {},
            'route': mock.MagicMock()
        }
        req = mock.MagicMock(context=context)
        resp = mock.MagicMock()
        routes[9].action(req, resp, test='test')
        assert resp.body == {'test': 'test'}
        assert model.update.call_args_list == [
            mock.call(context['session'], {'test': 'test'}, ids={'test': 'test'})]

    def test_raises_ambigous_values(self, model):
        model.update = mock.MagicMock(return_value=[])
        routes = SQLAlchemyRedisModelRoutesBuilderBase(
            model, build_from_schemas=False, build_generic=True)
        routes = sorted(routes, key=_get_sorted_key_from_route)
        context = {
            'model': model,
            'session': mock.MagicMock(),
            'body': {'test': 'test'},
            'route': mock.MagicMock()
        }
        req = mock.MagicMock(context=context)
        resp = mock.MagicMock()
        with pytest.raises(ValidationError):
            routes[9].action(req, resp, test='test2')
