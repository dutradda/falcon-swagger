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


from myreco.base.models.base import build_validator, get_module_path
import inspect


class EngineTypeMeta(type):

    def __init__(cls, name, bases_classes, attributes):
        cls.__config_validator__ = None
        schema = getattr(cls, '__configuration_schema__', None)
        if schema:
            cls.__config_validator__ = build_validator(schema, get_module_path(cls))


class EngineType(metaclass=EngineTypeMeta):
    def __init__(self, configuration):
        self.configuration = configuration

    def get_variables(self, engine):
        return []

    def validate_config(self, engine):
        pass


class EngineRecommenderMixin(object):

    def get_recommendations(self, **variables):
        return []


class EngineDataImporterBigqueryMixin(object):

    def import_data(self):
        pass


from myreco.domain.engines.types.neighborhood.engine import NeighborhoodEngine
from myreco.domain.engines.types.top_seller.engine import TopSellerEngine
from myreco.domain.engines.types.visual_similarity.engine import VisualSimilarityEngine


class EngineTypeChooser(object):

    def __new__(cls, name):
        if name == 'neighborhood':
            return NeighborhoodEngine

        elif name == 'top_seller':
            return TopSellerEngine

        elif name == 'visual_similarity':
            return VisualSimilarityEngine
