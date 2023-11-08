from pyaedt import settings

if not settings.use_grpc_edb_api:
    from pyedb.legacy.edb import EdbLegacy as Edb

    edb = Edb()
else:
    print("gRPC Not yet available.")
