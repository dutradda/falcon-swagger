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


from myreco.base.models.sqlalchemy_redis import SQLAlchemyRedisModelBuilder
from myreco.base.session import Session
from myreco.exceptions import ModelBaseError
from unittest import mock

import pytest
import msgpack
import sqlalchemy as sa


@pytest.fixture
def model1(model_base):
    class model1(model_base):
        __tablename__ = 'model1'
        __table_args__ = {'mysql_engine':'innodb'}
        id = sa.Column(sa.Integer, primary_key=True)

    return model1


@pytest.fixture
def model1_two_ids(model_base):
    class model1(model_base):
        __tablename__ = 'model1'
        __table_args__ = {'mysql_engine':'innodb'}
        id = sa.Column(sa.Integer, primary_key=True, autoincrement=True)
        id2 = sa.Column(sa.Integer, primary_key=True)

    return model1


@pytest.fixture
def model1_three_ids(model_base):
    class model1(model_base):
        __tablename__ = 'model1'
        __table_args__ = {'mysql_engine':'innodb'}
        id = sa.Column(sa.Integer, primary_key=True, autoincrement=True)
        id2 = sa.Column(sa.Integer, primary_key=True)
        id3 = sa.Column(sa.Integer, primary_key=True)

    return model1


@pytest.fixture
def model1_nested(model_base):
    class model1(model_base):
        __tablename__ = 'model1'
        id = sa.Column(sa.Integer, primary_key=True)
        test = sa.Column(sa.String(100))

    return model1


@pytest.fixture
def model2(model_base):
    class model2(model_base):
        __tablename__ = 'model2'
        __table_args__ = {'mysql_engine':'innodb'}
        id = sa.Column(sa.Integer, primary_key=True)
        model1_id = sa.Column(sa.ForeignKey('model1.id'))
        model1 = sa.orm.relationship('model1')

    return model2


@pytest.fixture
def model3(model_base):
    class model3(model_base):
        __tablename__ = 'model3'
        __table_args__ = {'mysql_engine':'innodb'}
        id = sa.Column(sa.Integer, primary_key=True)
        model1_id = sa.Column(sa.ForeignKey('model1.id', ondelete='CASCADE'))
        model2_id = sa.Column(sa.ForeignKey('model2.id', ondelete='CASCADE'))
        model1 = sa.orm.relationship('model1')
        model2 = sa.orm.relationship('model2')

    return model3


@pytest.fixture
def model2_mtm(model_base):
    mtm_table = sa.Table(
        'mtm', model_base.metadata,
        sa.Column('model1_id', sa.Integer, sa.ForeignKey('model1.id', ondelete='CASCADE')),
        sa.Column('model2_id', sa.Integer, sa.ForeignKey('model2.id', ondelete='CASCADE')),
        mysql_engine='innodb'
    )

    class model2(model_base):
        __tablename__ = 'model2'
        __table_args__ = {'mysql_engine':'innodb'}
        id = sa.Column(sa.Integer, primary_key=True)
        model1 = sa.orm.relationship(
            'model1', secondary='mtm', uselist=True)

    return model2


@pytest.fixture
def model3_mtm(model_base, model1, model2_mtm):
    model1_ = model1

    class model3(model_base):
        __tablename__ = 'model3'
        __table_args__ = {'mysql_engine':'innodb'}
        id = sa.Column(sa.Integer, primary_key=True)
        model1_id = sa.Column(sa.ForeignKey('model1.id', ondelete='CASCADE'))
        model2_id = sa.Column(sa.ForeignKey('model2.id', ondelete='CASCADE'))
        model1 = sa.orm.relationship(model1_)
        model2 = sa.orm.relationship(model2_mtm)

    return model3


@pytest.fixture
def model2_primary_join(model_base, model1):
    model1_ = model1

    class model2(model_base):
        __tablename__ = 'model2'
        __table_args__ = {'mysql_engine':'innodb'}
        id = sa.Column(sa.Integer, primary_key=True)
        id2 = sa.Column(sa.Integer)
        model1_id = sa.Column(sa.ForeignKey('model1.id', ondelete='CASCADE'))
        model1 = sa.orm.relationship(
            model1_,
            primaryjoin='and_(model2.model1_id==model1.id, model2.id2==model1.id)')

    return model2


