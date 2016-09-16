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


from sqlalchemy.orm import sessionmaker, Session as SessionSA
from sqlalchemy.orm.query import Query
from sqlalchemy import event, or_
from collections import defaultdict

import json

class _SessionBase(SessionSA):
    def __init__(
            self, bind=None, autoflush=True,
            expire_on_commit=True, _enable_transaction_accounting=True,
            autocommit=False, twophase=False, weak_identity_map=True,
            binds=None, extension=None, info=None, query_cls=Query, redis_bind=None):
        self.redis_bind = redis_bind
        self.user = None
        self._clean_redis_sets()
        SessionSA.__init__(
            self, bind=bind, autoflush=autoflush, expire_on_commit=expire_on_commit,
            _enable_transaction_accounting=_enable_transaction_accounting,
            autocommit=autocommit, twophase=twophase, weak_identity_map=weak_identity_map,
            binds=binds, extension=extension, info=info, query_cls=query_cls)

    def _clean_redis_sets(self):
        self._insts_to_hdel = set()
        self._insts_to_hmset = set()

    def commit(self):
        SessionSA.commit(self)
        if self.redis_bind is not None:
            try:
                self._update_objects_on_redis()
                self._update_back_references_on_redis()
            except:
                raise
            finally:
                self._clean_redis_sets()

    def _update_objects_on_redis(self):
        self._exec_hdel(self._insts_to_hdel)
        self._exec_hmset(self._insts_to_hmset)

    def _exec_hdel(self, insts):
        models_keys_insts_keys_map = defaultdict(set)

        for inst in self._insts_to_hdel:
            model_redis_key = self.build_model_redis_key(type(inst))
            inst_redis_key = self.build_inst_redis_key(inst)
            models_keys_insts_keys_map[model_redis_key].add(inst_redis_key)

        for model_key, insts_keys in models_keys_insts_keys_map.items():
            self.redis_bind.hdel(model_key, *insts_keys)

    def _exec_hmset(self, insts):
        models_keys_insts_keys_insts_map = defaultdict(dict)

        for inst in insts:
            model_redis_key = self.build_model_redis_key(type(inst))
            inst_redis_key = self.build_inst_redis_key(inst)
            models_keys_insts_keys_insts_map[model_redis_key][inst_redis_key] = inst.todict()

        for model_key, insts_keys_insts_map in models_keys_insts_keys_insts_map.items():
            self.redis_bind.hmset(model_key, insts_keys_insts_map)

    def build_inst_redis_key(self, inst):
        return str(inst.get_ids_values())

    def build_model_redis_key(self, model):
        return model.tablename

    def _update_back_references_on_redis(self):
        references = set.union(self._insts_to_hdel, self._insts_to_hmset)
        back_references = set()
        [back_references.update(ref.get_related(self)) for ref in references]
        back_references.difference_update(references)

        self._exec_hmset(back_references)

    def mark_for_hdel(self, inst):
        self._insts_to_hdel.add(inst)

    def mark_for_hmset(self, inst):
        self._insts_to_hmset.add(inst)


Session = sessionmaker(class_=_SessionBase)


@event.listens_for(Session, 'persistent_to_deleted')
def deleted_from_database(session, instance):
    if session.redis_bind is not None and instance is not None:
        session.mark_for_hdel(instance)


@event.listens_for(Session, 'pending_to_persistent')
def added_to_database(session, instance):
    if session.redis_bind is not None and instance is not None:
        session.mark_for_hmset(instance)
