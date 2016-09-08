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


from sqlalchemy.ext.declarative import declarative_base
from unittest import mock

from myreco.base.session import Session
from myreco.base.model import model_base_builder
from myreco.exceptions import QueryError

import pytest
import sqlalchemy as sa


@pytest.fixture
def model_base():
    return model_base_builder()


@pytest.fixture
def engine():
    return sa.create_engine('sqlite://')


@pytest.fixture
def redis():
    return mock.MagicMock()


@pytest.fixture
def session(engine, redis):
    return Session(bind=engine, redis_bind=redis)


@pytest.fixture
def model1(engine, request, model_base):
    model_base.metadata.bind = engine

    class model_(model_base):
        __tablename__ = 'test1'
        id = sa.Column(sa.Integer, primary_key=True)

    model_base.metadata.create_all()
    return model_


@pytest.fixture
def model2(engine, request, model_base):
    model_base.metadata.bind = engine

    class model_(model_base):
        __tablename__ = 'test2'
        id = sa.Column(sa.Integer, primary_key=True)

    model_base.metadata.create_all()
    return model_


class TestSessionCommitRedisSet(object):
    def test_if_instance_is_seted_on_redis(self, session, model1, redis):
        session.add(model1(id=1))
        session.commit()

        assert redis.hmset.call_args_list == [mock.call('test1', {'1': {'id': 1}})]

    def test_if_two_instance_are_seted_on_redis(self, session, model1, redis):
        session.add(model1(id=1))
        session.add(model1(id=2))
        session.commit()

        assert redis.hmset.call_args_list == [
            mock.call('test1', {'1': {'id': 1}, '2': {'id': 2}})]

    def test_if_two_commits_sets_redis_correctly(self, session, model1, redis):
        session.add(model1(id=1))
        session.commit()
        session.add(model1(id=2))
        session.commit()

        assert redis.hmset.call_args_list == [
            mock.call('test1', {'1': {'id': 1}}),
            mock.call('test1', {'2': {'id': 2}})]

    def test_if_error_right_raised(self, session, model1, redis):
        class ExceptionTest(Exception):
            pass

        session.add(model1(id=1))
        redis.hmset.side_effect = ExceptionTest
        with pytest.raises(ExceptionTest):
            session.commit()

    def test_if_istances_are_seted_on_redis_with_two_models_correctly(
            self, session, model1, model2, redis):
        session.add(model1(id=1))
        session.add(model2(id=1))
        session.add(model1(id=2))
        session.add(model2(id=2))
        session.commit()

        expected = [
            mock.call('test1', {'1': {'id': 1}, '2': {'id': 2}}),
            mock.call('test2', {'1': {'id': 1}, '2': {'id': 2}})
        ]

        assert len(expected) == len(redis.hmset.call_args_list)

        for call_ in redis.hmset.call_args_list:
            assert call_ in expected

    def test_if_two_commits_sets_redis_with_two_models_correctly(
            self, session, model1, model2, redis):
        session.add(model1(id=1))
        session.add(model2(id=1))
        session.commit()
        session.add(model1(id=2))
        session.add(model2(id=2))
        session.commit()

        expected = [
            mock.call('test1', {'1': {'id': 1}}),
            mock.call('test2', {'1': {'id': 1}}),
            mock.call('test1', {'2': {'id': 2}}),
            mock.call('test2', {'2': {'id': 2}})
        ]

        assert len(expected) == len(redis.hmset.call_args_list)

        for call_ in redis.hmset.call_args_list:
            assert call_ in expected


