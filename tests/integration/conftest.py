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


from falconswagger.models.orm.session import Session
from unittest import mock
from sqlalchemy import create_engine

import pytest
import pymysql



@pytest.fixture
def redis():
    return mock.MagicMock()


@pytest.fixture
def session(model_base, request, variables, redis):
    conn = pymysql.connect(
        user=variables['database']['user'], password=variables['database']['password'])

    with conn.cursor() as cursor:
        try:
            cursor.execute('drop database {};'.format(variables['database']['database']))
        except:
            pass

        cursor.execute('create database {};'.format(variables['database']['database']))
    conn.commit()
    conn.close()

    if variables['database']['password']:
        url = 'mysql+pymysql://{user}:{password}'\
            '@{host}:{port}/{database}'.format(**variables['database'])
    else:
        variables['database'].pop('password')
        url = 'mysql+pymysql://{user}'\
            '@{host}:{port}/{database}'.format(**variables['database'])
        variables['database']['password'] = None

    engine = create_engine(url)
    model_base.metadata.bind = engine
    model_base.metadata.create_all()

    session = Session(bind=engine, redis_bind=redis)

    def tear_down():
        session.close()

    request.addfinalizer(tear_down)
    return session
