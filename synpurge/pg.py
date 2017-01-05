# -*- coding: utf-8 -*-
# vim:fenc=utf-8
#
# Copyright © 2017 Adrian Perez <aperez@igalia.com>
#
# Distributed under terms of the GPLv3 license.

import attr


class Database(object):
    def __init__(self, db):
        self._db = db

    def find_event_id(self, room_id, upto):
        timestamp = int(upto.epoch * 1000)
        return self._db.synapse.event_id_before(room_id, timestamp)

    def __repr__(self):
        return "Database(pg={!r})".format(self._db)


def open(db_conf):
    from postgresql import driver
    from .pglib import category
    return Database(driver.connect(category=category, **attr.asdict(db_conf)))
