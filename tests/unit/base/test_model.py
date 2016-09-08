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


from myreco.base.model import model_base_builder
from myreco.base.session import Session
from unittest import mock

import pytest
import sqlalchemy as sa


@pytest.fixture
def model_base():
    return model_base_builder()


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
        model1 = sa.orm.relationship(model1_)

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
        model1 = sa.orm.relationship(model1_)
        model2 = sa.orm.relationship(model2_)

    return model3


@pytest.fixture
def model2_string(model_base):
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
        assert model1.relationships == set()

    def test_builds_no_backrefs(self, model1):
        assert model1.backrefs == set()

    def test_if_builds_relationships_correctly_with_one_model(self, model1, model2):
        assert model2.relationships == {model2.model1}

    def test_if_builds_relationships_correctly_with_two_models(self, model1, model2, model3):
        assert model3.relationships == {model3.model1, model3.model2}

    def test_if_builds_relationships_correctly_with_one_model_set_with_string(
            self, model1, model2_string):
        assert model2_string.relationships == {model2_string.model1}

    def test_if_builds_relationships_correctly_with_two_models_set_with_string(
            self, model1, model2, model3_string):
        assert model3_string.relationships == {model3_string.model1, model3_string.model2}

    def test_if_builds_backrefs_correctly_with_one_model(self, model2, model3):
        assert model2.backrefs == {model3.model2}

    def test_if_builds_backrefs_correctly_with_two_models(self, model1, model2, model3):
        assert model1.backrefs == {model2.model1, model3.model1}
