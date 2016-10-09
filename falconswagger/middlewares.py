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


from falconswagger.session import Session, RedisSession
from falconswagger.models.sqlalchemy_redis import SQLAlchemyModelMeta
from falconswagger.models.redis import RedisModelMeta



class SessionMiddleware(object):

    def __init__(self, sqlalchemy_bind=None, redis_bind=None):
        self.sqlalchemy_bind = sqlalchemy_bind
        self.redis_bind = redis_bind

    def process_resource(self, req, resp, model, uri_params):
        if model.__session__:
            req.context['session'] = model.__session__
            return

        if isinstance(model, SQLAlchemyModelMeta):
            req.context['session'] = Session(
                bind=self.sqlalchemy_bind, redis_bind=self.redis_bind)

        elif isinstance(model, RedisModelMeta):
            req.context['session'] = RedisSession(self.redis_bind)

    def process_response(self, req, resp, model):
        session = req.context.pop('session', None)
        if session is not None \
                and isinstance(model, SQLAlchemyModelMeta) \
                and not model.__session__:
            session.close()