class TestSessionCommitRedisDelete(object):
    def test_if_instance_is_deleted_from_redis(self, session, model1, redis):
        inst1 = model1(id=1)
        session.add(inst1)
        session.commit()

        session.delete(inst1)
        session.commit()

        assert redis.hdel.call_args_list == [mock.call('test1', '1')]

    def test_if_two_instance_are_deleted_from_redis(self, session, model1, redis):
        inst1 = model1(id=1)
        inst2 = model1(id=2)
        session.add_all([inst1, inst2])
        session.commit()

        session.delete(inst1)
        session.delete(inst2)
        session.commit()

        assert (redis.hdel.call_args_list == [mock.call('test1', '1', '2')] or
            redis.hdel.call_args_list == [mock.call('test1', '2', '1')])

    def test_if_two_commits_delete_redis_correctly(self, session, model1, redis):
        inst1 = model1(id=1)
        inst2 = model1(id=2)
        session.add_all([inst1, inst2])
        session.commit()

        session.delete(inst1)
        session.commit()
        session.delete(inst2)
        session.commit()

        assert redis.hdel.call_args_list == [
            mock.call('test1', '1'),
            mock.call('test1', '2')
        ]

    def test_if_error_right_raised(self, session, model1, redis):
        class ExceptionTest(Exception):
            pass

        inst1 = model1(id=1)
        session.add(inst1)
        session.commit()
        session.delete(inst1)
        redis.hdel.side_effect = ExceptionTest
        with pytest.raises(ExceptionTest):
            session.commit()

    def test_if_istances_are_seted_on_redis_with_two_models_correctly(
            self, session, model1, model2, redis):
        inst1 = model1(id=1)
        inst2 = model1(id=2)
        inst3 = model2(id=1)
        inst4 = model2(id=2)
        session.add_all([inst1, inst2, inst3, inst4])
        session.commit()

        session.delete(inst1)
        session.delete(inst2)
        session.delete(inst3)
        session.delete(inst4)
        session.commit()

        assert len(redis.hmset.call_args_list) == 2

        for call in redis.hdel.call_args_list:
            assert len(call[0]) == 3
            assert call[1] == {}
            assert call[0][0] == 'test1' or call[0][0] == 'test2'
            assert call[0][1] == '1' or call[0][1] == '2'
            assert call[0][2] == '1' or call[0][2] == '2'

    def test_if_two_commits_delete_redis_with_two_models_correctly(
            self, session, model1, model2, redis):
        inst1 = model1(id=1)
        inst2 = model1(id=2)
        inst3 = model2(id=1)
        inst4 = model2(id=2)
        session.add_all([inst1, inst2, inst3, inst4])
        session.commit()

        session.delete(inst1)
        session.delete(inst3)
        session.commit()
        session.delete(inst2)
        session.delete(inst4)
        session.commit()

        assert len(redis.hdel.call_args_list) == 4

        for call in redis.hdel.call_args_list:
            assert len(call[0]) == 2
            assert call[1] == {}
            assert call[0][0] == 'test1' or call[0][0] == 'test2'
            assert call[0][1] == '1' or call[0][1] == '2'


class TestSessionQueryGet(object):
    def test_query_get_more_than_one_model_error(self, session, redis, model1):
        with pytest.raises(QueryError):
            session.query(model1, model1).get(1)

    def test_if_query_get_calls_hmget_correctly(self, session, redis, model1):
        session.query(model1).get(1)
        assert redis.hmget.call_args_list == [mock.call('test1', ['1'])]

    def test_if_query_get_calls_hmget_correctly_with_two_ids(self, session, redis, model1):
        session.query(model1).get([1, 2])
        assert redis.hmget.call_args_list == [mock.call('test1', ['1', '2'])]

    def test_if_query_get_builds_redis_left_ids_correctly_with_result_found_on_redis_with_one_id(
            self, session, redis, model1):
        session.add(model1(id=1))
        session.commit()
        redis.hmget.return_value = [None]
        assert session.query(model1).get(1) == [{'id': 1}]

    def test_if_query_get_builds_redis_left_ids_correctly_with_no_result_found_on_redis_with_two_ids(
            self, session, redis, model1):
        session.add_all([model1(id=1), model1(id=2)])
        session.commit()
        redis.hmget.return_value = [None, None]
        assert session.query(model1).get([1, 2]) == [{'id': 1}, {'id': 2}]

    def test_if_query_get_builds_redis_left_ids_correctly_with_no_result_found_on_redis_with_three_ids(
            self, session, redis, model1):
        session.add_all([model1(id=1), model1(id=2), model1(id=3)])
        session.commit()
        redis.hmget.return_value = [None, None, None]
        assert session.query(model1).get([1, 2, 3]) == [{'id': 1}, {'id': 2}, {'id': 3}]

    def test_if_query_get_builds_redis_left_ids_correctly_with_no_result_found_on_redis_with_four_ids(
            self, session, redis, model1):
        session.add_all([model1(id=1), model1(id=2), model1(id=3), model1(id=4)])
        session.commit()
        redis.hmget.return_value = [None, None, None, None]
        assert session.query(model1).get([1, 2, 3, 4]) == [{'id': 1}, {'id': 2}, {'id': 3}, {'id': 4}]
        
    def test_if_query_get_builds_redis_left_ids_correctly_with_one_not_found_on_redis(
            self, session, redis, model1):
        session.add(model1(id=1))
        session.commit()
        redis.hmget.return_value = [None, '{"id": 2}']
        assert session.query(model1).get([1, 2]) == [{'id': 2}, {'id': 1}]
