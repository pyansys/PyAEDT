import os
import signal
import socket
import sys
import tempfile
import time

from pyaedt import is_ironpython, settings
from pyaedt.aedt_logger import pyaedt_logger as logger
from pyaedt.misc import list_installed_ansysem

# import sys
from pyaedt.rpc.rpyc_services import FileManagement, GlobalService, ServiceManager, check_port

if not is_ironpython:
    import rpyc
    from rpyc.core import consts
    from rpyc.utils.server import OneShotServer, ThreadedServer


# Maximum Stream message size. Set to 256MB
consts.STREAM_CHUNK = 256000000


safe_attrs = {
    "__abs__",
    "__add__",
    "__and__",
    "__bool__",
    "__class__",
    "__code__",
    "__cmp__",
    "__contains__",
    "__delitem__",
    "__delslice__",
    "__div__",
    "__divmod__",
    "__doc__",
    "__eq__",
    "__float__",
    "__floordiv__",
    "__func__",
    "__ge__",
    "__getmodule",
    "__cache",
    "__weakref__",
    "__dict__",
    "__getitem__",
    "__getslice__",
    "__gt__",
    "__hash__",
    "__hex__",
    "__iadd__",
    "__iand__",
    "__idiv__",
    "__ifloordiv__",
    "__ilshift__",
    "__imod__",
    "__imul__",
    "__index__",
    "__int__",
    "__invert__",
    "__ior__",
    "__ipow__",
    "__irshift__",
    "__isub__",
    "__iter__",
    "__itruediv__",
    "__ixor__",
    "__le__",
    "__len__",
    "__long__",
    "__lshift__",
    "__lt__",
    "__mod__",
    "__mul__",
    "__name__",
    "__ne__",
    "__neg__",
    "__new__",
    "__nonzero__",
    "__oct__",
    "__or__",
    "__pos__",
    "__pow__",
    "__radd__",
    "__rand__",
    "__rdiv__",
    "__rdivmod__",
    "__repr__",
    "__rfloordiv__",
    "__rlshift__",
    "__rmod__",
    "__rmul__",
    "__ror__",
    "__rpow__",
    "__rrshift__",
    "__rshift__",
    "__rsub__",
    "__rtruediv__",
    "__rxor__",
    "__setitem__",
    "__setslice__",
    "__str__",
    "__sub__",
    "__truediv__",
    "__xor__",
    "next",
    "__length_hint__",
    "__enter__",
    "__exit__",
    "__next__",
    "__format__",
}


def pyaedt_service_manager(port=17878, aedt_version=None, student_version=False):
    """Starts an RPyC server on CPython and listens on a specified port.

    This method must run on a server machine.

    Parameters
    ----------
    port : int, optional
        Port that the RPyC server is to listen on.
    aedt_version : str, optional
        Version of Aedt to instantiate with server. Default is latest available version installed on the machine.
    student_version : bool, optional
        Either to initialize Student version AEDT or Commercial version.

    Examples
    --------
    >>> from pyaedt.common_rpc import pyaedt_service_manager
    >>> pyaedt_service_manager()

    """
    port1 = check_port(port)
    if port == 0:
        logger.error("Error. No ports are available.")
        return False
    if port1 != port:
        logger.info("Port {} is already in use. Starting the server on port {}.".format(port, port1))
    aa = list_installed_ansysem()
    if aedt_version:
        if student_version:
            v = "ANSYSEMSV_ROOT{}".format(aedt_version[-4:].replace(".", ""))
        else:
            v = "ANSYSEM_ROOT{}".format(aedt_version[-4:].replace(".", ""))

        valid_version = v
    else:
        if aa:
            valid_version = aa[0]
        else:
            raise Exception("No ANSYSEM_ROOTXXX environment variable defined.")

    ansysem_path = os.environ[valid_version]
    logger.info("AEDT located at {} will be used.".format(ansysem_path))
    os.environ["PYAEDT_SERVER_AEDT_PATH"] = ansysem_path
    os.environ["PYAEDT_SERVER_AEDT_NG"] = "True"
    os.environ["ANS_NODEPCHECK"] = str(1)

    hostname = socket.gethostname()
    t = ThreadedServer(
        ServiceManager,
        hostname=hostname,
        port=port1,
        protocol_config={
            "sync_request_timeout": None,
            "allow_public_attrs": True,
            "allow_setattr": True,
            "safe_attrs": safe_attrs,
            "allow_delattr": True,
            "logger": logger,
        },
    )
    logger.info("Starting the server on port {} on {}.".format(port, hostname))
    t.start()


