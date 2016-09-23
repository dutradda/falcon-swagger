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


from myreco.exceptions import ModelBaseError


class ModelBaseMeta(type):

    def __init__(cls, name, bases, attributes):
        auth_hook = attributes.get('__auth_hook__', None)
        build_default_routes = attributes.get('__build_default_routes__', True)
        build_generic_routes = attributes.get('__build_generic_routes__', False)

        routes = attributes.get('__routes__', set())
        if hasattr(cls, '__routes_builder__'):
            routes = cls.__routes_builder__(cls, build_default_routes, build_generic_routes, routes, auth_hook)
            cls.__routes__ = routes

    def _to_list(cls, objs):
        return objs if isinstance(objs, list) else [objs]

    def _raises_ids_limit_offset_error(cls, ids, limit, offset):
        if (ids is not None) and (limit is not None or offset is not None):
            raise ModelBaseError(
                "'get' method can't be called with 'ids' and with 'offset' or 'limit'",
                {'ids': ids, 'limit': limit, 'offset': offset})

    def on_post(cls, *args, **kwargs):
        pass

    def on_put(cls, *args, **kwargs):
        pass

    def on_patch(cls, *args, **kwargs):
        pass

    def on_delete(cls, *args, **kwargs):
        pass

    def on_get(cls, *args, **kwargs):
        pass


class ModelBase(object):
    __api_prefix__ = '/'

    def get_key(self):
        return str(self.get_ids_values())


class ModelBuilderBaseMeta(type):

    def _set_api_prefix(cls, api_prefix):
        if api_prefix is not None:
            ModelBase.__api_prefix__ =  '/' + api_prefix.strip('/') + '/'
