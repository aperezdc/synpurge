# -*- coding: utf-8 -*-
# vim:fenc=utf-8
#
# Copyright © 2017 Adrian Perez <aperez@igalia.com>
#
# Distributed under terms of the GPLv3 license.

import attr
import re

from attr import validators as vv
from datetime import timedelta


_time_unit_map = dict(second="seconds", seconds="seconds",
                      minute="minutes", minutes="minutes",
                      hour="hours", hours="hours",
                      day="days", days="days",
                      week="weeks", weeks="weeks")

def _string_to_timedelta(s):
    parts = s.strip().split()
    if len(parts) == 1:
        return timedelta(days=int(parts[0]))
    if len(parts) != 2:
        raise ValueError(s)
    amount = int(parts[0])
    unit = parts[1].strip().lower()
    if unit in ("month", "months"):
        amount *= 30
        unit = "days"
    if unit in ("year", "years"):
        amount *= 365
        unit = "days"
    unit = _time_unit_map.get(unit, None)
    if unit is None:
        raise ValueError("Invalid unit: {!r}".format(parts[1].strip()))
    return timedelta(**{ unit: amount })


def _optional_string_to_timedelta(s):
    return None if s is None else _string_to_timedelta(s)


def _timedelta_to_string(d):
    if d.seconds > 0:
        return "{} seconds".format(d.total_seconds())
    else:
        return "{} days".format(d.days)


@attr.s(frozen=True)
class Config(object):
    # TODO: Properly validate the URL.
    homeserver = attr.ib(validator=vv.instance_of(str))
    keep = attr.ib(validator=vv.instance_of(timedelta),
                   convert=_string_to_timedelta)
    token = attr.ib(validator=vv.instance_of(str))
    rooms = attr.ib(validator=vv.instance_of(set),
                    hash=False)
    purge_request_timeout = \
            attr.ib(validator=vv.optional(vv.instance_of(timedelta)),
                    convert=_optional_string_to_timedelta,
                    default=None)

    def as_config_snippet(self):
        lines = ["[synpurge]",
                 "homeserver = {}".format(self.homeserver),
                 "keep = {}".format(_timedelta_to_string(self.keep)),  
                 "token = {}".format(self.token)]
        if self.purge_request_timeout is not None:
            value = _timedelta_to_string(self.purge_request_timeout)
            lines.append("purge_request_timeout = {}".format(value))
        room_snippets = (r.as_config_snippet() for r in self.rooms)
        return "\n".join(lines) + "\n\n" + "\n\n".join(sorted(room_snippets))


@attr.s(frozen=True)
class Room(object):
    _config = attr.ib(validator=vv.instance_of(Config),
                      repr=False)
    name = attr.ib(validator=vv.instance_of(str))
    _keep = attr.ib(validator=vv.optional(vv.instance_of(timedelta)),
                    convert=lambda s: None if s is None else
                    _string_to_timedelta(s),
                    default=None)
    _token = attr.ib(validator=vv.optional(vv.instance_of(str)),
                     default=None)
    pattern = attr.ib(validator=vv.instance_of(bool),
                      default=False,
                      convert=bool)

    def as_config_snippet(self):
        lines = [ "[{}]".format(self.name) ]
        if self._keep is not None:
            lines.append("keep = {}".format(_timedelta_to_string(self._keep)))
        if self._token is not None:
            lines.append("token = {}".format(self._token))
        if self.pattern:
            lines.append("pattern = true")
        return "\n".join(lines)

    @property
    def keep(self):
        return self._config.keep if self._keep is None else self._keep

    @property
    def token(self):
        return self._config.token if self._token is None else self._token

    def build_alias_matcher(self):
        re_match = re.compile(r"^" + self.name + r"$").match
        return lambda s: bool(re_match(s))


def load(path):
    from configparser import ConfigParser
    ini = ConfigParser(default_section=None, interpolation=None)
    ini.read(path)
    rooms = set()
    cfg = Config(rooms=rooms, **ini["synpurge"])
    [rooms.add(Room(name=s, config=cfg, **ini[s]))
        for s in ini.sections() if s != "synpurge"]
    return cfg
