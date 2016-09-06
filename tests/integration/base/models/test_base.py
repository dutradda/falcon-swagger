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


from myreco.base.models.base import declarative_base
from myreco.base.session import Session
from unittest import mock

import pytest
import sqlalchemy as sa


@pytest.fixture
def model_base():
    return declarative_base()


@pytest.fixture
def model1(model_base):
    class model1(model_base):
        __tablename__ = 'model1'
        id = sa.Column(sa.Integer, primary_key=True)

    return model1


@pytest.fixture
def model2(model_base, model1):
    model1_ = model1

    class model2(model_base):
        __tablename__ = 'model2'
        id = sa.Column(sa.Integer, primary_key=True)
        model1_id = sa.Column(sa.ForeignKey('model1.id'))
        model1 = sa.orm.relationship(model1_, uselist=True)

    return model2


@pytest.fixture
def model3(model_base, model1, model2):
    model1_ = model1
    model2_ = model2

    class model3(model_base):
        __tablename__ = 'model3'
        id = sa.Column(sa.Integer, primary_key=True)
        model1_id = sa.Column(sa.ForeignKey('model1.id'))
        model2_id = sa.Column(sa.ForeignKey('model2.id'))
        model1 = sa.orm.relationship(model1_, uselist=True)
        model2 = sa.orm.relationship(model2_, uselist=True)

    return model3


@pytest.fixture
def model2_string(model_base, model1):
    model1_ = model1

    class model2(model_base):
        __tablename__ = 'model2'
        id = sa.Column(sa.Integer, primary_key=True)
        model1_id = sa.Column(sa.ForeignKey('model1.id'))
        model1 = sa.orm.relationship('model1')

    return model2


@pytest.fixture
def model3_string(model_base, model1, model2):
    class model3(model_base):
        __tablename__ = 'model3'
        id = sa.Column(sa.Integer, primary_key=True)
        model1_id = sa.Column(sa.ForeignKey('model1.id'))
        model2_id = sa.Column(sa.ForeignKey('model2.id'))
        model1 = sa.orm.relationship('model1')
        model2 = sa.orm.relationship('model2')

    return model3


class TestModelBaseInit(object):
    def test_builds_no_relationships(self, model1):
        assert model1.relationships == dict()

    def test_builds_no_backrefs(self, model1):
        assert model1.backrefs == set()

    def test_if_builds_relationships_correctly_with_one_model(self, model1, model2):
        assert model2.relationships == {'model1': model1}

    def test_if_builds_relationships_correctly_with_two_models(self, model1, model2, model3):
        assert model3.relationships == {'model1': model1, 'model2': model2}

    def test_if_builds_relationships_correctly_with_one_model_set_with_string(
            self, model1, model2_string):
        assert model2_string.relationships == {'model1': model1}

    def test_if_builds_relationships_correctly_with_two_models_set_with_string(
            self, model1, model2, model3_string):
        assert model3_string.relationships == {'model1': model1, 'model2': model2}

    def test_if_builds_backrefs_correctly_with_one_model(self, model2, model3):
        assert model2.backrefs == {model3}

    def test_if_builds_backrefs_correctly_with_two_models(self, model1, model2, model3):
        assert model1.backrefs == {model2, model3}


@pytest.fixture
def engine():
    return sa.create_engine('sqlite://')


@pytest.fixture
def redis():
    return mock.MagicMock()


@pytest.fixture
def session(engine, redis, model_base):
    model_base.metadata.bind = engine
    model_base.metadata.create_all()
    return Session(bind=engine, redis_bind=redis)


class TestModelBase(object):
    def test_get_related_with_one_model(self, model1, model2, session):
        m11 = model1(id=1)
        m21 = model2(id=1)
        m21.model1 = [m11]
        session.add_all([m11, m21])
        session.commit()

        assert m11.get_related(session) == {m21}

    def test_get_related_with_two_models(self, model1, model2, model3, session):
        m11 = model1(id=2)
        m21 = model2(id=2)
        m31 = model3(id=1)
        m31.model1 = [m11]
        m31.model2 = [m21]
        session.add_all([m11, m21, m31])
        session.commit()

        assert m11.get_related(session) == {m31}
        assert m21.get_related(session) == {m31}

    def test_get_related_with_two_related(self, model1, model2, model3, session):
        m11 = model1(id=3)
        m21 = model2(id=3)
        m31 = model3(id=2)
        m31.model1 = [m11]
        m21.model1 = [m11]
        session.add_all([m11, m21, m31])
        session.commit()

        assert m11.get_related(session) == {m31, m21}

    def test_get_related_without_uselist(self, model1, model2_string, session):
        m11 = model1(id=4)
        m21 = model2_string(id=1)
        m21.model1 = m11
        session.add_all([m11, m21])
        session.commit()

        assert m11.get_related(session) == {m21}