def launch_server(port=18000, ansysem_path=None, non_graphical=False, threaded=True):
    """Starts an RPyC server and listens on a specified port.

    This method must run on a server machine only.

    Parameters
    ----------
    port : int, optional
        Port that the RPyC server is to listen on.
    ansysem_path : str, optional
        Full path to the AEDT installation directory. The default is
        ``None``. This parameter is needed for IronPython on Linux
        connections only.
    non_graphical : bool, optional
        Whether to start AEDT in non-graphical mode. The default is ``False``,
        which means AEDT starts in graphical mode. This parameter is needed
        for IronPython on Linux connections only.
    threaded : bool, optional

    Examples
    --------
    >>> from pyaedt.common_rpc import launch_server
    >>> launch_server()

    """
    port1 = check_port(port)
    if port == 0:
        logger.error("Error. No ports are available.")
        return False
    if port1 != port:
        logger.info("Port {} is already in use. Starting the server on port {}.".format(port, port1))
    if not ansysem_path:
        aa = list_installed_ansysem()
        if aa:
            ansysem_path = os.environ[aa[0]]
        else:
            raise Exception("No ANSYSEM_ROOTXXX environment variable defined.")
    logger.info("AEDT located at {} will be used.".format(ansysem_path))
    os.environ["PYAEDT_SERVER_AEDT_PATH"] = ansysem_path
    os.environ["PYAEDT_SERVER_AEDT_NG"] = str(non_graphical)
    os.environ["ANS_NO_MONO_CLEANUP"] = str(1)
    os.environ["ANS_NODEPCHECK"] = str(1)

    hostname = socket.gethostname()
    if threaded:
        service = ThreadedServer
    else:
        service = OneShotServer
    t = service(
        GlobalService,
        hostname=hostname,
        port=port1,
        protocol_config={
            "sync_request_timeout": None,
            "allow_public_attrs": True,
            "allow_setattr": True,
            "safe_attrs": safe_attrs,
            "allow_delattr": True,
            "logger": logger,
        },
    )
    logger.info("Starting the server on port {} on {}.".format(port, hostname))
    signal.signal(signal.SIGINT, lambda signum, frame: t.close())
    signal.signal(signal.SIGTERM, lambda signum, frame: t.close())

    t.start()


def create_session(server_name, client_port=None, launch_aedt_on_server=False, aedt_port=None, non_graphical=True):
    """Connect to an existing AEDT server session.

    Parameters
    ----------
    server_name : str
        Name of the remote machine to connect to.
    client_port : int
        Port that the RPyC server will run.
    launch_aedt_on_server : bool, optional
        Either if the method has to start AEDT after the connection is established or not. Default is  `False`.
    aedt_port : int, optional
        Aedt Grpc port on server.
    non_graphical : bool, optional
        Aedt Non Graphical Flag.

    Returns
    -------
    RPyC object.
    """
    try:
        client = rpyc.connect(
            server_name,
            settings.remote_rpc_service_manager_port,
            config={"allow_public_attrs": True, "sync_request_timeout": None},
        )
        if not client_port:
            client_port = client.root.check_port()
        port = client.root.start_service(client_port)
        time.sleep(1)
        cl = connect(server_name, port)
        logger.info("Created new session on port %s", port)
        if "server_name" not in dir(cl):
            cl.server_name = server_name
        if "aedt_port" not in dir(cl):
            cl.aedt_port = None
        if launch_aedt_on_server:
            if not aedt_port:
                aedt_port = client.root.check_port()
            cl.aedt(port=aedt_port, non_graphical=non_graphical)
            logger.info("Aedt started on port %s", aedt_port)
            if cl.aedt_port is None:
                cl.aedt_port = aedt_port
        return cl
    except:
        msg = "Error. No connection exists."
        msg += " Check if pyaedt_service_manager is running and if the port number is correct."
        logger.error(msg)
        return False


def connect(server_name, aedt_client_port):
    """Connect to an existing AEDT server session.

    Parameters
    ----------
    server_name : str
        Name of the remote machine to connect to.
    aedt_client_port : int
        Port that the RPyC server is running on inside AEDT.

    Returns
    -------
    RPyC object.
    """
    try:
        client = rpyc.connect(
            server_name, aedt_client_port, config={"allow_public_attrs": True, "sync_request_timeout": None}
        )
        client.root.redirect(sys.stdout)
        client.filemanager = FileManagement(client)
        try:
            client.aedt = client.root.aedt_grpc
            client.edb = client.root.edb
            client.open_file = client.root.open
            client.create_file = client.root.create
            client.list_dir = client.root.listdir
            client.makedirs = client.root.makedirs
            client.pathexists = client.root.pathexists
            client.close_session = client.root.stop
            client.aedt_port = client.root.aedt_port
            client.aedt_version = client.root.aedt_version
            client.student_version = client.root.student_version
            client.server_name = client.root.server_name
        except AttributeError:
            pass
        settings.remote_rpc_session = client
        settings.remote_rpc_session_temp_folder = os.path.join(
            tempfile.gettempdir(), server_name + "_" + str(aedt_client_port)
        )
        if not os.path.exists(settings.remote_rpc_session_temp_folder):
            os.makedirs(settings.remote_rpc_session_temp_folder)
        return client
    except:
        logger.error("Error. No connection exists. Check if AEDT is running and if the port number is correct.")
        return False
