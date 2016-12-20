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


from falconswagger.router import Route
from falconswagger.utils import build_validator
from falconswagger.exceptions import ModelBaseError, JSONError
from falconswagger.models.logger import ModelLoggerMetaMixin
from falconswagger.models.http import ModelHttpMetaMixin
from falcon.errors import HTTPNotFound, HTTPMethodNotAllowed
from falcon import HTTP_CREATED, HTTP_NO_CONTENT, HTTP_METHODS
from falcon.responders import create_default_options
from jsonschema import ValidationError
from collections import defaultdict
from copy import deepcopy
from importlib import import_module
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from datetime import datetime
import json
import os.path
import logging
import random
import re

class _ModelContextMetaMixin(type):

    def _get_context_values(cls, context):
        session = context['session']
        parameters = context['parameters']
        req_body = parameters['body']
        id_ = parameters['path']
        kwargs = deepcopy(parameters['headers'])
        kwargs.pop('Authorization', None)
        kwargs.update(parameters['query_string'])
        return session, req_body, id_, kwargs



class _ModelPostMetaMixin(_ModelContextMetaMixin):

    def post_by_body(cls, req, resp):
        cls._insert(req, resp)

    def _insert(cls, req, resp, with_update=False):
        session, req_body, id_, kwargs = cls._get_context_values(req.context)

        if with_update:
            if isinstance(req_body, list):
                [cls._update_dict(obj, id_) for obj in req_body]
            elif isinstance(req_body, dict):
                cls._update_dict(req_body, id_)

        resp_body = cls.insert(session, req_body, **kwargs)
        resp_body = resp_body if isinstance(req_body, list) else resp_body[0]
        resp.body = json.dumps(resp_body)
        resp.status = HTTP_CREATED

    def _update_dict(cls, dict_, other):
        dict_.update({k: v for k, v in other.items() if k not in dict_})

    def post_by_uri_template(cls, req, resp):
        cls._insert(req, resp, with_update=True)


class _ModelPutMetaMixin(_ModelPostMetaMixin):

    def put_by_body(cls, req, resp):
        cls._update(req, resp)

    def _update(cls, req, resp):
        session, req_body, _, kwargs = cls._get_context_values(req.context)

        objs = cls.update(session, req_body, **kwargs)

        if objs:
            resp.body = json.dumps(objs)
        else:
            raise HTTPNotFound()

    def put_by_uri_template(cls, req, resp):
        session, req_body, id_, kwargs = cls._get_context_values(req.context)
        req_body_copy = deepcopy(req_body)

        cls._update_dict(req_body, id_)
        objs = cls.update(session, req_body, ids=id_, **kwargs)

        if not objs:
            req_body = req_body_copy

            ambigous_keys = [
                kwa for kwa in id_ if kwa in req_body and req_body[kwa] != id_[kwa]]
            if ambigous_keys:
                body_schema = req.context.get('body_schema')
                raise ValidationError(
                    "Ambiguous value for '{}'".format(
                        "', '".join(ambigous_keys)),
                    instance={'body': req_body, 'uri': id_}, schema=body_schema)

            req.context['parameters']['body'] = req_body
            cls._insert(req, resp, with_update=True)
        else:
            resp.body = json.dumps(objs[0])


class _ModelPatchMetaMixin(_ModelPutMetaMixin):

    def patch_by_body(cls, req, resp):
        cls._update(req, resp)

    def patch_by_uri_template(cls, req, resp):
        session, req_body, id_, kwargs = cls._get_context_values(req.context)

        cls._update_dict(req_body, id_)
        objs = cls.update(session, req_body, ids=id_, **kwargs)
        if objs:
            resp.body = json.dumps(objs[0])
        else:
            raise HTTPNotFound()


class _ModelDeleteMetaMixin(_ModelContextMetaMixin):

    def delete_by_body(cls, req, resp):
        session, req_body, _, kwargs = cls._get_context_values(req.context)

        cls.delete(session, req_body, **kwargs)
        resp.status = HTTP_NO_CONTENT

    def delete_by_uri_template(cls, req, resp):
        session, _, id_, kwargs = cls._get_context_values(req.context)

        cls.delete(session, id_, **kwargs)
        resp.status = HTTP_NO_CONTENT


class _ModelGetMetaMixin(_ModelContextMetaMixin):

    def get_by_body(cls, req, resp):
        session, req_body, _, kwargs = cls._get_context_values(req.context)

        if req_body:
            resp_body = cls.get(session, req_body, **kwargs)
        else:
            resp_body = cls.get(session, **kwargs)

        if not resp_body:
            raise HTTPNotFound()

        resp.body = json.dumps(resp_body)

    def get_by_uri_template(cls, req, resp):
        session, _, id_, kwargs = cls._get_context_values(req.context)

        resp_body = cls.get(session, id_, **kwargs)
        if not resp_body:
            raise HTTPNotFound()

        resp.body = json.dumps(resp_body[0])

    def get_schema(cls, req, resp):
        resp.body = json.dumps(cls.__schema__)



class ModelJobsMetaMixin(type):

    def post_job(cls, req, resp):
        job_session = req.context['session']
        job_session = type(job_session)(bind=job_session.bind.engine.connect(),
                                        redis_bind=job_session.redis_bind)
        req.context['job_session'] = job_session

        job_hash = '{:x}'.format(random.getrandbits(128))
        executor = ThreadPoolExecutor(2)

        job = executor.submit(cls._run_job, req, resp)
        executor.submit(cls._job_watcher, job, job_hash, job_session)

        resp.body = json.dumps({'hash': job_hash})

    def _run_job(cls, req, resp):
        pass

    def _job_watcher(cls, job, job_hash, session):
        cls._set_job(job_hash, {'status': 'running'}, session)
        start_time = datetime.now()

        try:
            result = job.result()
        except Exception as error:
            result = {'name': error.__class__.__name__, 'message': str(error)}
            status = 'error'
            cls._logger.exception('ERROR from job {}'.format(job_hash))

        else:
            status = 'done'

        end_time = datetime.now()
        elapsed_time = str(end_time - start_time)[:-3]
        job_obj = {'status': status, 'result': result, 'elapsed_time': elapsed_time}

        cls._set_job(job_hash, job_obj, session)
        session.bind.close()
        session.close()

    def _set_job(cls, job_hash, status, session):
        key = cls._build_jobs_key()
        session.redis_bind.hset(key, job_hash, json.dumps(status))
        if session.redis_bind.ttl(key) > 0:
            session.redis_bind.expire(key, 7*24*60*60)

    def _build_jobs_key(cls):
        return cls.__key__ + '_jobs'

    def get_job(cls, req, resp):
        job_hash = req.context['parameters']['query_string']['hash']
        status = cls._get_job(job_hash, req.context['session'])

        if status is None:
            raise HTTPNotFound()

        resp.body = status

    def _get_job(cls, job_hash, session):
        return session.redis_bind.hget(cls._build_jobs_key(), job_hash)


class ModelOrmHttpMetaMixin(
        ModelHttpMetaMixin,
        _ModelPatchMetaMixin,
        _ModelDeleteMetaMixin,
        _ModelGetMetaMixin,
        ModelJobsMetaMixin):
    pass
