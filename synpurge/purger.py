# -*- coding: utf-8 -*-
# vim:fenc=utf-8
#
# Copyright © 2017 Adrian Perez <aperez@igalia.com>
#
# Distributed under terms of the GPLv3 license.

import attr
import logging

from . import config
from attr import validators as vv
from datetime import datetime
from delorean import Delorean

log = logging.getLogger(__name__)


@attr.s(frozen=True)
class DuplicateRoomId(Exception):
    room_id = attr.ib(validator=vv.instance_of(str))
    old_config = attr.ib(validator=vv.instance_of(config.Room))
    new_config = attr.ib(validator=vv.instance_of(config.Room))
    old_matched_alias = attr.ib(validator=vv.optional(vv.instance_of(str)),
                                default=None)
    new_matched_alias = attr.ib(validator=vv.optional(vv.instance_of(str)),
                                default=None)

    def __str__(self):
        lines = [self.room_id]
        lines.append("")  # Extra empty line.
        if self.old_matched_alias and self.old_config.pattern:
            lines.append("# Matched alias: " + self.old_matched_alias)
        lines.append(self.old_config.as_config_snippet())
        lines.append("")  # Extra empty line.
        if self.new_matched_alias and self.new_config.pattern:
            lines.append("# Matched alias: " + self.new_matched_alias)
        lines.append(self.old_config.as_config_snippet())
        return "\n".join(lines)


@attr.s(slots=True)
class PurgeInfo(object):
    room_id = attr.ib(validator=vv.instance_of(str))
    config = attr.ib(validator=vv.instance_of(config.Room))
    event_id = attr.ib(validator=vv.optional(vv.instance_of(str)),
                       default=None, init=False)
    matched_alias = attr.ib(validator=vv.optional(vv.instance_of(str)),
                            default=None)

    @property
    def room_display_name(self):
        if self.matched_alias is None:
            if self.config.pattern:
                return self.room_id
            else:
                return self.config.name
        else:
            return self.matched_alias


@attr.s
class RoomIdsResolver(object):
    _api = attr.ib()
    _rooms = attr.ib(default=attr.Factory(dict),
                     init=False, hash=False)

    def __add(self, room_id, room_conf, matched_alias=None, replace=False):
        old_info = self._rooms.get(room_id, None)
        if not (replace or old_info is None):
            raise DuplicateRoomId(room_id, old_info.config, room_conf,
                                  old_info.matched_alias, matched_alias)
        if matched_alias:
            log.debug("Resolved %s -> %s (%s)",
                      room_conf.name, room_id, matched_alias)
        else:
            log.debug("Resolved %s -> %s", room_conf.name, room_id)
        self._rooms[room_id] = PurgeInfo(room_id, room_conf,
                                         matched_alias=matched_alias)

    def resolve(self, room_conf: config.Room):
        params = dict(access_token=room_conf.token)
        if room_conf.pattern:
            log.debug("Expanding room pattern: %s", room_conf.name)
            room_alias_matches = room_conf.build_alias_matcher()
            for room_id, room_aliases in self._api.all_rooms.items():
                for room_alias in room_aliases:
                    if room_alias_matches(room_alias):
                        self.__add(room_id, room_conf, room_alias)
        elif room_conf.name.startswith("!"):
            self.__add(room_conf.name, room_conf)
        else:
            log.debug("Expanding room alias: %s", room_conf.name)
            self.__add(self._api.get_room_id(room_conf.name,
                                             params=params),
                       room_conf, room_conf.name)

    def get_purge_info(self):
        return frozenset((info for room_id, info in self._rooms.items()))


def resolve_room_ids(conf, api):
    resolver = RoomIdsResolver(api)
    for room_conf in conf.rooms:
        resolver.resolve(room_conf)
    return resolver.get_purge_info()


def find_event_id(room_id, upto, api, params=None):
    log.debug("Finding event before %s for room %s",
              upto.format_datetime(), room_id)
    data = api.get_room_messages(room_id, limit=250, params=params)
    while True:
        start, end, chunk = data["start"], data["end"], data["chunk"]
        log.debug("Got %d messages from %s to %s", len(chunk), start, end)
        for event in chunk:
            ts = datetime.fromtimestamp(event["origin_server_ts"] / 1000)
            event_time = Delorean(ts, timezone="UTC")
            if event_time < upto:
                event_id = event["event_id"]
                log.debug("Found event %s (%s)", event_id,
                          event_time.format_datetime())
                return event_id
        if start == end:
            return None
        data = api.get_room_messages(room_id, end, limit=250, params=params)
