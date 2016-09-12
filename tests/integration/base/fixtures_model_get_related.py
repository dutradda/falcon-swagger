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


import pytest
import sqlalchemy as sa


@pytest.fixture
def model1(model_base):
    mtm_table = sa.Table(
        'model1_model4', model_base.metadata,
        sa.Column('model1_id', sa.Integer, sa.ForeignKey('model1.id', ondelete='CASCADE')),
        sa.Column('model4_id', sa.Integer, sa.ForeignKey('model4.id', ondelete='CASCADE')),
        mysql_engine='innodb'
    )

    class model1(model_base):
        __tablename__ = 'model1'
        __table_args__ = {'mysql_engine':'innodb'}
        id = sa.Column(sa.Integer, primary_key=True)
        model2_id = sa.Column(sa.ForeignKey('model2.id'))

        model2 = sa.orm.relationship('model2') # one-to-many
        model3 = sa.orm.relationship('model3', uselist=True) # many-to-one
        model4 = sa.orm.relationship('model4', uselist=True, secondary='model1_model4') # many-to-many

    return model1


@pytest.fixture
def model2(model_base):
    mtm_table = sa.Table(
        'model2_model5', model_base.metadata,
        sa.Column('model2_id', sa.Integer, sa.ForeignKey('model2.id', ondelete='CASCADE')),
        sa.Column('model5_id', sa.Integer, sa.ForeignKey('model5.id', ondelete='CASCADE')),
        mysql_engine='innodb'
    )

    class model2(model_base):
        __tablename__ = 'model2'
        __table_args__ = {'mysql_engine':'innodb'}
        id = sa.Column(sa.Integer, primary_key=True)
        model3_id = sa.Column(sa.ForeignKey('model3.id'))

        model3 = sa.orm.relationship('model3') # one-to-many
        model4 = sa.orm.relationship('model4', uselist=True) # many-to-one
        model5 = sa.orm.relationship('model5', uselist=True, secondary='model2_model5') # many-to-many

    return model2


@pytest.fixture
def model3(model_base):
    mtm_table = sa.Table(
        'model3_model6', model_base.metadata,
        sa.Column('model3_id', sa.Integer, sa.ForeignKey('model3.id', ondelete='CASCADE')),
        sa.Column('model6_id', sa.Integer, sa.ForeignKey('model6.id', ondelete='CASCADE')),
        mysql_engine='innodb'
    )

    class model3(model_base):
        __tablename__ = 'model3'
        __table_args__ = {'mysql_engine':'innodb'}
        id = sa.Column(sa.Integer, primary_key=True)
        model4_id = sa.Column(sa.ForeignKey('model4.id'))
        model1_id = sa.Column(sa.ForeignKey('model1.id'))

        model4 = sa.orm.relationship('model4') # one-to-many
        model5 = sa.orm.relationship('model5', uselist=True) # many-to-one
        model6 = sa.orm.relationship('model6', uselist=True, secondary='model3_model6') # many-to-many

    return model3


@pytest.fixture
def model4(model_base):
    mtm_table = sa.Table(
        'model4_model7', model_base.metadata,
        sa.Column('model4_id', sa.Integer, sa.ForeignKey('model4.id', ondelete='CASCADE')),
        sa.Column('model7_id', sa.Integer, sa.ForeignKey('model7.id', ondelete='CASCADE')),
        mysql_engine='innodb'
    )

    class model4(model_base):
        __tablename__ = 'model4'
        __table_args__ = {'mysql_engine':'innodb'}
        id = sa.Column(sa.Integer, primary_key=True)
        model5_id = sa.Column(sa.ForeignKey('model5.id'))
        model2_id = sa.Column(sa.ForeignKey('model2.id'))

        model5 = sa.orm.relationship('model5') # one-to-many
        model6 = sa.orm.relationship('model6', uselist=True) # many-to-one
        model7 = sa.orm.relationship('model7', uselist=True, secondary='model4_model7') # many-to-many

    return model4


@pytest.fixture
def model5(model_base):
    mtm_table = sa.Table(
        'model5_model8', model_base.metadata,
        sa.Column('model5_id', sa.Integer, sa.ForeignKey('model5.id', ondelete='CASCADE')),
        sa.Column('model8_id', sa.Integer, sa.ForeignKey('model8.id', ondelete='CASCADE')),
        mysql_engine='innodb'
    )

    class model5(model_base):
        __tablename__ = 'model5'
        __table_args__ = {'mysql_engine':'innodb'}
        id = sa.Column(sa.Integer, primary_key=True)
        model6_id = sa.Column(sa.ForeignKey('model6.id'))
        model3_id = sa.Column(sa.ForeignKey('model3.id'))

        model6 = sa.orm.relationship('model6') # one-to-many
        model7 = sa.orm.relationship('model7', uselist=True) # many-to-one
        model8 = sa.orm.relationship('model8', uselist=True, secondary='model5_model8') # many-to-many

    return model5


@pytest.fixture
def model6(model_base):
    mtm_table = sa.Table(
        'model6_model9', model_base.metadata,
        sa.Column('model6_id', sa.Integer, sa.ForeignKey('model6.id', ondelete='CASCADE')),
        sa.Column('model9_id', sa.Integer, sa.ForeignKey('model9.id', ondelete='CASCADE')),
        mysql_engine='innodb'
    )

    class model6(model_base):
        __tablename__ = 'model6'
        __table_args__ = {'mysql_engine':'innodb'}
        id = sa.Column(sa.Integer, primary_key=True)
        model7_id = sa.Column(sa.ForeignKey('model7.id'))
        model4_id = sa.Column(sa.ForeignKey('model4.id'))

        model7 = sa.orm.relationship('model7') # one-to-many
        model8 = sa.orm.relationship('model8', uselist=True) # many-to-one
        model9 = sa.orm.relationship('model9', uselist=True, secondary='model6_model9') # many-to-many

    return model6


@pytest.fixture
def model7(model_base):
    class model7(model_base):
        __tablename__ = 'model7'
        __table_args__ = {'mysql_engine':'innodb'}
        id = sa.Column(sa.Integer, primary_key=True)
        model8_id = sa.Column(sa.ForeignKey('model8.id'))
        model5_id = sa.Column(sa.ForeignKey('model5.id'))

        model8 = sa.orm.relationship('model8') # one-to-many
        model9 = sa.orm.relationship('model9', uselist=True) # many-to-one

    return model7


@pytest.fixture
def model8(model_base):
    class model8(model_base):
        __tablename__ = 'model8'
        __table_args__ = {'mysql_engine':'innodb'}
        id = sa.Column(sa.Integer, primary_key=True)
        model9_id = sa.Column(sa.ForeignKey('model9.id'))
        model6_id = sa.Column(sa.ForeignKey('model6.id'))

        model9 = sa.orm.relationship('model9') # one-to-many

    return model8


@pytest.fixture
def model9(model_base):
    class model9(model_base):
        __tablename__ = 'model9'
        __table_args__ = {'mysql_engine':'innodb'}
        id = sa.Column(sa.Integer, primary_key=True)
        model7_id = sa.Column(sa.ForeignKey('model7.id'))

    return model9
