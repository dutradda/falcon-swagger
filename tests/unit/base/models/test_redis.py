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


from falconswagger.models.redis import RedisModelMeta, RedisModelBuilder
from falconswagger.exceptions import ModelBaseError
from unittest import mock
import pytest
import msgpack


class TestRedisModelBuilder(object):

    def test_build(self):
        model = RedisModelBuilder('test', ['id'], {})
        assert model.__name__ == 'TestModel'
        assert model.__key__ == 'test'
        assert model.__schema__ == {}


@pytest.fixture
def model():
    return RedisModelBuilder('test', ['id'], {})


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


class TestRedisModelMetaUpdateWithoutIDs(object):

    def test_without_objects_and_without_ids(self, model):
        session = mock.MagicMock()
        session.bind.hkeys.return_value = []
        assert model.update(session, []) == []

    def test_hmset_with_objects_and_without_ids(self, model):
        session = mock.MagicMock()
        session.bind.hkeys.return_value = [str((1,)).encode()]
        expected_map = {
            str((1,)).encode(): msgpack.dumps({'id': 1})
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
        session.bind.hkeys.return_value = ['test', str((1,)).encode(), 'test2']
        expected_map = {
            str((1,)).encode(): msgpack.dumps({'id': 1})
        }

        assert model.update(session, [{'id': 1}, {'id': 2}]) == [{'id': 1}]
        assert session.bind.hmset.call_args_list == [mock.call('test', expected_map)]

    def test_hmset_with_objects_and_without_ids_with_set_map_len_greater_than_chunks(self, model):
        session = mock.MagicMock()
        session.bind.hkeys.return_value = [str((2,)).encode(), str((1,)).encode()]
        model.CHUNKS = 1
        expected_map1 = {
            str((1,)).encode(): msgpack.dumps({'id': 1})
        }
        expected_map2 = {
            str((2,)).encode(): msgpack.dumps({'id': 2})
        }

        assert model.update(session, [{'id': 1}, {'id': 2}]) == [{'id': 1}, {'id': 2}]
        assert (session.bind.hmset.call_args_list == [
            mock.call('test', expected_map1),
            mock.call('test', expected_map2)
        ] or session.bind.hmset.call_args_list == [
            mock.call('test', expected_map2),
            mock.call('test', expected_map1)
        ])


class TestRedisModelMetaUpdateWithIDs(object):

    def test_without_objects_and_with_ids(self, model):
        session = mock.MagicMock()
        session.bind.hkeys.return_value = [str((2,)), str((1,))]
        assert model.update(session, [], {'id': 1}) == []
        assert not session.bind.hmset.called

    def test_with_objects_and_with_ids_and_with_one_id_different_than_objects(self, model):
        session = mock.MagicMock()
        session.bind.hkeys.return_value = [str((1,)).encode()]
        expected_map = {
            str((1,)).encode(): msgpack.dumps({'id': 1})
        }
        assert model.update(session, [{'id': 1}], [{'id': 1}, {'id': 2}]) == [{'id': 1}]
        assert session.bind.hmset.call_args_list == [mock.call('test', expected_map)]

    def test_with_objects_and_with_ids_and_with_one_obj_different_than_ids(self, model):
        session = mock.MagicMock()
        session.bind.hkeys.return_value = [str((1,)).encode()]
        expected_map = {
            str((1,)).encode(): msgpack.dumps({'id': 1})
        }
        assert model.update(session, [{'id': 1}, {'id': 2}], [{'id': 1}]) == [{'id': 1}]
        assert session.bind.hmset.call_args_list == [mock.call('test', expected_map)]

    def test_with_objects_and_with_ids_and_with_ids_different_than_objects(self, model):
        session = mock.MagicMock()
        session.bind.hkeys.return_value = [str((1,)).encode()]
        assert model.update(session, [{'id': 2}], {'id': 1}) == []
        assert not session.bind.hmset.called

    def test_with_objects_and_with_ids_and_with_objs_different_than_ids(self, model):
        session = mock.MagicMock()
        session.bind.hkeys.return_value = [str((2,)).encode()]
        assert model.update(session, [{'id': 2}], {'id': 1}) == []
        assert not session.bind.hmset.called

    def test_hmset_with_objects_and_with_ids(self, model):
        session = mock.MagicMock()
        session.bind.hkeys.return_value = [str((1,)).encode()]
        expected_map = {
            str((1,)).encode(): msgpack.dumps({'id': 1})
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
        session.bind.hkeys.return_value = ['test', str((1,)).encode(), 'test2']
        expected_map = {
            str((1,)).encode(): msgpack.dumps({'id': 1})
        }

        assert model.update(session, [{'id': 1}, {'id': 2}], [{'id': 1}, {'id': 2}]) == [{'id': 1}]
        assert session.bind.hmset.call_args_list == [mock.call('test', expected_map)]

    def test_hmset_with_objects_and_with_ids_len_greater_than_chunks(self, model):
        session = mock.MagicMock()
        session.bind.hkeys.return_value = [str((2,)).encode(), str((1,)).encode()]
        model.CHUNKS = 1
        expected_map1 = {
            str((1,)).encode(): msgpack.dumps({'id': 1})
        }
        expected_map2 = {
            str((2,)).encode(): msgpack.dumps({'id': 2})
        }

        assert model.update(session, [{'id': 1}, {'id': 2}], [{'id': 1}, {'id': 2}]) == [
            {'id': 1}, {'id': 2}
        ]
        assert (session.bind.hmset.call_args_list == [
            mock.call('test', expected_map1),
            mock.call('test', expected_map2)
        ] or session.bind.hmset.call_args_list == [
            mock.call('test', expected_map2),
            mock.call('test', expected_map1)
        ])


class TestRedisModelMetaDelete(object):

    def test_without_ids(self, model):
        session = mock.MagicMock()
        model.delete(session, [])
        assert not session.bind.hdel.called

    def test_delete(self, model):
        session = mock.MagicMock()
        model.delete(session, {'id': 1})
        assert session.bind.hdel.call_args_list == [mock.call('test', '(1,)')]


class TestRedisModelMetaGetAll(object):

    def test_get_all(self, model):
        session = mock.MagicMock()
        session.bind.hmget.return_value = [msgpack.dumps({'id': 1})]
        assert model.get(session) == []

    def test_get_all_with_limit(self, model):
        session = mock.MagicMock()
        session.bind.hkeys.return_value = [1, 2]
        model.get(session, limit=1)

        assert session.bind.hmget.call_args_list == [mock.call('test', 1)]

    def test_get_all_with_limit_and_offset(self, model):
        session = mock.MagicMock()
        session.bind.hkeys.return_value = [1, 2, 3]
        model.get(session, limit=2, offset=1)

        assert session.bind.hmget.call_args_list == [mock.call('test', 2, 3)]

    def test_get_all_with_offset(self, model):
        session = mock.MagicMock()
        session.bind.hkeys.return_value = [1, 2, 3]
        model.get(session, offset=2)

        assert session.bind.hmget.call_args_list == [mock.call('test', 3)]


class TestRedisModelMetaGetMany(object):

    def test_get_many(self, model):
        session = mock.MagicMock()
        model.get(session, {'id': 1})
        assert session.bind.hmget.call_args_list == [mock.call('test', '(1,)')]

    def test_get_many_with_limit(self, model):
        session = mock.MagicMock()
        model.get(session, [{'id': 1}, {'id': 2}], limit=1)
        assert session.bind.hmget.call_args_list == [mock.call('test', '(1,)')]

    def test_get_many_with_limit_and_offset(self, model):
        session = mock.MagicMock()
        model.get(session, [{'id': 1}, {'id': 2}, {'id': 3}], limit=2, offset=1)
        assert session.bind.hmget.call_args_list == [mock.call('test', '(2,)', '(3,)')]

    def test_get_many_with_offset(self, model):
        session = mock.MagicMock()
        model.get(session, [{'id': 1}, {'id': 2}, {'id': 3}], offset=2)
        assert session.bind.hmget.call_args_list == [mock.call('test', '(3,)')]
