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
    ABTestUsersModelBase, build_variations_engines_managers)
from myreco.domain.engines_managers.models import (EnginesManagersVariablesModelBase,
    EnginesManagersModelBase, build_engines_managers_fallbacks_table)
from myreco.domain.engines.models import EnginesModelBase, EnginesTypesNamesModelBase
from myreco.domain.items_types.models import ItemsTypesModelBase
from myreco.base.models.sqlalchemy_redis import SQLAlchemyRedisModelBuilder


model_base = SQLAlchemyRedisModelBuilder()


build_users_grants_table(model_base.metadata, mysql_engine='innodb')
build_users_stores_table(model_base.metadata, mysql_engine='innodb')
build_variations_engines_managers(model_base.metadata, mysql_engine='innodb')
build_engines_managers_fallbacks_table(model_base.metadata, mysql_engine='innodb')


class GrantsModel(model_base, GrantsModelBase):
    __table_args__ = {'mysql_engine':'innodb'}


class URIsModel(model_base, URIsModelBase):
    __table_args__ = {'mysql_engine':'innodb'}


class MethodsModel(model_base, MethodsModelBase):
    __table_args__ = {'mysql_engine':'innodb'}


class UsersModel(model_base, UsersModelBase):
    __table_args__ = {'mysql_engine':'innodb'}


class StoresModel(model_base, StoresModelBase):
    __table_args__ = {'mysql_engine':'innodb'}


class VariablesModel(model_base, VariablesModelBase):
    __table_args__ = {'mysql_engine':'innodb'}


class PlacementsModel(model_base, PlacementsModelBase):
    __table_args__ = {'mysql_engine':'innodb'}


class VariationsModel(model_base, VariationsModelBase):
    __table_args__ = {'mysql_engine':'innodb'}


class ABTestUsersModel(model_base, ABTestUsersModelBase):
    __table_args__ = {'mysql_engine':'innodb'}


class EnginesManagersVariablesModel(model_base, EnginesManagersVariablesModelBase):
    __table_args__ = {'mysql_engine':'innodb'}


class EnginesManagersModel(model_base, EnginesManagersModelBase):
    __table_args__ = {'mysql_engine':'innodb'}


class EnginesModel(model_base, EnginesModelBase):
    __table_args__ = {'mysql_engine':'innodb'}


class EnginesTypesNamesModel(model_base, EnginesTypesNamesModelBase):
    __table_args__ = {'mysql_engine':'innodb'}


class ItemsTypesModel(model_base, ItemsTypesModelBase):
    __table_args__ = {'mysql_engine':'innodb'}
