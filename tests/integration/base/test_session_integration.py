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

from falconswagger.models.orm.session import Session
from falconswagger.models.orm.sqlalchemy_redis import ModelSQLAlchemyRedisFactory

import msgpack
import pytest
import sqlalchemy as sa


@pytest.fixture
def redis():
    r = mock.MagicMock()
    r.smembers = lambda x: {x.replace('_filters_names', '').encode()}
    return r


@pytest.fixture
def model1(model_base):
    class model_(model_base):
        __tablename__ = 'test1'
        __table_args__ = {'mysql_engine':'innodb'}
        id = sa.Column(sa.Integer, primary_key=True)
    return model_


@pytest.fixture
def model2(model_base):
    class model_(model_base):
        __tablename__ = 'test2'
        __table_args__ = {'mysql_engine':'innodb'}
        id = sa.Column(sa.Integer, primary_key=True)
    return model_


@pytest.fixture
def model1_no_redis(model_base):
    class model_(model_base):
        __tablename__ = 'test1'
        __table_args__ = {'mysql_engine':'innodb'}
        __use_redis__ = False
        id = sa.Column(sa.Integer, primary_key=True)
    return model_


class TestSessionCommitWithoutRedis(object):
    def test_set_without_redis(self, model1, session, redis):
        session.redis_bind = None
        session.add(model1(session, id=1))
        session.commit()

        assert redis.hmset.call_args_list == []

    def test_delete_without_redis(self, model1, session, redis):
        session.redis_bind = None
        m1 = model1(session, id=1)
        session.add(m1)
        session.commit()
        session.delete(m1)
        session.commit()

        assert redis.hmdel.call_args_list == []


class TestSessionCommitRedisSet(object):
    def test_if_instance_is_seted_on_redis(self, model1, session, redis):
        session.add(model1(session, id=1))
        session.commit()

        assert redis.hmset.call_args_list == [mock.call('test1', {b'1': msgpack.dumps({'id': 1})})]

    def test_if_two_instance_are_seted_on_redis(self, model1, session, redis):
        session.add(model1(session, id=1))
        session.add(model1(session, id=2))
        session.commit()

        assert redis.hmset.call_args_list == [
            mock.call('test1', {b'1': msgpack.dumps({'id': 1}), b'2': msgpack.dumps({'id': 2})})]

    def test_if_two_commits_sets_redis_correctly(self, model1, session, redis):
        session.add(model1(session, id=1))
        session.commit()
        session.add(model1(session, id=2))
        session.commit()

        assert redis.hmset.call_args_list == [
            mock.call('test1', {b'1': msgpack.dumps({b'id': 1})}),
            mock.call('test1', {b'2': msgpack.dumps({b'id': 2})})]

    def test_if_error_right_raised(self, model1, session, redis):
        class ExceptionTest(Exception):
            pass

        session.add(model1(session, id=1))
        redis.hmset.side_effect = ExceptionTest
        with pytest.raises(ExceptionTest):
            session.commit()

    def test_if_istances_are_seted_on_redis_with_two_models_correctly(
            self, model1, model2, session, redis):
        session.add(model1(session, id=1))
        session.add(model2(session, id=1))
        session.add(model1(session, id=2))
        session.add(model2(session, id=2))
        session.commit()

        expected = [
            mock.call('test1', {b'1': msgpack.dumps({'id': 1}), b'2': msgpack.dumps({'id': 2})}),
            mock.call('test2', {b'1': msgpack.dumps({'id': 1}), b'2': msgpack.dumps({'id': 2})})
        ]

        assert len(expected) == len(redis.hmset.call_args_list)

        for call_ in redis.hmset.call_args_list:
            assert call_ in expected

    def test_if_two_commits_sets_redis_with_two_models_correctly(
            self, model1, model2, session, redis):
        session.add(model1(session, id=1))
        session.add(model2(session, id=1))
        session.commit()
        session.add(model1(session, id=2))
        session.add(model2(session, id=2))
        session.commit()

        expected = [
            mock.call('test1', {b'1': msgpack.dumps({'id': 1})}),
            mock.call('test2', {b'1': msgpack.dumps({'id': 1})}),
            mock.call('test1', {b'2': msgpack.dumps({'id': 2})}),
            mock.call('test2', {b'2': msgpack.dumps({'id': 2})})
        ]

        assert len(expected) == len(redis.hmset.call_args_list)

        for call_ in redis.hmset.call_args_list:
            assert call_ in expected


class TestSessionCommitRedisSetWithoutUseRedisFlag(object):
    def test_if_instance_is_seted_on_redis(self, model1_no_redis, session, redis):
        session.add(model1_no_redis(session, id=1))
        session.commit()

        assert redis.hmset.call_args_list == []


