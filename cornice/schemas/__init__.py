# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

from cornice.schemas import generic


adapters = {}


try:
    __import__('colander')
except ImportError:
    pass
else:
    from cornice.schemas import colander_adapter

    adapters['cornice'] = colander_adapter.ColanderAdapter
