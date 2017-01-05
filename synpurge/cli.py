#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vim:fenc=utf-8
#
# Copyright © 2017 Adrian Perez <aperez@igalia.com>
#
# Distributed under terms of the GPLv3 license.

import logging

from argh import EntryPoint, arg

log = logging.getLogger(__name__)
cmd = EntryPoint("synpurg", dict(
    description="Purges Synapse's room history",
))


@cmd
def version():
    """Print the version of program."""
    from . import __version__
    return __version__


@cmd
def check(path: "configuration file",
          verbose: "display configuration" = False):
    """Load and validate a configuration file."""
    from . import config
    try:
        c = config.load(path)
    except Exception as e:
        raise SystemExit(e)
    if verbose:
        return c.as_config_snippet()


@cmd
def purge(path: "configuration file",
          debug: "enable debugging output" = False,
          verbose: "enable verbose operation" = False,
          pretend: "only show what would be done" = False,
          keep_going: "keep going on purge timeouts" = False):
    """Run a batch of room history purges."""
    if debug:
        logging.basicConfig(level=logging.DEBUG)
    elif verbose:
        logging.basicConfig(level=logging.INFO)

    from . import config
    try:
        c = config.load(path)
    except Exception as e:
        raise SystemExit("Error loading configuration: {!s}".format(e))

    from . import purger
    from . import minimx

    api = minimx.API(homeserver=c.homeserver, token=c.token)
    log.info("Resolving room aliases")
    try:
        purges = purger.resolve_room_ids(c, api)
    except purger.DuplicateRoomId as e:
        raise SystemExit(("Two configuration items resolve to the same room"
                          " ({})\n---\n{}\n---\n{}").format(e.room_id,
                                                            e.old_config.as_config_snippet(),
                                                            e.new_config.as_config_snippet()))

    if c.database:
        from . import pg
        pgdb = pg.open(c.database)
        log.debug("Using PostgreSQL: %r", pgdb)
        def find_event_id(room_id, upto, _token=None):
            return pgdb.find_event_id(room_id, upto)
    else:
        def find_event_id(room_id, upto, token=None):
            params = None if token is None else dict(access_token=token)
            return purger.find_event_id(room_id, upto, api, params=params)

    import delorean
    import itertools
    now = delorean.utcnow()
    num_purges= len(purges)
    for current, purge in zip(itertools.count(1), purges):
        log.info("Finding reference event (%i/%i) for room %s (%s)",
                 current, num_purges, purge.room_id, purge.config.name)
        purge.event_id = find_event_id(purge.room_id,
                                       now - purge.config.keep,
                                       purge.config.token)

    if pretend:
        for purge in purges:
            if purge.event_id is None:
                continue
            print("{} {} ({}, keep up to {})".format(purge.room_id, purge.event_id,
                                                     purge.config.name,
                                                     (now - purge.config.keep).humanize()))
        return

    for current, purge in zip(itertools.count(1), purges):
        if purge.event_id is None:
            log.info("Skipped (%i/%i) for room %s (%s), event %s",
                     current, num_purges, purge.room_id, purge.config.name, purge.event_id)
            continue
        log.info("Purging (%i/%i) for room %s (%s), event %s",
                 current, num_purges, purge.room_id, purge.config.name, purge.event_id)
        try:
            api.purge_history(purge.room_id, purge.event_id,
                              params=dict(access_token=purge.config.token))
        except minimx.APITimeout:
            if keep_going:
                log.info("Timed out purging room %s (%s) - continuing",
                         purge.room_id, purge.config.name)
            else:
                raise SystemExit("Timed out purging room {} ({})".format(purge.room_id,
                                                                         purge.config.name))