class TestSessionCommitRedisDelete(object):
    def test_if_instance_is_deleted_from_redis(self, model1, session, redis):
        inst1 = model1(session, id=1)
        session.add(inst1)
        session.commit()

        session.delete(inst1)
        session.commit()

        assert redis.hdel.call_args_list == [mock.call('test1', b'1')]

    def test_if_two_instance_are_deleted_from_redis(self, model1, session, redis):
        inst1 = model1(session, id=1)
        inst2 = model1(session, id=2)
        session.add_all([inst1, inst2])
        session.commit()

        session.delete(inst1)
        session.delete(inst2)
        session.commit()

        assert (redis.hdel.call_args_list == [mock.call('test1', b'1', b'2')] or
            redis.hdel.call_args_list == [mock.call('test1', b'2', b'1')])

    def test_if_two_commits_delete_redis_correctly(self, model1, session, redis):
        inst1 = model1(session, id=1)
        inst2 = model1(session, id=2)
        session.add_all([inst1, inst2])
        session.commit()

        session.delete(inst1)
        session.commit()
        session.delete(inst2)
        session.commit()

        assert redis.hdel.call_args_list == [
            mock.call('test1', b'1'),
            mock.call('test1', b'2')
        ]

    def test_if_error_right_raised(self, model1, session, redis):
        class ExceptionTest(Exception):
            pass

        inst1 = model1(session, id=1)
        session.add(inst1)
        session.commit()
        session.delete(inst1)
        redis.hdel.side_effect = ExceptionTest
        with pytest.raises(ExceptionTest):
            session.commit()

    def test_if_istances_are_seted_on_redis_with_two_models_correctly(
            self, model1, model2, session, redis):
        inst1 = model1(session, id=1)
        inst2 = model1(session, id=2)
        inst3 = model2(session, id=1)
        inst4 = model2(session, id=2)
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
            assert call[0][1] == b'1' or call[0][1] == b'2'
            assert call[0][2] == b'1' or call[0][2] == b'2'

    def test_if_two_commits_delete_redis_with_two_models_correctly(
            self, model1, model2, session, redis):
        inst1 = model1(session, id=1)
        inst2 = model1(session, id=2)
        inst3 = model2(session, id=1)
        inst4 = model2(session, id=2)
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
            assert call[0][1] == b'1' or call[0][1] == b'2'


class TestSessionCommitRedisDeleteWithoutUseRedisFlag(object):
    def test_if_instance_is_deleted_from_redis(self, model1_no_redis, session, redis):
        inst1 = model1_no_redis(session, id=1)
        session.add(inst1)
        session.commit()

        session.delete(inst1)
        session.commit()

        assert redis.hdel.call_args_list == []


@pytest.fixture
def model1_related(model_base):
    class test1(model_base):
        __tablename__ = 'test1'
        __table_args__ = {'mysql_engine':'innodb'}
        id = sa.Column(sa.Integer, primary_key=True)
        test = sa.Column(sa.String(255))
    return test1


@pytest.fixture
def model2_related(model_base, model1_related):
    mtm_table = sa.Table(
        'model1_model2', model_base.metadata,
        sa.Column('model1_id', sa.Integer, sa.ForeignKey('test1.id', ondelete='CASCADE')),
        sa.Column('model2_id', sa.Integer, sa.ForeignKey('test2.id', ondelete='CASCADE')),
        mysql_engine='innodb'
    )
    class test2(model_base):
        __tablename__ = 'test2'
        __table_args__ = {'mysql_engine':'innodb'}
        id = sa.Column(sa.Integer, primary_key=True)
        model1 = sa.orm.relationship(model1_related, uselist=True, secondary=mtm_table)
    return test2


@pytest.fixture
def model3_related(model_base, model2_related):
    class test3(model_base):
        __tablename__ = 'test3'
        __table_args__ = {'mysql_engine':'innodb'}
        id = sa.Column(sa.Integer, primary_key=True)
        model2_id = sa.Column(sa.ForeignKey('test2.id'))
        model2 = sa.orm.relationship(model2_related)
    return test3


@mock.patch('falconswagger.models.orm.session.msgpack', new=mock.MagicMock(dumps=lambda x: x))
class TestSessionCommitWithNestedRelatedModels(object):
    def test_redis_update_nested_related(self, model1_related, model2_related, model3_related, session, redis):
        m1 = model1_related(session)
        m2 = model2_related(session)
        m2.model1 = [m1]
        m3 = model3_related(session)
        m3.model2 = m2

        session.add_all([m1, m2, m3])
        session.commit()
        session.expunge_all()
        redis.hmset.reset_mock()

        m1.test = 'testando'
        session.add(m1)
        session.commit()

        m1_expected = {'id': 1, 'test': 'testando'}
        m2_expected = {
            'id': 1,
            'model1': [m1_expected]
        }
        m3_expected = {
            'id': 1,
            'model2_id': 1,
            'model2': m2_expected
        }
        call1 = mock.call('test1', {b'1': m1_expected})
        call2 = mock.call('test2', {b'1': m2_expected})
        call3 = mock.call('test3', {b'1': m3_expected})

        assert redis.hmset.call_args_list == [call1, call2, call3] or \
            redis.hmset.call_args_list == [call1, call3, call2] or \
            redis.hmset.call_args_list == [call2, call3, call1] or \
            redis.hmset.call_args_list == [call2, call1, call3] or \
            redis.hmset.call_args_list == [call3, call2, call1] or \
            redis.hmset.call_args_list == [call3, call1, call2]

    def test_redis_update_nested_related_deleted(self, model1_related, model2_related, model3_related, session, redis):
        m1 = model1_related(session)
        m2 = model2_related(session)
        m2.model1 = [m1]
        m3 = model3_related(session)
        m3.model2 = m2

        session.add_all([m1, m2, m3])
        session.commit()
        session.expunge_all()
        redis.hmset.reset_mock()

        session.delete(m1)
        session.commit()

        assert redis.hdel.call_args_list == [mock.call('test1', b'1')]

        m2_expected = {
            'id': 1,
            'model1': []
        }
        m3_expected = {
            'id': 1,
            'model2_id': 1,
            'model2': m2_expected
        }
        call2 = mock.call('test2', {b'1': m2_expected})
        call3 = mock.call('test3', {b'1': m3_expected})

        assert redis.hmset.call_args_list == [call2, call3] or \
            redis.hmset.call_args_list == [call3, call2]
