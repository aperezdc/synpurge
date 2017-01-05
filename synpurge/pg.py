# -*- coding: utf-8 -*-
# vim:fenc=utf-8
#
# Copyright © 2017 Adrian Perez <aperez@igalia.com>
#
# Distributed under terms of the GPLv3 license.

import attr

_SQL_EVENT_ID_BEFORE = """\
SELECT event_id
  FROM events
WHERE room_id = $1
  AND origin_server_ts <= $2
ORDER BY origin_server_ts DESC
LIMIT 1
"""

class Database(object):
    def __init__(self, db):
        self._db = db
        self._event_id_before = db.prepare(_SQL_EVENT_ID_BEFORE)

    def find_event_id(self, room_id, upto):
        timestamp = int(upto.epoch * 1000)
        return self._event_id_before.first(room_id, timestamp)

    def __repr__(self):
        return "Database(pg={!r})".format(self._db)

    def __del__(self):
        del self._db


def open(db_conf):
    from postgresql import driver
    return Database(driver.connect(**attr.asdict(db_conf)))
