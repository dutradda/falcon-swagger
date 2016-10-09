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
from myreco.base.models.sqlalchemy_redis import SQLAlchemyRedisModelBuilder


class ModelsFactory(object):

	def __init__(self, commons_models_attributes=None, commons_tables_attributes=None):
		self.base_model = SQLAlchemyRedisModelBuilder()
		self.meta_class = type(self.base_model)
		self._commons_models_attrs = self._init_attributes(commons_models_attributes)
		self._commons_tables_attrs = self._init_attributes(commons_tables_attributes)

	def _init_attributes(self, attrs=None, update=None):
		if attrs is None:
			if update is None:
				attrs = dict()
			else:
				attrs = update
		elif update is not None:
			attrs.update(update)
		return attrs

	def make_all_models(self):
		self.make_all_tables()
		return {
			'engines': self.make_engines_model(),
			'engines_types_names': self.make_engines_types_names_model(),
			'engines_managers': self.make_engines_managers_model(),
			'engines_managers_variables': self.make_engines_managers_variables_model(),
			'items_types': self.make_items_types_model(),
			'placements': self.make_placements_model(),
			'variations': self.make_variations_model(),
			'ab_test_users': self.make_ab_test_users_model(),
			'stores': self.make_stores_model(),
			'uris': self.make_uris_model(),
			'users': self.make_users_model(),
			'methods': self.make_methods_model(),
			'grants': self.make_grants_model(),
			'variables': self.make_variables_model()
		}

	def make_all_tables(self):
		return {
			'users_grants': self.make_users_grants_table(),
			'users_stores': self.make_users_stores_table(),
			'variations_engines_managers': self.make_variations_engines_managers_table(),
			'engines_managers_fallbacks': self.make_engines_managers_fallbacks_table()
		}

	def make_users_grants_table(self, attributes=None):
		attributes = self._init_attributes(attributes, self._commons_tables_attrs)
		return build_users_grants_table(self.base_model.metadata, **attributes)

	def make_users_stores_table(self, attributes=None):
		attributes = self._init_attributes(attributes, self._commons_tables_attrs)
		return build_users_stores_table(self.base_model.metadata, **attributes)

	def make_variations_engines_managers_table(self, attributes=None):
		attributes = self._init_attributes(attributes, self._commons_tables_attrs)
		return build_variations_engines_managers_table(self.base_model.metadata, **attributes)

	def make_engines_managers_fallbacks_table(self, attributes=None):
		attributes = self._init_attributes(attributes, self._commons_tables_attrs)
		return build_engines_managers_fallbacks_table(self.base_model.metadata, **attributes)

	def make_engines_model(self, attributes=None):
		attributes = self._init_attributes(attributes, self._commons_models_attrs)
		return self.meta_class('EnginesModel', (EnginesModelBase, self.base_model), attributes)

	def make_engines_types_names_model(self, attributes=None):
		attributes = self._init_attributes(attributes, self._commons_models_attrs)
		return self.meta_class(
			'EnginesTypesNamesModel', (EnginesTypesNamesModelBase, self.base_model), attributes)

	def make_engines_managers_model(self, attributes=None):
		attributes = self._init_attributes(attributes, self._commons_models_attrs)
		return self.meta_class(
			'EnginesManagersModel', (EnginesManagersModelBase, self.base_model), attributes)

	def make_engines_managers_variables_model(self, attributes=None):
		attributes = self._init_attributes(attributes, self._commons_models_attrs)
		return self.meta_class(
			'EnginesManagersVariablesModel',
			(EnginesManagersVariablesModelBase, self.base_model), attributes)

	def make_items_types_model(self, attributes=None):
		attributes = self._init_attributes(attributes, self._commons_models_attrs)
		return self.meta_class(
			'ItemsTypesModel', (ItemsTypesModelBase, self.base_model), attributes)

	def make_placements_model(self, attributes=None):
		attributes = self._init_attributes(attributes, self._commons_models_attrs)
		return self.meta_class(
			'PlacementsModel', (PlacementsModelBase, self.base_model), attributes)

	def make_variations_model(self, attributes=None):
		attributes = self._init_attributes(attributes, self._commons_models_attrs)
		return self.meta_class(
			'VariationsModel', (VariationsModelBase, self.base_model), attributes)

	def make_ab_test_users_model(self, attributes=None):
		attributes = self._init_attributes(attributes, self._commons_models_attrs)
		return self.meta_class(
			'ABTestUsersModel', (ABTestUsersModelBase, self.base_model), attributes)

	def make_stores_model(self, attributes=None):
		attributes = self._init_attributes(attributes, self._commons_models_attrs)
		return self.meta_class(
			'StoresModel', (StoresModelBase, self.base_model), attributes)

	def make_uris_model(self, attributes=None):
		attributes = self._init_attributes(attributes, self._commons_models_attrs)
		return self.meta_class(
			'URIsModel', (URIsModelBase, self.base_model), attributes)

	def make_users_model(self, attributes=None):
		attributes = self._init_attributes(attributes, self._commons_models_attrs)
		return self.meta_class(
			'UsersModel', (UsersModelBase, self.base_model), attributes)

	def make_methods_model(self, attributes=None):
		attributes = self._init_attributes(attributes, self._commons_models_attrs)
		return self.meta_class(
			'MethodsModel', (MethodsModelBase, self.base_model), attributes)

	def make_grants_model(self, attributes=None):
		attributes = self._init_attributes(attributes, self._commons_models_attrs)
		return self.meta_class(
			'GrantsModel', (GrantsModelBase, self.base_model), attributes)

	def make_variables_model(self, attributes=None):
		attributes = self._init_attributes(attributes, self._commons_models_attrs)
		return self.meta_class(
			'VariablesModel', (VariablesModelBase, self.base_model), attributes)
