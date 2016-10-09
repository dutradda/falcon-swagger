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


from falcon import HTTP_UNAUTHORIZED, HTTP_BAD_REQUEST

import json


class FalconSwaggerError(Exception):
    def __init__(self, message, status, headers=None, input_=None):
        self.message = message
        self.status = status
        self.args = (message,)
        self.headers = {} if headers is None else headers
        self.input_ = input_

    def to_json(self):
        if self.input_ is not None:
            return self._to_json_with_input()

        return {
            'error': self.message
        }

    def _to_json_with_input(self):
        return {
            'error': {
                'message': self.message,
                'input': self.input_
            }
        }

    @staticmethod
    def handle(exception, req, resp, params):
        resp.status = exception.status
        resp.body = json.dumps(exception.to_json())
        [resp.append_header(key, value) for key, value in exception.headers.items()]


class ModelBaseError(FalconSwaggerError):
    def __init__(self, message, input_=None):
        FalconSwaggerError.__init__(self, message, HTTP_BAD_REQUEST)
        self.input_ = input_


class JSONError(FalconSwaggerError):
    def __init__(self, message, headers=None, input_=None):
        FalconSwaggerError.__init__(self, message, HTTP_BAD_REQUEST, headers=headers, input_=input_)


class UnauthorizedError(FalconSwaggerError):
    def __init__(self, message, realm, status=HTTP_UNAUTHORIZED):
        headers = {'WWW-Authenticate': 'Basic realm="{}"'.format(realm)}
        FalconSwaggerError.__init__(self, message, status, headers)
