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


from myreco.base.models.base import get_model_schema
from myreco.domain.engines.types.base import EngineRecommenderMixin, EngineType
from jsonschema import ValidationError
import json


class VisualSimilarityEngine(EngineRecommenderMixin, EngineType):
    __configuration_schema__ = get_model_schema(__file__)

    def get_variables(self, engine):
        item_id_name = self.configuration['item_id_name']
        aggregators_ids_name = self.configuration['aggregators_ids_name']
        item_type_schema_props = json.loads(engine.item_type.schema_json)['properties']
        return [{
            'name': item_id_name,
            'schema': item_type_schema_props[item_id_name]
        },{
            'name': aggregators_ids_name,
            'schema': item_type_schema_props[aggregators_ids_name]
        }]

    def validate_config(self, engine):
        item_id_name = self.configuration['item_id_name']
        aggregators_ids_name = self.configuration['aggregators_ids_name']
        item_type_schema_props = json.loads(engine.item_type.schema_json)['properties']
        message = "Configuration key '{}' not in item_type schema"

        if item_id_name not in item_type_schema_props:
            raise ValidationError(message.format('item_id_name'),
                instance=dict_inst, schema=item_type_schema_props)

        elif aggregators_ids_name not in item_type_schema_props:
            raise ValidationError(message.format('aggregators_ids_name'),
                instance=dict_inst, schema=item_type_schema_props)
