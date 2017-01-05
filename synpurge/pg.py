# -*- coding: utf-8 -*-
# vim:fenc=utf-8
#
# Copyright © 2017 Adrian Perez <aperez@igalia.com>
#
# Distributed under terms of the GPLv3 license.

import attr
import logging

log = logging.getLogger(__name__)


class Database(object):
    def __init__(self, db):
        self._db = db
        self._cached_all_rooms = None
        self._cached_public_rooms = None

    def find_event_id(self, room_id, upto):
        timestamp = int(upto.epoch * 1000)
        return self._db.synapse.event_id_before(room_id, timestamp)

    def get_room_id(self, room_alias, params=None):
        return self._db.synapse.resolve_room_alias(room_alias)

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
            log.debug("Cached aliases for %i rooms")
        return self._cached_all_rooms

    def __repr__(self):
        return "Database(pg={!r})".format(self._db)


def open(db_conf):
    from postgresql import driver
    from .pglib import category
    return Database(driver.connect(category=category, **attr.asdict(db_conf)))
