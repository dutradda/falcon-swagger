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


from falconswagger.exceptions import ModelBaseError
import re
import logging


def _camel_case_convert(name):
    s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
    return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()


class ModelBaseMeta(type):
    __all_models__ = dict()

    def __init__(cls, name, bases_classes, attributes):
        if not hasattr(cls, '__key__'):
            name = cls.__name__.replace('Model', '')
            cls.__key__ = getattr(cls, '__key__', _camel_case_convert(name))

        all_models = type(cls).__all_models__
        key = cls.__key__

        if key in all_models:
            raise ModelBaseError("The model '{}' was already declared with key '{}'".format(
                all_models[key], key))

        all_models[key] = cls
        cls._logger = logging.getLogger(cls.__module__ + '.' + cls.__name__)
