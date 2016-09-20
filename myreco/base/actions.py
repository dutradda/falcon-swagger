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


from falcon import HTTP_CREATED, HTTPNotFound, HTTP_NO_CONTENT
from jsonschema import RefResolver, Draft4Validator, ValidationError
from copy import deepcopy


class _DefaultPostActionsMeta(type):

    def base_action(cls, req, resp, **kwargs):
        cls._insert(req, resp)

    def _insert(cls, req, resp, with_update=False, **kwargs):
        model = req.context['model']
        session = req.context['session']
        req_body = req.context['body']

        if with_update:
            if isinstance(req_body, list):
                [cls._update_dict(obj, kwargs) for obj in req_body]
            elif isinstance(req_body, dict):
                cls._update_dict(req_body, kwargs)

        resp.body = model.insert(session, req_body)
        resp.body = resp.body if isinstance(req_body, list) else resp.body[0]
        resp.status = HTTP_CREATED

    def _update_dict(cls, dict_, other):
        dict_.update({k: v for k, v in other.items() if k not in dict_})

    def ids_action(cls, req, resp, **kwargs):
        cls._insert(req, resp, with_update=True, **kwargs)


class DefaultPostActions(metaclass=_DefaultPostActionsMeta):
    pass


class _DefaultPutActionsMeta(_DefaultPostActionsMeta):

    def base_action(cls, req, resp, **kwargs):
        cls._update(req, resp, **kwargs)

    def _update(cls, req, resp, **kwargs):
        model = req.context['model']
        session = req.context['session']
        req_body = req.context['body']

        objs = model.update(session, req_body)

        if objs:
            resp.body = objs
        else:
            raise HTTPNotFound()

    def ids_action(cls, req, resp, **kwargs):
        model = req.context['model']
        session = req.context['session']
        route = req.context['route']
        req_body = req.context['body']
        req_body_copy = deepcopy(req.context['body'])

        cls._update_dict(req_body, kwargs)
        objs = model.update(session, req_body, ids=kwargs)

        if not objs:
            req_body = req_body_copy
            ambigous_keys = [
                kwa for kwa in kwargs if kwa in req_body and req_body[kwa] != kwargs[kwa]]
            if ambigous_keys:
                raise ValidationError(
                    "Ambiguous value for '{}'".format(
                        "', '".join(ambigous_keys)),
                    instance={'body': req_body, 'uri': kwargs}, schema=route.validator.schema)

            req.context['body'] = req_body
            cls._insert(req, resp, with_update=True, **kwargs)
        else:
            resp.body = objs[0]


class DefaultPutActions(metaclass=_DefaultPutActionsMeta):
    pass


class _DefaultPatchActionsMeta(_DefaultPutActionsMeta):

    def ids_action(cls, req, resp, **kwargs):
        model = req.context['model']
        session = req.context['session']
        req_body = req.context['body']
        cls._update_dict(req_body, kwargs)
        objs = model.update(session, req_body, ids=kwargs)
        if objs:
            resp.body = objs[0]
        else:
            raise HTTPNotFound()


class DefaultPatchActions(metaclass=_DefaultPatchActionsMeta):
    pass


class _DefaultDeleteActionsMeta(type):

    def base_action(cls, req, resp, **kwargs):
        model = req.context['model']
        session = req.context['session']
        req_body = req.context['body']
        model.delete(session, req.context['body'])
        resp.status = HTTP_NO_CONTENT

    def ids_action(cls, req, resp, **kwargs):
        model = req.context['model']
        session = req.context['session']
        model.delete(session, kwargs)
        resp.status = HTTP_NO_CONTENT


class DefaultDeleteActions(metaclass=_DefaultDeleteActionsMeta):
    pass


class _DefaultGetActionsMeta(type):

    def base_action(cls, req, resp, **kwargs):
        model = req.context['model']
        session = req.context['session']
        req_body = req.context['body']

        if req_body:
            resp.body = model.get(session, req_body)
        else:
            resp.body = model.get(session)

        if not resp.body:
            raise HTTPNotFound()

    def ids_action(cls, req, resp, **kwargs):
        model = req.context['model']
        session = req.context['session']
        resp.body = model.get(session, kwargs)
        if not resp.body:
            raise HTTPNotFound()
        resp.body = resp.body[0]


class DefaultGetActions(metaclass=_DefaultGetActionsMeta):
    pass