@pytest.fixture
def model1_mto(model_base):
    class model1(model_base):
        __tablename__ = 'model1'
        __table_args__ = {'mysql_engine':'innodb'}
        id = sa.Column(sa.Integer, primary_key=True)

        model2 = sa.orm.relationship('model2', uselist=True)

    return model1


@pytest.fixture
def model2_mto(model_base):
    class model2(model_base):
        __tablename__ = 'model2'
        __table_args__ = {'mysql_engine':'innodb'}
        id = sa.Column(sa.Integer, primary_key=True)
        model1_id = sa.Column(sa.ForeignKey('model1.id', ondelete='CASCADE'))

    return model2


@pytest.fixture
def model2_mto_nested(model_base):
    class model2(model_base):
        __tablename__ = 'model2'
        __table_args__ = {'mysql_engine':'innodb'}
        id = sa.Column(sa.Integer, primary_key=True)
        model1_id = sa.Column(sa.ForeignKey('model1.id', ondelete='CASCADE'))
        test = sa.Column(sa.String(100))

    return model2


class TestModelBaseTodict(object):
    def test_todict_after_get_from_database(self, model1, model2, session):
        session.add(model2(session, id=1, model1=model1(session, id=1)))
        session.commit()
        expected = {
            'id': 1,
            'model1_id': 1,
            'model1': {'id': 1}
        }
        session.query(model2).filter_by(id=1).one().todict() == expected

    def test_todict_after_get_from_database_with_mtm(self, model1, model2_mtm, session):
        session.add(model2_mtm(session, id=1, model1=[model1(session, id=1)]))
        session.commit()
        expected = {
            'id': 1,
            'model1': [{'id': 1}]
        }
        session.query(model2_mtm).filter_by(id=1).one().todict() == expected

    def test_todict_after_get_from_database_with_mtm_with_two_relations(
            self, model1, model2_mtm, session):
        session.add(model2_mtm(session, id=1, model1=[model1(session, id=1), model1(session, id=2)]))
        session.commit()
        expected = {
            'id': 1,
            'model1': [{'id': 1}, {'id': 2}]
        }
        session.query(model2_mtm).filter_by(id=1).one().todict() == expected


class TestModelBaseGetRelated(object):
    def test_get_related_with_one_model(self, model1, model2, session):
        m11 = model1(session, id=1)
        m21 = model2(session, id=1)
        m21.model1 = m11
        session.add_all([m11, m21])
        session.commit()

        assert m11.get_related(session) == {m21}

    def test_get_related_with_two_models(self, model1, model2, model3, session):
        m11 = model1(session, id=1)
        m21 = model2(session, id=1)
        m31 = model3(session, id=1)
        m31.model1 = m11
        m31.model2 = m21
        session.add_all([m11, m21, m31])
        session.commit()

        assert m11.get_related(session) == {m31}
        assert m21.get_related(session) == {m31}

    def test_get_related_with_two_related(self, model1, model2, model3, session):
        m11 = model1(session, id=1)
        m21 = model2(session, id=1)
        m31 = model3(session, id=1)
        m31.model1 = m11
        m21.model1 = m11
        session.add_all([m11, m21, m31])
        session.commit()

        assert m11.get_related(session) == {m31, m21}

    def test_get_related_with_two_models_and_two_related(self, model1, model2, model3, session):
        m11 = model1(session, id=1)
        m21 = model2(session, id=1)
        m31 = model3(session, id=1)
        m31.model1 = m11
        m21.model1 = m11
        m22 = model2(session, id=2)
        m32 = model3(session, id=2)
        m32.model1 = m11
        m22.model1 = m11
        session.add_all([m11, m21, m31, m22, m32])
        session.commit()

        assert m11.get_related(session) == {m31, m21, m22, m32}

    def test_get_related_with_mtm(
            self, model1, model2_mtm, model3_mtm, session):
        m11 = model1(session, id=1)
        m12 = model1(session, id=2)
        m21 = model2_mtm(session, id=1)
        m31 = model3_mtm(session, id=1)
        m31.model1 = m11
        m21.model1 = [m11, m12]
        m22 = model2_mtm(session, id=2)
        m32 = model3_mtm(session, id=2)
        m32.model1 = m11
        m22.model1 = [m11, m12]
        session.add_all([m11, m12, m21, m31, m22, m32])
        session.commit()

        assert m11.get_related(session) == {m31, m21, m22, m32}
        assert m12.get_related(session) == {m21, m22}

    def test_get_related_with_primary_join(
            self, model1, model2_primary_join, session):
        m11 = model1(session, id=5)
        m21 = model2_primary_join(session, id=1, id2=5)
        m21.model1 = m11
        session.add_all([m11, m21])
        session.commit()

        assert m21.model1 == m11
        assert m11.get_related(session) == {m21}

    def test_get_related_with_primary_join_get_no_result(
            self, model1, model2_primary_join, session):
        m11 = model1(session, id=1)
        m21 = model2_primary_join(session, id=1, id2=5)
        m21.model1 = m11
        session.add_all([m11, m21])
        session.commit()

        assert m21.model1 == None
        assert m11.get_related(session) == set()
        assert m21.get_related(session) == set()

    def test_get_related_with_mto(
            self, model1_mto, model2_mto, session):
        m11 = model1_mto(session, id=1)
        m21 = model2_mto(session, id=1)
        m11.model2 = [m21]
        session.add_all([m11, m21])
        session.commit()

        assert m11.model2 == [m21]
        assert m21.get_related(session) == {m11}

    def test_get_related_with_mto_with_two_related(
            self, model1_mto, model2_mto, session):
        m11 = model1_mto(session, id=1)
        m21 = model2_mto(session, id=1)
        m22 = model2_mto(session, id=2)
        m11.model2 = [m21, m22]
        session.add(m11)
        session.commit()

        assert m11.model2 == [m21, m22]
        assert m21.get_related(session) == {m11}


