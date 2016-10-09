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


from myreco.domain.users.models import (GrantsModelBase, URIsModelBase, MethodsModelBase,
    UsersModelBase, build_users_grants_table, build_users_stores_table)
from myreco.domain.stores.model import StoresModelBase
from myreco.domain.variables.model import VariablesModelBase
from myreco.domain.placements.models import (PlacementsModelBase, VariationsModelBase,
    ABTestUsersModelBase, build_variations_engines_managers_table)
from myreco.domain.engines_managers.models import (EnginesManagersVariablesModelBase,
    EnginesManagersModelBase, build_engines_managers_fallbacks_table)
from myreco.domain.engines.models import EnginesModelBase, EnginesTypesNamesModelBase
from myreco.domain.items_types.models import ItemsTypesModelBase
from myreco.domain.models_factory import ModelsFactory


table_args = {'mysql_engine':'innodb'}
factory = ModelsFactory(commons_models_attributes={'__table_args__': table_args},
    					commons_tables_attributes=table_args)
models = factory.make_all_models()

GrantsModel = models['grants']

URIsModel = models['uris']

MethodsModel = models['methods']

UsersModel = models['users']

StoresModel = models['stores']

VariablesModel = models['variables']

PlacementsModel = models['placements']

VariationsModel = models['variations']

ABTestUsersModel = models['ab_test_users']

EnginesManagersVariablesModel = models['engines_managers_variables']

EnginesManagersModel = models['engines_managers']

EnginesModel = models['engines']

EnginesTypesNamesModel = models['engines_types_names']

ItemsTypesModel = models['items_types']
    
SQLAlchemyRedisModelBase = factory.base_model
