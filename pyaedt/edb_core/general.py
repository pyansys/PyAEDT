"""This module contains EDB general methods and related methods.

"""

from __future__ import absolute_import  # noreorder

import logging

from pyaedt import is_ironpython
from pyaedt.generic.clr_module import Dictionary, List, Tuple
from pyaedt.generic.general_methods import pyaedt_function_handler

if not is_ironpython:  # pragma: no cover
    try:
        from enum import Enum
    except ImportError:
        Enum = None
else:  # pragma: no cover
    Enum = object

logger = logging.getLogger(__name__)


@pyaedt_function_handler()
def convert_netdict_to_pydict(dict_in):
    """Convert a net dictionary to a Python dictionary.

    Parameters
    ----------
    dict_in : dict
        Net dictionary to convert.

    Returns
    -------
    dict
        Dictionary converted to Python.

    """
    pydict = {}
    for key in dict_in.Keys:
        pydict[key] = dict_in[key]
    return pydict


@pyaedt_function_handler()
def convert_pytuple_to_nettuple(_tuple):
    """Convert a Python tuple into a .NET tuple.

    Parameters
    ----------
    tuple : Python tuple

    Returns
    -------
    .NET tuple.
    """
    return Tuple.Create(_tuple[0], _tuple[1])


@pyaedt_function_handler()
def convert_pydict_to_netdict(input_dict):
    """Convert a Python dictionary to a .NET dictionary.

    Parameters
    ----------
    input_dict : dict
        Python dictionary to convert.


    Returns
    -------
    dict
        Dictionary converted to .NET.
    """
    net_dict = Dictionary[type(list(input_dict.keys())[0]), type(list(input_dict.values())[0])]()
    for k1, v1 in input_dict.items():  # pragma: no cover
        net_dict[k1] = v1
    return net_dict
    # to be completed


@pyaedt_function_handler()
def convert_py_list_to_net_list(pylist, list_type=None):
    """Convert a Python list to a Net list.

    Parameters
    ----------
    pylist : list
        Python list to convert.

    Returns
    -------
    list
        List converted to Net.
    """
    if not isinstance(pylist, (list, tuple)):
        pylist = [pylist]
    ls = list([type(item) for item in pylist])
    if len(ls) > 0:
        if list_type:
            net_list = List[list_type]()
        else:
            net_list = List[ls[0]]()
        for el in pylist:
            net_list.Add(el)
        return net_list


@pyaedt_function_handler()
def convert_net_list_to_py_list(netlist):
    """Convert a Net list to a Python list.

    Parameters
    ----------
    netlist : list
       Net list to convert.


    Returns
    -------
    list
        List converted to Python.
    """
    pylist = []
    for el in netlist:
        pylist.__add__(el)
    return pylist


class PadGeometryTpe(Enum):  # pragma: no cover
    Circle = 1
    Square = 2
    Rectangle = 3
    Oval = 4
    Bullet = 5
    NSidedPolygon = 6
    Polygon = 7
    Round45 = 8
    Round90 = 9
    Square45 = 10
    Square90 = 11
    InvalidGeometry = 12


class DielectricExtentType(Enum):
    BoundingBox = 0
    Conforming = 1
    ConvexHull = 2
    Polygon = 3


class BoundaryType(Enum):
    InvalidBoundary = -1
    PortBoundary = 0
    PecBoundary = 1
    RlcBoundary = 2
    kCurrentSource = 3
    kVoltageSource = 4
    kNexximGround = 5
    kNexximPort = 6
    kDcTerminal = 7
    kVoltageProbe = 8


class TerminalType(Enum):
    InvalidTerminal = -1
    EdgeTerminal = 0
    PointTerminal = 1
    TerminalInstanceTerminal = 2
    PadstackInstanceTerminal = 3
    BundleTerminal = 4
    PinGroupTerminal = 5


class Primitives(Enum):
    Rectangle = 0
    Circle = 1
    Polygon = 2
    Path = 3
    Bondwire = 4
    PrimitivePlugin = 5
    Text = 6
    Path3D = 7
    BoardBendDef = 8
    InValidType = 9


class LayoutObjType(Enum):
    InvalidLayoutObj = -1
    Primitive = 0
    PadstackInstance = 1
    Terminal = 2
    TerminalInstance = 3
    CellInstance = 4
    Layer = 5
    Net = 6
    Padstack = 7
    Group = 8
    NetClass = 9
    Cell = 10
    DifferentialPair = 11
    PinGroup = 12
    VoltageRegulator = 13
    ExtendedNet = 14
    LayoutObjTypeCount = 15
