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


from myreco.domain.engines.types.neighborhood.engine import NeighborhoodEngine
from myreco.domain.engines.types.top_seller.engine import TopSellerEngine
from myreco.domain.engines.types.visual_similarity.engine import VisualSimilarityEngine
from collections import defaultdict
import inspect


class EngineTypeChooser(object):

    def __new__(cls, name):
        if name == 'neighborhood':
            return NeighborhoodEngine

        elif name == 'top_seller':
            return TopSellerEngine

        elif name == 'visual_similarity':
            return VisualSimilarityEngine


class EngineRecommenderBaseMixin(object):

    def get_variables(self):
        signature = inspect.signature(self.get_recommendations)
        variables = list()
        for var in signature.parameters.values():
            if var.kind.name == 'POSITIONAL_OR_KEYWORD':
                variables.append(var.name)

        return tuple(variables)

    def get_recommendations(self, *args):
        pass


class EngineDataImporterBase(object):

    def import_data(self, configuration):
        pass


class EngineObjectsExporterBase(object):

    def export_objects(self, configuration):
        pass
