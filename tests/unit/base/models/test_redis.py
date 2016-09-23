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


from myreco.base.models.redis import RedisRoutesBuilder, RedisModelMeta, RedisModelsBuilder
from myreco.base.actions import DefaultPostActions
from myreco.exceptions import ModelBaseError
from unittest import mock
import pytest
import msgpack


class TestRedisRoutesBuilder(object):
    def test_with_empty_routes(self):
        model = mock.MagicMock()
        assert RedisRoutesBuilder(model) == set()

    def test_with_input_schema(self):
        model = mock.MagicMock(__api_prefix__='/')
        routes = [{'uri_template': '/test', 'method': {'name': 'POST'}, 'input_schema': {'test': 'test'}}]
        routes = list(RedisRoutesBuilder(model, routes=routes))
        assert len(routes) == 1
        assert routes[0].uri_template == '/test'
        assert routes[0].method == 'POST'
        assert routes[0].action == DefaultPostActions.base_action
        assert routes[0].validator.schema == {'test': 'test'}
        assert routes[0].output_schema == None


class TestRedisModelsBuilder(object):
    def test_without_models_types(self):
        assert RedisModelsBuilder([]) == set()

    def test_without_prefix_and_without_routes(self):
        models_types = [{
            'name': 'test',
            'id_names': ['id']
        }]
        model = list(RedisModelsBuilder(models_types))
        assert len(model) == 1
        assert model[0].__name__ == 'TestModel'
        assert model[0].__routes__ == set()
        assert model[0].__key__ == 'test'
        assert model[0].__ids_names__ == ('id',)

    def test_without_prefix_and_with_routes(self):
        models_types = [{
            'name': 'test',
            'id_names': ['id'],
            'routes': [{'uri_template': '/test', 'method': {'name': 'POST'}, 'input_schema': {'test': 'test'}}]
        }]
        model = list(RedisModelsBuilder(models_types))
        assert len(model) == 1
        assert model[0].__name__ == 'TestModel'
        assert model[0].__key__ == 'test'
        assert model[0].__ids_names__ == ('id',)
        routes = list(model[0].__routes__)
        assert len(routes) == 1
        assert routes[0].uri_template == '/test'
        assert routes[0].method == 'POST'
        assert routes[0].action == DefaultPostActions.base_action
        assert routes[0].validator.schema == {'test': 'test'}
        assert routes[0].output_schema == None

    def test_with_prefix_and_without_routes(self):
        models_types = [{
            'name': 'test',
            'id_names': ['id']
        }]
        model = list(RedisModelsBuilder(models_types, api_prefix='/api'))
        assert len(model) == 1
        assert model[0].__name__ == 'TestModel'
        assert model[0].__key__ == 'test'
        assert model[0].__ids_names__ == ('id',)

    def test_with_prefix_and_with_routes(self):
        models_types = [{
            'name': 'test',
            'id_names': ['id'],
            'routes': [{'uri_template': '/test', 'method': {'name': 'POST'}, 'input_schema': {'test': 'test'}}]
        }]
        model = list(RedisModelsBuilder(models_types, api_prefix='/api'))
        assert len(model) == 1
        assert model[0].__name__ == 'TestModel'
        assert model[0].__key__ == 'test'
        assert model[0].__ids_names__ == ('id',)
        routes = list(model[0].__routes__)
        assert len(routes) == 1
        assert routes[0].uri_template == '/api/test'
        assert routes[0].method == 'POST'
        assert routes[0].action == DefaultPostActions.base_action
        assert routes[0].validator.schema == {'test': 'test'}
        assert routes[0].output_schema == None


@pytest.fixture
def model():
    models_types = [{
        'name': 'test',
        'id_names': ['id']
    }]
    return list(RedisModelsBuilder(models_types))[0]


class TestRedisModelMetaInsert(object):
    def test_without_objects(self, model):
        session = mock.MagicMock()
        assert model.insert(session, []) == []

    def test_with_objects_len_less_than_chunks(self, model):
        session = mock.MagicMock()
        expected_map = {
            str((1,)): msgpack.dumps({'id': 1})
        }

        assert model.insert(session, [{'id': 1}]) == [{'id': 1}]
        assert session.bind.hmset.call_args_list == [mock.call('test', expected_map)]

    def test_with_objects_len_greater_than_chunks(self, model):
        session = mock.MagicMock()
        expected_map1 = {
            str((1,)): msgpack.dumps({'id': 1})
        }
        expected_map2 = {
            str((2,)): msgpack.dumps({'id': 2})
        }

        model.CHUNKS = 1
        assert model.insert(session, [{'id': 1}, {'id': 2}]) == [{'id': 1}, {'id': 2}]
        assert session.bind.hmset.call_args_list == [
            mock.call('test', expected_map1),
            mock.call('test', expected_map2)]


