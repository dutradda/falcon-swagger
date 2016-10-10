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


from falconswagger.exceptions import UnauthorizedError
from falcon import HTTP_FORBIDDEN, HTTP_METHODS
from types import MethodType


def authorization_hook(req, resp, model, params):
    users_model = model.get_model('users')

    authorization = req.auth
    if authorization is None:
        raise UnauthorizedError('Authorization header is required', users_model.__realm__)

    basic_str = 'Basic '
    if authorization.startswith(basic_str):
        authorization = authorization.replace(basic_str, '')

    session = req.context['session']
    authorization = users_model.authorize(
        session, authorization, req.uri_template, req.path, req.method)

    if authorization is None:
        raise UnauthorizedError('Invalid authorization', users_model.__realm__)

    elif authorization is False:
        raise UnauthorizedError(
            'Please refresh your authorization', users_model.__realm__, HTTP_FORBIDDEN)


def before_operation(func):
    def _wrap_class_method(cls, method_name):
        method = getattr(cls, method_name, None)
        if method:
            setattr(cls, method_name, _before_operation(method))

    def _before_operation(func_):
        cls = None
        is_cls = False
        if isinstance(func_, type):
            is_cls = True
            cls = func_
        elif isinstance(func_, MethodType):
            cls = func_.__self__

        def do_before(req, resp, **params):
            func(req, resp, cls, params)
            func_(req, resp, **params)

        if is_cls:
            methods = set()
            for path in cls.__schema__.values():
                for method_name, method in path.items():
                    if method_name.upper() in HTTP_METHODS:
                        op_name = method.get('operationId')
                        if op_name:
                            methods.add(op_name)

            for method in methods:
                _wrap_class_method(cls, method)

            return cls

        return do_before

    return _before_operation
