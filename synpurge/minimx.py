# -*- coding: utf-8 -*-
# vim:fenc=utf-8
#
# Copyright © 2017 Adrian Perez <aperez@igalia.com>
#
# Distributed under terms of the GPLv3 license.

import attr
import logging
import requests

from attr import validators as vv
from urllib.parse import quote as urlquote
from requests import Timeout as APITimeout

log = logging.getLogger(__name__)


class APIError(Exception):
    pass


def _make_requests_session():
    s = requests.Session()
    s.headers.update({
        "Content-Type": "application/json",
    })
    return s


@attr.s
class API(object):
    # TODO: Properly validate the URL.
    homeserver = attr.ib(validator=vv.instance_of(str))
    token = attr.ib(validator=vv.instance_of(str))

    _session = attr.ib(validator=vv.instance_of(requests.Session),
                       default=attr.Factory(_make_requests_session))

    _cached_public_rooms = attr.ib(default=None, init=False,
                                   hash=False, repr=False)

    _API_BASE = "/_matrix/client/r0/"

    def url(self, *components):
        encoded = (urlquote(c) for c in components)
        return self.homeserver + self._API_BASE + "/".join(encoded)

    def request(self, method, url, raw_response=False, raw_body=False,
                timeout=None, params=None):
        if params is None:
            params = {}
        if "access_token" not in params:
            params["access_token"] = self.token
        # TODO: Handle rate-limiting and retries.
        req = self._session.prepare_request(requests.Request(method, url,
                                                             params=params))
        res = self._session.send(req, timeout=timeout)
        if raw_response:
            return res
        if res.status_code == 200:
            if raw_body:
                return res.text
            else:
                return res.json()
        else:
            raise APIError(res.text)

    @property
    def public_rooms(self):
        if self._cached_public_rooms is None:
            log.info("Fetching public room directory")
            rooms = ((r["room_id"], r) for r in self.get_public_rooms())
            self._cached_public_rooms = dict(rooms)
            log.info("Cached information for %d rooms",
                     len(self._cached_public_rooms))
        return self._cached_public_rooms
    
    @public_rooms.deleter
    def public_rooms(self):
        # This effectivey invalidates the cache. The next access to the
        # property will fetch the room directory from the homeserver again.
        self._cached_public_rooms = None

    def get_public_rooms(self, timeout=None, params=None):
        next_batch = None
        prev_batch = False
        while next_batch != prev_batch:
            data = self.__get_public_rooms_chunk(next_batch,
                                                 timeout,
                                                 params)
            for room in data["chunk"]:
                yield room
            prev_batch = next_batch
            next_batch = data["next_batch"]

    def __get_public_rooms_chunk(self, next_batch, timeout, params):
        if params is None:
            params = {}
        if next_batch is not None:
            params["next_batch"] = next_batch
        return self.request("GET", self.url("publicRooms"),
                            timeout=timeout,
                            params=params)

    def get_room_id(self, room_alias, timeout=None, params=None):
        data = self.request("GET",
                            self.url("directory", "room", room_alias),
                            timeout=timeout,
                            params=params)
        return data["room_id"]

    def get_room_messages(self, room_id, start=None, end=None, limit=None,
                          forward=False, timeout=None, params=None):
        if params is None:
            params = {}
        params["dir"] = "f" if forward else "b"
        if start is not None: params["from"] = start
        if end is not None: params["to"] = end
        if limit is not None: params["limit"] = limit
        return self.request("GET",
                            self.url("rooms", room_id, "messages"),
                            timeout=timeout,
                            params=params)

    def purge_history(self, room_id, event_id, timeout=None, params=None):
        if timeout is not None and timeout < 180:
            log.warn("Timeout smaller than 180s (%is), will likely timeout", timeout)
        return self.request("POST",
                            self.url("admin", "purge_history", room_id, event_id),
                            timeout=timeout, params=params)
