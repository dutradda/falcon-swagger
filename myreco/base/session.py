from sqlalchemy.orm import sessionmaker, Session as SessionSA
from sqlalchemy.orm.query import Query
from sqlalchemy import event

from collections import defaultdict


class SessionBase(SessionSA):
    def __init__(
            self, bind=None, autoflush=True,
            expire_on_commit=True, _enable_transaction_accounting=True,
            autocommit=False, twophase=False, weak_identity_map=True,
            binds=None, extension=None, info=None, query_cls=Query, redis_bind=None):
        self.redis_bind = redis_bind
        self._insts_to_hdel = set()
        self._insts_to_hmset = set()
        SessionSA.__init__(
            self, bind=bind, autoflush=autoflush, expire_on_commit=expire_on_commit,
            _enable_transaction_accounting=_enable_transaction_accounting,
            autocommit=autocommit, twophase=twophase, weak_identity_map=weak_identity_map,
            binds=binds, extension=extension, info=info, query_cls=query_cls)

    def commit(self):
        SessionSA.commit(self)
        self._update_objects_on_redis()
        self._update_back_references_on_redis()

    def _update_objects_on_redis(self):
        ids_of_insts_to_del = [inst.get_redis_key() for inst in self._insts_to_del]
        self.redis_bind.delete(*ids_of_insts_to_del)

        insts_to_hmset = defaultdict(dict)

        for inst in self._insts_to_hmset:
            insts_to_hmset[type(inst)][inst.get_redis_key()] = inst.todict()

        for insts in insts_to_hmset.values():
            self.redis_bind.hmset(self._prefix, insts)

    def _update_back_references_on_redis(self):
        references = set.union(self._insts_to_del, self._insts_to_hmset)
        back_references = set()
        [back_references.update(ref.get_back_refs()) for ref in references]
        back_references.difference_update(references)

        self._exec_hmset(back_references)

    def _update_objects_on_redis(self):
        self._exec_hdel(self._insts_to_hdel)
        self._exec_hmset(self._insts_to_hmset)

    def _exec_hdel(self, insts):
        ids_of_insts_to_hdel = defaultdict(set)

        for inst in self._insts_to_hdel:
            ids_of_insts_to_hdel[type(inst).get_redis_key()].add(self._get_inst_key(inst))

        for redis_key, ids in ids_of_insts_to_hdel.items():
            self.redis_bind.hdel(redis_key, *ids)

    def _exec_hmset(self, insts):
        insts_to_hmset = defaultdict(dict)

        for inst in self._insts_to_hmset:
            insts_to_hmset[type(inst).get_redis_key()][inst.get_redis_key()] = inst.todict()

        for redis_key, hmset_map in insts_to_hmset.items():
            self.redis_bind.hmset(redis_key, hmset_map)

    def _get_inst_key(self, inst):
        return str(getattr(inst, inst.id_name))

    def mark_for_hdel(self, inst):
        self._insts_to_hdel.add(inst)

    def mark_for_hmset(self, inst):
        self._insts_to_hmset.add(inst)


Session = SessionMaker()


@event.listens_for(Session, 'persistent_to_deleted')
def deleted_from_database(session, instance):
    session.mark_for_hdel(instance)


@event.listens_for(Session, 'pending_to_persistent')
def added_to_database(session, instance):
    session.mark_for_hmset(instance)