class TestModelBaseInsert(object):
    def test_insert_with_one_object(self, model1, session):
        objs = model1.insert(session, {'id': 1})
        assert objs == [{'id': 1}]

    def test_insert_without_todict(self, model1, session):
        objs = model1.insert(session, {'id': 1}, todict=False)
        assert [o.todict() for o in objs] == [{'id': 1}]

    def test_insert_with_two_objects(self, model1, session):
        objs = model1.insert(session, [{'id': 1}, {'id': 2}])
        assert objs == [{'id': 1}, {'id': 2}] or objs == [{'id': 2}, {'id': 1}]

    def test_insert_with_two_nested_objects(self, model1, model2, session):
        objs = model2.insert(session, {'id': 1, 'model1': {'id': 1}})
        assert objs == [{'id': 1, 'model1_id': 1, 'model1': {'id': 1}}]

    def test_insert_with_three_nested_objects(self, model1, model2, model3, session):
        m1 = {'id': 1}
        m2 = {'id': 1, 'model1': m1}
        objs = model3.insert(session, {'id': 1, 'model2': m2})

        expected = {
            'id': 1,
            'model1_id': None,
            'model1': None,
            'model2_id': 1,
            'model2': {
                'id': 1,
                'model1_id': 1,
                'model1': {
                    'id': 1
                }
            }
        }
        assert objs == [expected]

    def test_insert_with_nested_update(self, model1, model2, model3, session):
        model1.insert(session, {'id': 1})
        model2.insert(session, {'id': 1})

        m3 = {
            'id': 1,
            'model2': {
                'id': 1,
                '_update': True,
                'model1_id': 1
            }
        }
        objs = model3.insert(session, m3)

        expected = {
            'id': 1,
            'model1_id': None,
            'model1': None,
            'model2_id': 1,
            'model2': {
                'id': 1,
                'model1_id': 1,
                'model1': {
                    'id': 1
                }
            }
        }
        assert objs == [expected]

    def test_insert_with_two_nested_update(self, model1_nested, model2, model3, session):
        model1_nested.insert(session, {'id': 1})
        model2.insert(session, {'id': 1})

        m3 = {
            'id': 1,
            'model2': {
                'id': 1,
                '_update': True,
                'model1': {
                    'id': 1,
                    '_update': True,
                    'test': 'test_updated'
                }
            }
        }
        objs = model3.insert(session, m3)

        expected = {
            'id': 1,
            'model1_id': None,
            'model1': None,
            'model2_id': 1,
            'model2': {
                'id': 1,
                'model1_id': 1,
                'model1': {
                    'id': 1,
                    'test': 'test_updated'
                }
            }
        }
        assert objs == [expected]

    def test_insert_with_two_nested_update_with_mtm(
            self, model1_nested, model2_mtm, model3, session):
        model1_nested.insert(session, [{'id': 1}, {'id': 2}])
        model2_mtm.insert(session, {'id': 1})

        m3 = {
            'id': 1,
            'model2': {
                'id': 1,
                '_update': True,
                'model1': [
                    {
                        'id': 1,
                        '_update': True,
                        'test': 'test_updated'
                    }, {
                        'id': 2,
                        '_update': True,
                        'test': 'test_updated2'
                    }
                ]
            }
        }
        objs = model3.insert(session, m3)

        expected = {
            'id': 1,
            'model1_id': None,
            'model1': None,
            'model2_id': 1,
            'model2': {
                'id': 1,
                'model1': [
                    {
                        'id': 1,
                        'test': 'test_updated'
                    },{
                        'id': 2,
                        'test': 'test_updated2'
                    }
                ]
            }
        }
        assert objs == [expected]

    def test_insert_with_two_nested_update_with_mto(
            self, model1_mto, model2_mto_nested, model3, session):
        model1_mto.insert(session, {'id': 1})
        model2_mto_nested.insert(session, [{'id': 1}, {'id': 2}])

        m3 = {
            'id': 1,
            'model1': {
                'id': 1,
                '_update': True,
                'model2': [
                    {
                        'id': 1,
                        '_update': True,
                        'test': 'test_updated'
                    }, {
                        'id': 2,
                        '_update': True,
                        'test': 'test_updated2'
                    }
                ]
            }
        }
        objs = model3.insert(session, m3)

        expected = {
            'id': 1,
            'model2_id': None,
            'model2': None,
            'model1_id': 1,
            'model1': {
                'id': 1,
                'model2': [
                    {
                        'id': 1,
                        'model1_id': 1,
                        'test': 'test_updated'
                    },{
                        'id': 2,
                        'model1_id': 1,
                        'test': 'test_updated2'
                    }
                ]
            }
        }
        assert objs == [expected]

    def test_insert_with_mtm_update_and_delete(self, model1, model2_mtm, model3, session):
        m1 = {'id': 1}
        m2 = {'id': 1, 'model1': [m1]}
        model2_mtm.insert(session, m2)
        m3_insert = {
            'id': 1,
            'model2': {
                'id': 1,
                '_update': True,
                'model1': [{
                    'id': 1,
                    '_delete': True
                }]
            }
        }
        objs = model3.insert(session, m3_insert)
        assert session.query(model1).all() == []

        expected = {
            'id': 1,
            'model1_id': None,
            'model1': None,
            'model2_id': 1,
            'model2': {
                'id': 1,
                'model1': []
            }
        }
        assert objs == [expected]

    def test_insert_with_mtm_update_and_remove(self, model1, model2_mtm, model3, session):
        m1 = {'id': 1}
        m2 = {'id': 1, 'model1': [m1]}
        model2_mtm.insert(session, m2)
        m3_insert = {
            'id': 1,
            'model2': {
                'id': 1,
                '_update': True,
                'model1': [{
                    'id': 1,
                    '_remove': True
                }]
            }
        }
        objs = model3.insert(session, m3_insert)
        assert session.query(model1).one().todict() == {'id': 1}

        expected = {
            'id': 1,
            'model1_id': None,
            'model1': None,
            'model2_id': 1,
            'model2': {
                'id': 1,
                'model1': []
            }
        }
        assert objs == [expected]

    def test_insert_with_mto_update_and_remove(
            self, model1_mto, model2_mto, model3, session):
        m2 = {'id': 1}
        m1 = {'id': 1, 'model2': [m2]}
        model1_mto.insert(session, m1)
        m3_insert = {
            'id': 1,
            'model1': {
                'id': 1,
                '_update': True,
                'model2': [{
                    'id': 1,
                    '_remove': True
                }]
            }
        }
        objs = model3.insert(session, m3_insert)
        assert session.query(model2_mto).one().todict() == {'id': 1, 'model1_id': None}

        expected = {
            'id': 1,
            'model1_id': 1,
            'model2_id': None,
            'model1': {
                'id': 1,
                'model2': []
            },
            'model2': None
        }
        assert objs == [expected]

    def test_insert_nested_update_without_relationships(
            self, model1, model2, session, redis):
        with pytest.raises(ModelBaseError):
            model2.insert(session, {'model1': {'id': 1, '_update': True}})

    def test_insert_nested_remove_without_relationships(
            self, model1, model2, session, redis):
        with pytest.raises(ModelBaseError):
            model2.insert(session, {'model1': {'id': 1, '_remove': True}})

    def test_insert_nested_delete_without_relationships(
            self, model1, model2, session, redis):
        with pytest.raises(ModelBaseError):
            model2.insert(session, {'model1': {'id': 1, '_delete': True}})


