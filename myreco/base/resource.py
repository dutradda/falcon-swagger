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


from jsonschema import Draft4Validator
from falcon.errors import HTTPMethodNotAllowed
from falcon import after as hook_after, before as hook_before

from myreco.base.session import Session


class FalconJsonSchemaResource(object):
    def __init__(
            self, post_input_json_schema={},
            post_output_json_schema={},
            put_input_json_schema={},
            put_output_json_schema={},
            patch_input_json_schema={},
            patch_output_json_schema={},
            delete_input_json_schema={},
            delete_output_json_schema={},
            get_input_json_schema={},
            get_output_json_schema={}):
        self.post_input_json_schema = post_input_json_schema
        self.post_output_json_schema = post_output_json_schema
        self.put_input_json_schema = put_input_json_schema
        self.put_output_json_schema = put_output_json_schema
        self.patch_input_json_schema = patch_input_json_schema
        self.patch_output_json_schema = patch_output_json_schema
        self.delete_input_json_schema = delete_input_json_schema
        self.delete_output_json_schema = delete_output_json_schema
        self.get_input_json_schema = get_input_json_schema
        self.get_output_json_schema = get_output_json_schema

        if post_input_json_schema:
            self.on_post_validator = Draft4Validator(post_input_json_schema)

        if put_input_json_schema:
            self.on_put_validator = Draft4Validator(put_input_json_schema)

        if patch_input_json_schema:
            self.on_post_validator = Draft4Validator(patch_input_json_schema)

        if delete_input_json_schema:
            self.on_delete_validator = Draft4Validator(delete_input_json_schema)

        if get_input_json_schema:
            self.on_get_validator = Draft4Validator(get_input_json_schema)


class FalconModelResource(FalconJsonSchemaResource):
    def __init__(
            self, api, allowed_methods,
            model, api_prefix='', session=None,
            post_input_json_schema={},
            post_output_json_schema={},
            put_input_json_schema={},
            put_output_json_schema={},
            patch_input_json_schema={},
            patch_output_json_schema={},
            delete_input_json_schema={},
            delete_output_json_schema={},
            get_input_json_schema={},
            get_output_json_schema={}):
        self.allowed_methods = [am.upper() for am in allowed_methods]
        self.model = model
        self.session = session
        self._add_route(api, api_prefix)
        FalconJsonSchemaResourceBase.__init__(
            self, post_input_json_schema,
            post_output_json_schema,
            put_input_json_schema,
            put_output_json_schema,
            patch_input_json_schema,
            patch_output_json_schema,
            delete_input_json_schema,
            delete_output_json_schema,
            get_input_json_schema,
            get_output_json_schema)

    def _add_route(self, api, api_prefix):
        uri = api_prefix + '/{}/'.format(self.model.tablename) + '{' + self.model.id_name + '}/'
        api.add_route(uri, self)

    def on_post(self, req, resp, **kwargs):
        self._raise_method_not_allowed('POST')
        self.model.insert(self.session, req.body)

    def _raise_method_not_allowed(self, method):
        if not method in self.allowed_methods:
            raise HTTPMethodNotAllowed(self.allowed_methods)

    def on_put(self, req, resp, **kwargs):
        self._raise_method_not_allowed('PUT')
        id_ = self._get_id_from_kwargs(kwargs)
        self.model.update(self.session, {id_: req.body})

    def _get_id_from_kwargs(self, kwargs):
        return kwargs.pop(self.model.id_name)

    def on_patch(self, req, resp, **kwargs):
        self._raise_method_not_allowed('PATCH')
        id_ = self._get_id_from_kwargs(kwargs)
        self.model.update(self.session, {id_: req.body})

    def on_delete(self, req, resp, **kwargs):
        self._raise_method_not_allowed('DELETE')
        id_ = self._get_id_from_kwargs(kwargs)
        self.model.update(self.session, {id_: req.body})

    def on_get(self, req, resp, **kwargs):
        self._raise_method_not_allowed('GET')
        id_ = self._get_id_from_kwargs(kwargs)
        self.model.get(self.session, id_)
