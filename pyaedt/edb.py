"""This module contains the ``Edb`` class.

This module is implicitily loaded in HFSS 3D Layout when launched.

"""
from pyaedt import settings

if not settings.use_grpc_edb_api:
    from pyedb.legacy.edb import EdbLegacy as Edb

    edb = Edb()
else:
    raise Exception("gRPC Not yet available.")