class TestModelBaseUpdate(object):
    def test_update_with_one_object(self, model1_nested, session):
        model1_nested.insert(session, {'id': 1})
        model1_nested.update(session, {'id': 1, 'test': 'test_updated'})
        assert session.query(model1_nested).one().todict() == {'id': 1, 'test': 'test_updated'}

    def test_update_with_two_objects(self, model1_nested, session):
        model1_nested.insert(session, [{'id': 1}, {'id': 2}])
        model1_nested.update(session, [
            {'id': 1, 'test': 'test_updated'},
            {'id': 2, 'test': 'test_updated2'}])
        assert [o.todict() for o in session.query(model1_nested).all()] == \
            [{'id': 1, 'test': 'test_updated'}, {'id': 2, 'test': 'test_updated2'}]

    def test_update_with_two_nested_objects(self, model1_nested, model2, session):
        model1_nested.insert(session, {'id': 1})
        model2.insert(session, {'id': 1})
        model2.update(session, {'id': 1, 'model1': {'id': 1, '_update': True, 'test': 'test_updated'}})

        assert session.query(model2).one().todict() == {
            'id': 1,
            'model1_id': 1,
            'model1': {
                'id': 1,
                'test': 'test_updated'
            }
        }

    def test_update_with_three_nested_objects(self, model1_nested, model2, model3, session):
        model1_nested.insert(session, {'id': 1})
        model2.insert(session, {'id': 1})
        model3.insert(session, {'id': 1})
        m3_update = {
            'id': 1,
            'model2': {
                'id': 1,
                '_update': True,
                'model1': {
                    'id': 1,
                    '_update': True,
                    'test': 'test_updated'
                }
            }
        }
        model3.update(session, m3_update)

        assert session.query(model3).one().todict() == {
            'id': 1,
            'model1_id': None,
            'model1': None,
            'model2_id': 1,
            'model2': {
                'id': 1,
                'model1_id': 1,
                'model1': {
                    'id': 1,
                    'test': 'test_updated'
                }
            }
        }

    def test_update_with_nested_insert(self, model1, model2, session):
        model2.insert(session, {'id': 1})

        m2_update = {
            'id': 1,
            'model1': {
                'id': 1
            }
        }
        model2.update(session, m2_update)

        expected = {
            'id': 1,
            'model1_id': 1,
            'model1': {
                'id': 1
            }
        }
        assert session.query(model2).one().todict() == expected

    def test_update_with_two_nested_insert(self, model1, model2, model3, session):
        model3.insert(session, {'id': 1})

        m3_update = {
            'id': 1,
            'model2': {
                'id': 1,
                'model1': {
                    'id': 1
                }
            }
        }
        model3.update(session, m3_update)

        expected = {
            'id': 1,
            'model1_id': None,
            'model1': None,
            'model2_id': 1,
            'model2': {
                'id': 1,
                'model1_id': 1,
                'model1': {
                    'id': 1
                }
            }
        }
        assert session.query(model3).one().todict() == expected

    def test_update_with_two_nested_insert_with_mtm(
            self, model1, model2_mtm, model3, session):
        model3.insert(session, {'id': 1})

        m3_update = {
            'id': 1,
            'model2': {
                'id': 1,
                'model1': [
                    {'id': 1},
                    {'id': 2}
                ]
            }
        }
        model3.update(session, m3_update)

        expected = {
            'id': 1,
            'model1_id': None,
            'model1': None,
            'model2_id': 1,
            'model2': {
                'id': 1,
                'model1': [
                    {'id': 1},
                    {'id': 2}
                ]
            }
        }
        assert session.query(model3).one().todict() == expected

    def test_update_with_two_nested_insert_with_mto(
            self, model1_mto, model2_mto, model3, session):
        model3.insert(session, {'id': 1})

        m3_update = {
            'id': 1,
            'model1': {
                'id': 1,
                'model2': [
                    {'id': 1},
                    {'id': 2}
                ]
            }
        }
        model3.update(session, m3_update)

        expected = {
            'id': 1,
            'model1_id': 1,
            'model1': {
                'id': 1,
                'model2': [
                    {'id': 1, 'model1_id': 1},
                    {'id': 2, 'model1_id': 1}
                ]
            },
            'model2_id': None,
            'model2': None
        }
        assert session.query(model3).one().todict() == expected

    def test_update_with_missing_id(self, model1, session):
        session.add(model1(session, id=1))
        session.commit()
        assert model1.update(session, [{'id': 1}, {'id': 2}]) == [{'id': 1}]

    def test_update_with_missing_all_ids(self, model1, session):
        assert model1.update(session, [{'id': 1}, {'id': 2}]) == []

    def test_update_with_nested_remove_without_uselist(self, model1, model2, session):
        model2.insert(session, {'model1': {}})
        model2.update(session, {'id': 1, 'model1': {'id': 1, '_remove': True}})
        assert session.query(model2).one().todict() == {'id': 1, 'model1_id': None, 'model1': None}

    def test_update_with_nested_remove_with_two_relationships(self, model1, model2_mtm, session):
        model2_mtm.insert(session, {'model1': [{}, {}]})
        model2_mtm.update(session, {'id': 1, 'model1': [{'id': 2, '_remove': True}]})
        assert session.query(model2_mtm).one().todict() == {'id': 1, 'model1': [{'id': 1}]}


