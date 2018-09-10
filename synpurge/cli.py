# -*- coding: utf-8 -*-
# vim:fenc=utf-8
#
# Copyright © 2017 Adrian Perez <aperez@igalia.com>
#
# Distributed under terms of the GPLv3 license.

import logging

from argh import EntryPoint

log = logging.getLogger(__name__)
cmd = EntryPoint("synpurge", dict(
    description="Purges Synapse's room history",
))


def get_real_room_id(room):
    # TODO: Provide an alternate implemenation using the HTTP API.
    if room.startswith("!"):
        room_id = room
    else:
        room_id = pgdb.get_room_id(room)
        if room_id is None:
            raise SystemExit("No room has the alias {}".format(room))
    return room_id


@cmd
def version():
    """Print the version of program."""
    from . import __version__
    return __version__


@cmd
def check(path: "configuration file",
          verbose: "display configuration"=False):
    """Load and validate a configuration file."""
    from . import config
    try:
        c = config.load(path)
    except Exception as e:
        raise SystemExit(e)
    if verbose:
        return c.as_config_snippet()


def _configure(config_path,
               open_database=False,
               require_database=True,
               debug=False,
               verbose=False):
    if debug:
        logging.basicConfig(level=logging.DEBUG)
    elif verbose:
        logging.basicConfig(level=logging.INFO)

    from . import config, pg
    try:
        c = config.load(config_path)
    except Exception as e:
        raise SystemExit("Error loading configuration: {!s}".format(e))

    db = None
    if open_database:
        if c.database:
            db = pg.open(c.database)
            log.debug("Using PostgreSQL: %r", db)
        elif require_database:
            raise SystemExit("No database configured")

    return c, db


@cmd
def room_info(path: "configuration file",
              room: "room ID or alias",
              debug: "enable debugging output"=False,
              json: "output information as JSON"=False):
    """Obtains information about a room."""
    c, pgdb = _configure(path,
                         open_database=True,
                         require_database=True,
                         debug=debug)
    room_id = get_real_room_id(room)
    room = pgdb.get_room_info(room_id)
    if room is None:
        raise SystemExit("No such room {}".format(room_id))

    if json:
        import json
        return json.dumps(room.asdict(), indent="  ", sort_keys=True)

    print("Room ID:", room.room_id)
    print("Creator:", room.creator)
    print("Public: ", "yes" if room.is_public else "no")
    if room.name:
        print("Name:   ", room.name)
    if room.topic:
        print("Topic:  ", room.topic)
    if len(room.aliases) > 0:
        print("Aliases:", ("\n" + " " * 9).join(sorted(room.aliases)))


@cmd
def cleanup(path: "configuration file",
            reindex: "re-create indexes"=False,
            full: "clean the whole database"=False,
            debug: "enable debugging output"=False,
            verbose: "enable verbose operation"=False):
    """Cleans up the database after purging."""
    c, pgdb = _configure(path,
                         open_database=True,
                         require_database=True,
                         debug=debug,
                         verbose=verbose)
    if full:
        pgdb.cleanup_full()
        if reindex:
            pgdb.reindex_full()
    else:
        pgdb.cleanup()
        if reindex:
            pgdb.reindex()


@cmd
def reindex(path: "configuration file",
            concurrent: "enable concurrent reindexing"=False,
            debug: "enable debugging output"=False,
            verbose: "enable verbose operation"=False):
    """Reindex the database."""
    c, pgdb = _configure(path,
                         open_database=True,
                         require_database=True,
                         debug=debug,
                         verbose=verbose)
    if concurrent:
        pgdb.reindex_concurrent()
    else:
        pgdb.reindex()


