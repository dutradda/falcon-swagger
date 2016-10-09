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


from falconswagger.models.sqlalchemy_redis import SQLAlchemyRedisModelBuilder, SQLAlchemyModelMeta
from falconswagger.session import Session
from falconswagger.exceptions import ModelBaseError
from unittest import mock

import pytest
import sqlalchemy as sa


@pytest.fixture
def model_base():
    return SQLAlchemyRedisModelBuilder()


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
def model2_uselist(model_base, model1):
    model1_ = model1

    class model2(model_base):
        __tablename__ = 'model2'
        id = sa.Column(sa.Integer, primary_key=True)
        model1_id = sa.Column(sa.ForeignKey('model1.id'))
        model1 = sa.orm.relationship(model1_, uselist=True)

    return model2


@pytest.fixture
def model2_mtm(model_base):
    mtm_table = sa.Table(
        'mtm', model_base.metadata,
        sa.Column('model1_id', sa.Integer, sa.ForeignKey('model1.id')),
        sa.Column('model2_id', sa.Integer, sa.ForeignKey('model2.id'))
    )

    class model2(model_base):
        __tablename__ = 'model2'
        id = sa.Column(sa.Integer, primary_key=True)
        model1 = sa.orm.relationship('model1', secondary='mtm', uselist=True)

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
        assert model1.__relationships__ == dict()

    def test_builds_no_backrefs(self, model1):
        assert model1.__backrefs__ == set()

    def test_if_builds_relationships_correctly_with_one_model(self, model1, model2):
        assert model2.__relationships__ == {'model1': model2.model1}

    def test_if_builds_relationships_correctly_with_one_model_and_uselist(self, model1, model2_uselist):
        assert model2_uselist.__relationships__ == {'model1': model2_uselist.model1}

    def test_if_builds_relationships_correctly_with_one_model_and_mtm(self, model1, model2_mtm):
        assert model2_mtm.__relationships__ == {'model1': model2_mtm.model1}

    def test_if_builds_relationships_correctly_with_two_models(self, model1, model2, model3):
        assert model3.__relationships__ == {'model1': model3.model1, 'model2': model3.model2}

    def test_if_builds_relationships_correctly_with_one_model_set_with_string(
            self, model1, model2_string):
        assert model2_string.__relationships__ == {'model1': model2_string.model1}

    def test_if_builds_relationships_correctly_with_two_models_set_with_string(
            self, model1, model2, model3_string):
        assert model3_string.__relationships__ == {
            'model1': model3_string.model1, 'model2': model3_string.model2}

    def test_if_builds_backrefs_correctly_with_one_model(self, model2, model3):
        assert model2.__backrefs__ == {model3.model2}

    def test_if_builds_backrefs_correctly_with_two_models(self, model1, model2, model3):
        assert model1.__backrefs__ == {model2.model1, model3.model1}

    def test_if_builds_primaries_keys_correctly(self, model_base):
        class model(model_base):
                __tablename__ = 'test'
                id3 = sa.Column(sa.Integer, primary_key=True)
                id1 = sa.Column(sa.Integer, primary_key=True)
                id2 = sa.Column(sa.Integer, primary_key=True)

        assert model.primaries_keys == {'id1': model.id1, 'id2': model.id2, 'id3': model.id3}

    def test_raises_model_error_with_invalid_base_class(self):
        class model(object):
            __baseclass_name__ = 'Test'
            id = sa.Column(sa.Integer, primary_key=True)

        with pytest.raises(ModelBaseError) as error:
            sa.ext.declarative.declarative_base(
                name='Invalid',
                metaclass=SQLAlchemyModelMeta, cls=model)

        assert error.value.args == (
            "'Invalid' class must inherit from 'Test'",)


class TestModelBaseTodict(object):

    def test_todict_without_schema(self, model1, model2):
        assert model1(mock.MagicMock(), id=1).todict() == {'id': 1}

    def test_todict_with_schema(self, model1, model2):
        schema = {'id': True}
        assert model1(mock.MagicMock(), id=1).todict(schema) == {'id': 1}

    def test_todict_with_schema_remove_id(self, model1, model2):
        schema = {'id': False}
        assert model1(mock.MagicMock(), id=1).todict(schema) == {}

    def test_todict_with_relationship_and_without_schema(self, model1, model2):
        m2 = model2(mock.MagicMock(), id=1, model1={'id': 1, '_operation': 'insert'})
        assert m2.todict() == {
            'id': 1,
            'model1_id': None,
            'model1': {
                'id': 1
            }
        }

    def test_todict_with_relationship_and_this_relationship_not_in_schema(self, model1, model2):
        m2 = model2(mock.MagicMock(), id=1, model1={'id': 1, '_operation': 'insert'})
        schema = {'model1': False}
        assert m2.todict(schema) == {
            'id': 1,
            'model1_id': None
        }

    def test_todict_with_relationship_and_a_relationship_attr_not_in_schema(self, model1, model2):
        m2 = model2(mock.MagicMock(), id=1, model1={'id': 1, '_operation': 'insert'})
        schema = {'model1': {'id': False}}
        assert m2.todict(schema) == {
            'id': 1,
            'model1_id': None,
            'model1': {}
        }

    def test_todict_with_nested_relationship_without_schema(self, model1, model2, model3):
        m2 = {'id': 1, 'model1': {'id': 1, '_operation': 'insert'}, '_operation': 'insert'}
        m3 = model3(mock.MagicMock(), id=1, model2=m2)
        assert m3.todict() == {
            'id': 1,
            'model1_id': None,
            'model2_id': None,
            'model1': None,
            'model2': {
                'id': 1,
                'model1_id': None,
                'model1': {'id': 1}
            }
        }

    def test_todict_with_nested_relationship_with_schema(self, model1, model2, model3):
        m2 = {'id': 1, 'model1': {'id': 1, '_operation': 'insert'}, '_operation': 'insert'}
        m3 = model3(mock.MagicMock(), id=1, model2=m2)
        schema = {
            'model2': {
                'model1': {
                    'id': False
                }
            }
        }
        assert m3.todict(schema) == {
            'id': 1,
            'model1_id': None,
            'model2_id': None,
            'model1': None,
            'model2': {
                'id': 1,
                'model1_id': None,
                'model1': {}
            }
        }


class TestModelBaseNestedOperations(object):

    def test_raises_model_error_with_invalid_nested_id(self, model1, model2_mtm):
        session = mock.MagicMock()
        session.query().filter().all().__getitem__.return_value = model1(mock.MagicMock(), id=1)
        with pytest.raises(ModelBaseError) as exc_info:
            model2_mtm.insert(session, {
                              'model1': [{'id': 1, '_operation': 'remove'}]})
        assert exc_info.value.args == \
            ("can't remove model 'model1' on column(s) 'id' with value(s) 1",)
