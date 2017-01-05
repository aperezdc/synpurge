# -*- coding: utf-8 -*-
# vim:fenc=utf-8
#
# Copyright © 2017 Adrian Perez <aperez@igalia.com>
#
# Distributed under terms of the GPLv3 license.

from os import path
from postgresql import lib, sys

sys.libpath.append(path.abspath(path.dirname(__file__)))

synapse = lib.load("synapse")
category = lib.Category(synapse)
