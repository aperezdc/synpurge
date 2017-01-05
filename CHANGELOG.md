# Change Log
All notable changes to this project will be documented in this file.
The format is based on [Keep a Changelog](http://keepachangelog.com/).

## [Unreleased]

## [v3] - 2017-01-05
### Added
- Synpurge can now connect directly to PostgreSQL to map dates to events.
  This makes operation substantially faster.

### Fixed
- Purging rooms for which a suitable reference event cannot be found are
  skipped, instead of causing API calls to the purge history endpoing which
  have bogus parameters.

## [v2] - 2017-01-05
### Added
- New command line syntax, with subcommands.
- Better logging: the `purge` subcommand supports both verbose operation
  (`-v`, `--verbose`), and outputting debug messages (`-d`, `--debug`).
  Note that full URLs including the access tokens being used are printed
  when debugging output is enabled.
- The `purge --pretend` will figure out which calls to the purge history
  API endpoint are needed, and print a summary *without* doing the requests.
- Added the ability to continue with the next purge operation on a timeout
  (`-k`, `--keep-going`).

### Fixed
- Python 3.4 is supported now.
- Include `CHANGELOG.md` in generated tarballs.

## [v1] - 2017-01-04
### Added
- Initial implementation.

[Unreleased]: https://github.com/aperezdc/synpurge/compare/v2...HEAD
[v2]: https://github.com/aperezdc/synpurge/compare/v1...v2
