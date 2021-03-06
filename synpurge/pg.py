# -*- coding: utf-8 -*-
# vim:fenc=utf-8
#
# Copyright © 2017 Adrian Perez <aperez@igalia.com>
#
# Distributed under terms of the GPLv3 license.

import attr
import itertools
import logging

from attr import validators as vv

log = logging.getLogger(__name__)


#
# This list is sorted out with the tables likely to be smaller listed
# first, as to slowly go about making space for cleaning up the even
# bigger tables coming up afterwards.
#
_HUGE_TABLES = ("event_to_state_groups",
                "state_events",
                "room_memberships",
                "event_search",
                "event_reference_hashes",
                "event_edges",
                "event_auth",
                "events",
                "event_json",
                "state_groups_state")


@attr.s(frozen=True, slots=True)
class RoomInfo(object):
    room_id = attr.ib(validator=vv.instance_of(str))
    creator = attr.ib(validator=vv.instance_of(str))
    is_public = attr.ib(validator=vv.instance_of(bool), convert=bool)
    aliases = attr.ib(validator=vv.instance_of(frozenset), convert=frozenset)
    topic = attr.ib(validator=vv.optional(vv.instance_of(str)), default=None)
    name = attr.ib(validator=vv.optional(vv.instance_of(str)), default=None)

    def asdict(self):
        d = attr.asdict(self)
        d["aliases"] = list(d["aliases"])
        return d


class Database(object):
    def __init__(self, db, db_name):
        self._db = db
        self._name = db_name
        self._cached_all_rooms = None
        self._cached_public_rooms = None

    def find_event_id(self, room_id, upto):
        timestamp = int(upto.epoch * 1000)
        return self._db.synapse.event_id_before(room_id, timestamp)

    def get_room_id(self, room_alias, params=None):
        return self._db.synapse.resolve_room_alias(room_alias)

    def get_room_info(self, room_id):
        info = self._db.synapse.get_room_info(room_id)
        return info if info is None else RoomInfo(**dict(info.items()))

    def find_table_indexes(self, table_name):
        return self._db.synapse.table_indexes(table_name)

    @property
    def public_rooms(self):
        if self._cached_public_rooms is None:
            self._cached_public_rooms = \
                dict(self._db.synapse.public_room_aliases)
            log.debug("Cached aliases for %i public rooms",
                      len(self._cached_public_rooms))
        return self._cached_public_rooms

    @property
    def all_rooms(self):
        if self._cached_all_rooms is None:
            self._cached_all_rooms = \
                dict(self._db.synapse.room_aliases)
            log.debug("Cached aliases for %i rooms",
                      len(self._cached_all_rooms))
        return self._cached_all_rooms

    def cleanup(self):
        log.info("Starting database cleanup")
        for i, table_name in zip(itertools.count(1), _HUGE_TABLES):
            log.debug("Cleaning up table '%s' (%i/%i)",
                      table_name, i, len(_HUGE_TABLES))
            # VACUUM does not work from an ILF library.
            self._db.execute("VACUUM FULL ANALYZE {}".format(table_name))
        log.info("Finished database cleanup")

    def cleanup_full(self):
        log.info("Starting full database cleanup")
        # VACUUM does not work from an ILF library.
        self._db.execute("VACUUM FULL ANALYZE")
        log.info("Finished full database cleanup")

    def reindex(self):
        log.info("Starting database reindexing")
        for i, table_name in zip(itertools.count(1), _HUGE_TABLES):
            log.debug("Re-indexing table '%s' (%i/%i)",
                      table_name, i, len(_HUGE_TABLES))
            # REINDEX does not work from an ILF library.
            self._db.execute("REINDEX TABLE {}".format(table_name))
        log.info("Finished database reindexing")

    def reindex_concurrent(self):
        log.info("Starting database concurrent reindexing")
        for i, table_name in zip(itertools.count(1), _HUGE_TABLES):
            log.debug("Re-indexing table '%s' concurrently (%i/%i)",
                      table_name, i, len(_HUGE_TABLES))
            self.reindex_table_concurrent(table_name)
        log.info("Finished database concurrent reindexing")

    def reindex_full(self):
        log.info("Starting full database reindexing")
        # REINDEX does not work from an ILF library.
        self._db.execute("REINDEX DATABASE {}".format(self._name))
        log.info("Finished full database reindexing")

    def reindex_table_concurrent(self, table_name):
        for idx_name, idx_definition, idx_cluster in self.find_table_indexes(table_name):
            log.debug("Re-indexing index '%s' in table '%s'", idx_name, table_name)
            tmp_idx_name = "{}_tmp".format(idx_name)
            tmp_idx_definition = idx_definition.replace(idx_name, tmp_idx_name)
            try:
                self.__execute(tmp_idx_definition)
                if idx_cluster:
                    self.__execute("ALTER TABLE {} CLUSTER ON {}".format(table_name, tmp_idx_name))
                self.__execute("DROP INDEX {}".format(idx_name))
                self.__execute("ALTER INDEX {} RENAME TO {}".format(tmp_idx_name, idx_name))
            except:
                self.__execute("DROP INDEX {}".format(tmp_idx_name))

    def __execute(self, statement):
        log.debug(statement)
        self._db.execute(statement)

    def __repr__(self):
        return "Database(pg={!r})".format(self._db)


def open(db_conf):
    from postgresql import driver
    from .pglib import category
    conn_params = attr.asdict(db_conf)
    for key in ("clean_interval", "clean_full", "reindex_interval", "reindex_full"):
        del conn_params[key]
    return Database(driver.connect(category=category, **conn_params),
                    db_conf.database or db_conf.user)