@cmd
def purge(path: "configuration file",
          debug: "enable debugging output"=False,
          verbose: "enable verbose operation"=False,
          pretend: "only show what would be done"=False,
          keep_going: "keep going on purge timeouts"=False,
          concurrent: "enable concurrent reindexing"=False):
    """Run a batch of room history purges."""
    c, pgdb = _configure(path,
                         open_database=True,
                         require_database=False,
                         debug=debug,
                         verbose=verbose)

    from . import purger
    from . import minimx

    api = minimx.API(homeserver=c.homeserver, token=c.token)
    if c.database:
        assert pgdb is not None
        if c.database.reindex_full and concurrent:
            raise SystemExit("reindex_full (from configuration file) cannot "
                             "be used simultanously with --concurrent")

        def find_event_id(room_id, upto, _token=None):
            return pgdb.find_event_id(room_id, upto)
    else:
        def find_event_id(room_id, upto, token=None):
            params = None if token is None else dict(access_token=token)
            return purger.find_event_id(room_id, upto, api, params=params)

    log.info("Resolving room aliases")
    try:
        purges, warnings = purger.resolve_room_ids(c, pgdb or api, True)
    except purger.DuplicateRoomId as e:
        raise SystemExit("Two configuration items resolve to the same room: {}".format(e))

    if warnings:
        for ex in warnings:
            log.info("During alias resolution: {}".format(e))

    import delorean
    import itertools
    now = delorean.utcnow()
    num_purges = len(purges)
    for current, purge in zip(itertools.count(1), purges):
        log.info("Finding reference event (%i/%i) for room %s (%s)",
                 current, num_purges, purge.room_id, purge.room_display_name)
        purge.event_id = find_event_id(purge.room_id,
                                       now - purge.config.keep,
                                       purge.config.token)

    # Remove the rooms for which a suitable reference event couldn't be found.
    purges = [p for p in purges if p.event_id is not None]
    num_purges = len(purges)

    if pretend:
        for purge in purges:
            print("{} {} ({}, keep up to {})".format(purge.room_id, purge.event_id,
                                                     purge.room_display_name,
                                                     (now - purge.config.keep).humanize()))
        return

    for current, purge in zip(itertools.count(1), purges):
        log.info("Purging (%i/%i) for room %s (%s), event %s",
                 current, num_purges, purge.room_id,
                 purge.room_display_name, purge.event_id)
        try:
            api.purge_history(purge.room_id, purge.event_id,
                              params=dict(access_token=purge.config.token))
        except minimx.APITimeout:
            if keep_going:
                log.info("Timed out purging room %s (%s) - continuing",
                         purge.room_id, purge.room_display_name)
            else:
                raise SystemExit("Timed out purging room {} ({})".format(purge.room_id,
                                                                         purge.room_display_name))
        if c.database:
            assert pgdb is not None
            if c.database.clean_interval and current % c.database.clean_interval == 0:
                if c.database.clean_full:
                    pgdb.cleanup_full()
                else:
                    pgdb.cleanup()
            if c.database.reindex_interval and current % c.database.reindex_interval == 0:
                if c.database.reindex_full:
                    pgdb.reindex_full()
                elif concurrent:
                    pgdb.reindex_concurrent()
                else:
                    pgdb.reindex()


@cmd
def delete_room(path: "configuration file",
                room: "room ID or alias",
                debug: "enable debugging output"=False,
                verbose: "enable verbose operation"=False,
                pretend: "only show what would be done"=False,
                keep_going: "keep going on purge timeouts"=False):
    """Delete room."""
    c, pgdb = _configure(path,
                         open_database=True,
                         require_database=True,
                         debug=debug)
    room_id = get_real_room_id(room)
    if c.database:
        assert pgdb is not None
        if pretend:
            print("Delete room {}.".format(room_id))
        else:
            pgdb.delete_tuples_from_table_by_id(room_id)


@cmd
def delete_application(path: "configuration file",
                       application: "application ID",
                       debug: "enable debugging output"=False,
                       verbose: "enable verbose operation"=False,
                       pretend: "only show what would be done"=False,
                       keep_going: "keep going on purge timeouts"=False):
    """Delete application."""
    c, pgdb = _configure(path,
                         open_database=True,
                         require_database=True,
                         debug=debug)
    if c.database:
        assert pgdb is not None
        rooms = pgdb.find_rooms_by_application(application)
        for room_id in rooms:
            if pretend:
                print("Delete room {} linked with application {}.".format(room_id, application))
            else:
                pgdb.delete_tuples_from_table_by_id(room_id)
        # Delete things by application
        if pretend:
            print("Delete application {}.".format(application))
        else:
            pgdb.delete_application(application)