class TestRedisModelMetaUpdate(object):
    def test_without_objects_and_without_ids(self, model):
        session = mock.MagicMock()
        session.bind.hkeys.return_value = []
        assert model.update(session, []) == []

    def test_hmset_with_objects_and_without_ids(self, model):
        session = mock.MagicMock()
        session.bind.hkeys.return_value = [str((1,))]
        expected_map = {
            str((1,)): msgpack.dumps({'id': 1})
        }

        assert model.update(session, [{'id': 1}]) == [{'id': 1}]
        assert session.bind.hmset.call_args_list == [mock.call('test', expected_map)]

    def test_hmset_with_objects_and_without_ids_and_with_invalid_keys(self, model):
        session = mock.MagicMock()
        session.bind.hkeys.return_value = ['test']

        assert model.update(session, [{'id': 1}]) == []
        assert session.bind.hmset.call_args_list == []

    def test_hmset_with_objects_and_without_ids_and_with_one_invalid_key(self, model):
        session = mock.MagicMock()
        session.bind.hkeys.return_value = ['test', str((1,)), 'test2']
        expected_map = {
            str((1,)): msgpack.dumps({'id': 1})
        }

        assert model.update(session, [{'id': 1}, {'id': 2}]) == [{'id': 1}]
        assert session.bind.hmset.call_args_list == [mock.call('test', expected_map)]

    def test_if_calls_insert_with_objects_and_without_ids_len_greater_than_chunks(self, model):
        session = mock.MagicMock()
        session.bind.hkeys.return_value = [str((2,)), str((1,))]
        model.CHUNKS = 1
        model.insert = mock.MagicMock()
        model.update(session, [{'id': 1}, {'id': 2}])

        assert model.insert.call_args_list == [mock.call(session, [{'id': 1}, {'id': 2}])]

    def test_without_objects_and_with_ids(self, model):
        session = mock.MagicMock()
        session.bind.hkeys.return_value = [str((2,)), str((1,))]
        assert model.update(session, [], {'id': 1}) == []
        assert not session.bind.hmset.called

    def test_with_objects_and_with_ids_different_than_objects(self, model):
        session = mock.MagicMock()
        session.bind.hkeys.return_value = [str((1,))]
        assert model.update(session, [{'id': 2}], {'id': 1}) == []
        assert not session.bind.hmset.called

    def test_hmset_with_objects_and_with_ids(self, model):
        session = mock.MagicMock()
        session.bind.hkeys.return_value = [str((1,))]
        expected_map = {
            str((1,)): msgpack.dumps({'id': 1})
        }

        assert model.update(session, {'id': 1}, {'id': 1}) == [{'id': 1}]
        assert session.bind.hmset.call_args_list == [mock.call('test', expected_map)]

    def test_hmset_with_objects_and_with_ids_and_with_invalid_keys(self, model):
        session = mock.MagicMock()
        session.bind.hkeys.return_value = ['test']

        assert model.update(session, [{'id': 1}], [{'id': 1}]) == []
        assert session.bind.hmset.call_args_list == []

    def test_hmset_with_objects_and_with_ids_and_with_one_invalid_key(self, model):
        session = mock.MagicMock()
        session.bind.hkeys.return_value = ['test', str((1,)), 'test2']
        expected_map = {
            str((1,)): msgpack.dumps({'id': 1})
        }

        assert model.update(session, [{'id': 1}, {'id': 2}], [{'id': 1}, {'id': 2}]) == [{'id': 1}]
        assert session.bind.hmset.call_args_list == [mock.call('test', expected_map)]

    def test_if_calls_insert_with_objects_and_with_ids_len_greater_than_chunks(self, model):
        session = mock.MagicMock()
        session.bind.hkeys.return_value = [str((2,)), str((1,))]
        model.CHUNKS = 1
        model.insert = mock.MagicMock()
        model.update(session, [{'id': 1}, {'id': 2}], [{'id': 1}, {'id': 2}])

        assert model.insert.call_args_list == [mock.call(session, [{'id': 1}, {'id': 2}])]


class TestRedisModelMetaDelete(object):
    pass


class TestRedisModelMetaGet(object):
    pass