class TestModelBaseGet(object):
    def test_if_query_get_calls_hmget_correctly(self, session, redis, model1):
        model1.get(session, {'id': 1})
        assert redis.hmget.call_args_list == [mock.call('model1', ['(1,)'])]

    def test_if_query_get_calls_hmget_correctly_with_two_ids(self, session, redis, model1):
        model1.get(session, [{'id': 1}, {'id': 2}])
        assert redis.hmget.call_args_list == [mock.call('model1', ['(1,)', '(2,)'])]

    def test_if_query_get_builds_redis_left_ids_correctly_with_result_found_on_redis_with_one_id(
            self, model1, session, redis):
        session.add(model1(session, id=1))
        session.commit()
        redis.hmget.return_value = [None]
        assert model1.get(session, {'id': 1}) == [{'id': 1}]

    def test_if_query_get_builds_redis_left_ids_correctly_with_no_result_found_on_redis_with_two_ids(
            self, model1, session, redis):
        session.add_all([model1(session, id=1), model1(session, id=2)])
        session.commit()
        redis.hmget.return_value = [None, None]
        assert model1.get(session, [{'id': 1}, {'id': 2}]) == [{'id': 1}, {'id': 2}]

    def test_if_query_get_builds_redis_left_ids_correctly_with_no_result_found_on_redis_with_three_ids(
            self, model1, session, redis):
        session.add_all([model1(session, id=1), model1(session, id=2), model1(session, id=3)])
        session.commit()
        redis.hmget.return_value = [None, None, None]
        assert model1.get(session, [{'id': 1}, {'id': 2}, {'id': 3}]) == \
            [{'id': 1}, {'id': 2}, {'id': 3}]

    def test_if_query_get_builds_redis_left_ids_correctly_with_no_result_found_on_redis_with_four_ids(
            self, model1, session, redis):
        session.add_all([model1(session, id=1), model1(session, id=2), model1(session, id=3), model1(session, id=4)])
        session.commit()
        redis.hmget.return_value = [None, None, None, None]
        assert model1.get(session, [{'id': 1}, {'id': 2}, {'id': 3}, {'id': 4}]) == \
            [{'id': 1}, {'id': 2}, {'id': 3}, {'id': 4}]

    def test_if_query_get_builds_redis_left_ids_correctly_with_one_not_found_on_redis(
            self, model1, session, redis):
        session.add(model1(session, id=1))
        session.commit()
        redis.hmget.return_value = [None, msgpack.dumps({'id': 2})]
        assert model1.get(session, [{'id': 1}, {'id': 2}]) == [{'id': 1}, {'id': 2}]

    def test_with_ids_and_limit(self, model1, session, redis):
        session.add_all([model1(session, id=1), model1(session, id=2), model1(session, id=3)])
        session.commit()
        model1.get(session, [{'id': 1}, {'id': 2}, {'id': 3}, {'id': 4}], limit=2)
        assert redis.hmget.call_args_list == [mock.call('model1', ['(1,)', '(2,)'])]

    def test_with_ids_and_offset(self, model1, session, redis):
        session.add_all([model1(session, id=1), model1(session, id=2), model1(session, id=3)])
        session.commit()
        model1.get(session, [{'id': 1}, {'id': 2}, {'id': 3}, {'id': 4}], offset=2)
        assert redis.hmget.call_args_list == [mock.call('model1', ['(3,)', '(4,)'])]

    def test_with_ids_and_limit_and_offset(self, model1, session, redis):
        session.add_all([model1(session, id=1), model1(session, id=2), model1(session, id=3)])
        session.commit()
        model1.get(session, [{'id': 1}, {'id': 2}, {'id': 3}, {'id': 4}], limit=2, offset=1)
        assert redis.hmget.call_args_list == [mock.call('model1', ['(2,)', '(3,)'])]

    def test_with_missing_id(self, model1, session, redis):
        session.add(model1(session, id=1))
        session.commit()
        redis.hmget.return_value = [None, None]
        assert model1.get(session, [{'id': 1}, {'id': 2}]) == [{'id': 1}]

    def test_with_missing_all_ids(self, model1, session, redis):
        redis.hmget.return_value = [None, None]
        assert model1.get(session, [{'id': 1}, {'id': 2}]) == []

    def test_without_ids(self, model1, session, redis):
        model1.insert(session, {})
        assert model1.get(session) == [{'id': 1}]

    def test_without_ids_and_with_limit(self, model1, session, redis):
        model1.insert(session, [{}, {}, {}])
        assert model1.get(session, limit=2) == [{'id': 1}, {'id': 2}]

    def test_without_ids_and_with_offset(self, model1, session, redis):
        model1.insert(session, [{}, {}, {}])
        assert model1.get(session, offset=1) == [{'id': 2}, {'id': 3}]

    def test_without_ids_and_with_limit_and_offset(self, model1, session, redis):
        model1.insert(session, [{}, {}, {}])
        assert model1.get(session, limit=1, offset=1) == [{'id': 2}]


class TestModelBaseDelete(object):
    def test_delete(self, model1, session, redis):
        model1.insert(session, {})
        assert model1.get(session) == [{'id': 1}]

        model1.delete(session, {'id': 1})
        assert model1.get(session) == []

    def test_delete_with_invalid_id(self, model1, session, redis):
        model1.insert(session, {})
        model1.delete(session , [{'id': 2}, {'id': 3}])
        assert model1.get(session) == [{'id': 1}]

    def test_delete_with_two_ids(self, model1_two_ids, session, redis):
        model1_two_ids.insert(session, {'id2': 2})
        assert model1_two_ids.get(session) == [{'id': 1, 'id2': 2}]

        model1_two_ids.delete(session , {'id': 1, 'id2': 2})
        assert model1_two_ids.get(session) == []

    def test_delete_with_three_ids(self, model1_three_ids, session, redis):
        model1_three_ids.insert(session, {'id2': 2, 'id3': 3})
        assert model1_three_ids.get(session) == [{'id': 1, 'id2': 2, 'id3': 3}]

        model1_three_ids.delete(session , {'id': 1, 'id2': 2, 'id3': 3})
        assert model1_three_ids.get(session) == []
