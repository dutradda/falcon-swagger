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


class ModelHttpJobsMetaMixin(type):

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
        if session.redis_bind.ttl(key) < 0:
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

