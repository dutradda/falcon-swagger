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


MODEL_BASE_CLASS_NAME = 'ModelBase'


from sqlalchemy.ext.declarative import declarative_base as declarative_base_sa
from sqlalchemy.ext.declarative.base import _declarative_constructor

from myreco.base.models.json_schema import JsonSchemaModelMeta
from myreco.base.models.sqlalchemy import SQLAlchemyModelMeta, SQLAlchemyModel


class BaseMeta(JsonSchemaModelMeta, SQLAlchemyModelMeta):
    pass


def declarative_base(
        bind=None, metadata=None, mapper=None,
        constructor=_declarative_constructor,
        class_registry=None):
    return declarative_base_sa(
    name=MODEL_BASE_CLASS_NAME, metaclass=BaseMeta,
    cls=SQLAlchemyModel, bind=bind, metadata=metadata,
    mapper=mapper, constructor=constructor)

ModelBase = declarative_base()
