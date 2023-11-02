# -*- coding: utf-8 -*-
from collections import OrderedDict
from decimal import Decimal
import json
import math
import random
import re
import string

from pyaedt.generic.general_methods import pyaedt_function_handler, settings
from pyaedt.modeler.cad.elements3d import EdgePrimitive, FacePrimitive, VertexPrimitive


@pyaedt_function_handler()
def _tuple2dict(t, d):
    """Parameters
    ----------
    t :

    d :


    Returns
    -------

    """
    k = t[0]
    v = t[1]
    if isinstance(v, list) and len(t) > 2:
        d[k] = v
    elif isinstance(v, list) and len(t) == 2 and not v:
        d[k] = None
    elif (
        isinstance(v, list) and isinstance(v[0], tuple) and len(t) == 2
    ):  # len check is to avoid expanding the list with a 3rd element=None
        if k in d:
            if not isinstance(d[k], list):
                d[k] = [d[k]]
            d1 = OrderedDict()
            for tt in v:
                _tuple2dict(tt, d1)
            d[k].append(d1)
        else:
            d[k] = OrderedDict()
            for tt in v:
                _tuple2dict(tt, d[k])
    else:
        d[k] = v


@pyaedt_function_handler()
def _dict2arg(d, arg_out):
    """Create a valid string of name-value pairs for the native AEDT API.

    Prepend the argument string in `arg_out` using the dictionary ``d``
    to create a valid input string as an argument for the native AEDT API.

    Parameters
    ----------
    d : dict
        Dictionary to use for prepending to the argument string being built
        for the native AEDT API.

    arg_out : str.
        String of the name/value pair to be built as an argument
        for the native AEDT API.

    """
    for k, v in d.items():
        if "_pyaedt" in k:
            continue
        if k == "Point" or k == "DimUnits":
            if isinstance(v[0], (list, tuple)):
                for e in v:
                    arg = ["NAME:" + k, e[0], e[1]]
                    arg_out.append(arg)
            else:
                arg = ["NAME:" + k, v[0], v[1]]
                arg_out.append(arg)
        elif k == "Range":
            if isinstance(v[0], (list, tuple)):
                for e in v:
                    arg_out.append(k + ":=")
                    arg_out.append([i for i in e])
            else:
                arg_out.append(k + ":=")
                arg_out.append([i for i in v])
        elif isinstance(v, (OrderedDict, dict)):
            arg = ["NAME:" + k]
            _dict2arg(v, arg)
            arg_out.append(arg)
        elif v is None:
            arg_out.append(["NAME:" + k])
        elif type(v) is list and len(v) > 0 and isinstance(v[0], (OrderedDict, dict)):
            for el in v:
                arg = ["NAME:" + k]
                _dict2arg(el, arg)
                arg_out.append(arg)

        else:
            arg_out.append(k + ":=")
            if type(v) is EdgePrimitive or type(v) is FacePrimitive or type(v) is VertexPrimitive:
                arg_out.append(v.id)
            else:
                arg_out.append(v)


@pyaedt_function_handler()
def _arg2dict(arg, dict_out):
    if arg[0] == "NAME:DimUnits" or "NAME:Point" in arg[0]:
        if arg[0][5:] in dict_out:
            if isinstance(dict_out[arg[0][5:]][0], (list, tuple)):
                dict_out[arg[0][5:]].append(list(arg[1:]))
            else:
                dict_out[arg[0][5:]] = [dict_out[arg[0][5:]]]
                dict_out[arg[0][5:]].append(list(arg[1:]))
        else:
            dict_out[arg[0][5:]] = list(arg[1:])
    elif arg[0][:5] == "NAME:":
        top_key = arg[0][5:]
        dict_in = OrderedDict()
        i = 1
        while i < len(arg):
            if arg[i][0][:5] == "NAME:" and (
                isinstance(arg[i], (list, tuple)) or str(type(arg[i])) == r"<type 'List'>"
            ):
                _arg2dict(list(arg[i]), dict_in)
                i += 1
            elif arg[i][-2:] == ":=":
                if str(type(arg[i + 1])) == r"<type 'List'>":
                    if arg[i][:-2] in dict_in:
                        dict_in[arg[i][:-2]].append(list(arg[i + 1]))
                    else:
                        dict_in[arg[i][:-2]] = list(arg[i + 1])
                else:
                    if arg[i][:-2] in dict_in:
                        if isinstance(dict_in[arg[i][:-2]], list):
                            dict_in[arg[i][:-2]].append(arg[i + 1])
                        else:
                            dict_in[arg[i][:-2]] = [dict_in[arg[i][:-2]]]
                            dict_in[arg[i][:-2]].append(arg[i + 1])
                    else:
                        dict_in[arg[i][:-2]] = arg[i + 1]

                i += 2
            else:
                raise ValueError("Incorrect data argument format")
        if top_key in dict_out:
            if isinstance(dict_out[top_key], list):
                dict_out[top_key].append(dict_in)
            else:
                dict_out[top_key] = [dict_out[top_key], dict_in]
        else:
            dict_out[top_key] = dict_in
    else:
        raise ValueError("Incorrect data argument format")


@pyaedt_function_handler()
def create_list_for_csharp(input_list, return_strings=False):
    """Parameters
    ----------
    input_list :

    return_strings :
         (Default value = False)

    Returns
    -------

    """
    from pyaedt.generic.clr_module import Double, List

    if return_strings:
        col = List[str]()
    else:
        col = List[Double]()

    for el in input_list:
        if return_strings:
            col.Add(str(el))
        else:
            col.Add(el)
    return col


@pyaedt_function_handler()
def create_table_for_csharp(input_list_of_list, return_strings=True):
    """Parameters
    ----------
    input_list_of_list :

    return_strings :
         (Default value = True)

    Returns
    -------

    """
    from pyaedt.generic.clr_module import List

    new_table = List[List[str]]()
    for col in input_list_of_list:
        newcol = create_list_for_csharp(col, return_strings)
        new_table.Add(newcol)
    return new_table


@pyaedt_function_handler()
def format_decimals(el):
    """Parameters
    ----------
    el :


    Returns
    -------

    """
    if float(el) > 1000:
        num = "{:,.0f}".format(Decimal(el))
    elif float(el) > 1:
        num = "{:,.3f}".format(Decimal(el))
    else:
        num = "{:.3E}".format(Decimal(el))
    return num


@pyaedt_function_handler()
def random_string(length=6, only_digits=False, char_set=None):
    """Generate a random string

    Parameters
    ----------
    length :
        length of the random string (Default value = 6)
    only_digits : bool, optional
        ``True`` if only digits are to be included.
    char_set : str, optional
        Custom character set to pick the characters from.  By default chooses from
        ASCII and digit characters or just digits if ``only_digits`` is ``True``.

    Returns
    -------
    type
        random string

    """
    if not char_set:
        if only_digits:
            char_set = string.digits
        else:
            char_set = string.ascii_uppercase + string.digits
    random_str = "".join(random.choice(char_set) for _ in range(int(length)))
    return random_str


@pyaedt_function_handler()
def unique_string_list(element_list, only_string=True):
    """Return a unique list of strings from an element list.

    Parameters
    ----------
    element_list :

    only_string :
         (Default value = True)

    Returns
    -------

    """
    if element_list:
        if isinstance(element_list, list):
            element_list = set(element_list)
        elif isinstance(element_list, str):
            element_list = [element_list]
        else:
            error_message = "Invalid list data"
            try:
                error_message += " {}".format(element_list)
            except:
                pass
            raise Exception(error_message)

        if only_string:
            non_string_entries = [x for x in element_list if type(x) is not str]
            assert not non_string_entries, "Invalid list entries {} are not a string!".format(non_string_entries)

    return element_list


@pyaedt_function_handler()
def string_list(element_list):
    """Parameters
    ----------
    element_list :


    Returns
    -------

    """
    if isinstance(element_list, str):
        element_list = [element_list]
    else:
        assert isinstance(element_list, str), "Input must be a list or a string"
    return element_list


@pyaedt_function_handler()
def ensure_list(element_list):
    """Parameters
    ----------
    element_list :


    Returns
    -------

    """
    if not isinstance(element_list, list):
        element_list = [element_list]
    return element_list


@pyaedt_function_handler()
def variation_string_to_dict(variation_string, separator="="):
    """Helper function to convert a list of "="-separated strings into a dictionary

    Returns
    -------
    dict
    """
    var_data = variation_string.split()
    variation_dict = {}
    for var in var_data:
        pos_eq = var.find("=")
        var_name = var[0:pos_eq]
        var_value = var[pos_eq + 1 :].replace("'", "")
        variation_dict[var_name] = var_value
    return variation_dict


RKM_MAPS = {
    # Resistors
    "L": "m",
    "R": "",
    "E": "",
    "k": "k",
    "K": "k",
    "M": "M",
    "G": "G",
    "T": "T",
    "f": "f",
    # Capacitors/Inductors
    "F": "",
    "H": "",
    "h": "",
    "m": "m",
    "u": "μ",
    "μ": "μ",
    "U": "μ",
    "n": "n",
    "N": "n",
    "p": "p",
    "P": "p",
    "mF": "m",
    "uF": "μ",
    "μF": "μ",
    "UF": "μ",
    "nF": "n",
    "NF": "n",
    "pF": "p",
    "PF": "p",
    "mH": "m",
    "uH": "μ",
    "μH": "μ",
    "UH": "μ",
    "nH": "n",
    "NH": "n",
    "pH": "p",
    "PH": "p",
}
AEDT_MAPS = {"μ": "u"}


@pyaedt_function_handler()
def from_rkm(code):
    """Convert an RKM code string to a string with a decimal point.

    Parameters
    ----------
    code : str
        RKM code string.

    Returns
    -------
    str
        String with a decimal point and an R value.

    Examples
    --------
    >>> from pyaedt.generic.DataHandlers import from_rkm
    >>> from_rkm('R47')
    '0.47'

    >>> from_rkm('4R7')
    '4.7'

    >>> from_rkm('470R')
    '470'

    >>> from_rkm('4K7')
    '4.7k'

    >>> from_rkm('47K')
    '47k'

    >>> from_rkm('47K3')
    '47.3k'

    >>> from_rkm('470K')
    '470k'

    >>> from_rkm('4M7')
    '4.7M'

    """
    # Matches RKM codes that start with a digit.
    # fd_pattern = r'([0-9]+)([LREkKMGTFmuµUnNpP]+)([0-9]*)'
    fd_pattern = r"([0-9]+)([{}]+)([0-9]*)".format(
        "".join(RKM_MAPS.keys()),
    )
    # matches rkm codes that end with a digit
    # ld_pattern = r'([0-9]*)([LREkKMGTFmuµUnNpP]+)([0-9]+)'
    ld_pattern = r"([0-9]*)([{}]+)([0-9]+)".format("".join(RKM_MAPS.keys()))

    fd_regex = re.compile(fd_pattern, re.I)
    ld_regex = re.compile(ld_pattern, re.I)

    for regex in [fd_regex, ld_regex]:
        m = regex.match(code)
        if m:
            fd, base, ld = m.groups()
            ps = RKM_MAPS[base]

            if ld:
                return_str = "".join([fd, ".", ld, ps])
            else:
                return_str = "".join([fd, ps])
            return return_str
    return code


@pyaedt_function_handler()
def to_aedt(code):
    """Parameters
    ----------
    code : str

    Returns
    -------
    str

    """
    pattern = r"([{}]{})".format("".join(AEDT_MAPS.keys()), "{1}")
    regex = re.compile(pattern, re.I)
    return_code = regex.sub(lambda m: AEDT_MAPS.get(m.group(), m.group()), code)
    return return_code


def str_to_bool(s):
    """Convert a ``"True"`` or ``"False"`` string to its corresponding Boolean value.

    If the passed arguments are not relevant in the context of conversion, the argument
    itself is returned. This method can be called using the ``map()`` function to
    ensure conversion of Boolean strings in a list.

    Parameters
    ----------
    s: str

    Returns
    -------
    bool or str
         The method is not case-sensitive.
         - ``True`` is returned  if the input is ``"true"``, ``"1"``,
           `"yes"``, or ``"y"``,
         - ``False`` is returned if the input is ``"false"``, ``"no"``,
           ``"n``,  or ``"0"``.
         - Otherwise, the input value is passed through the method unchanged.

    """
    if type(s) == str:
        if s.lower() in ["true", "yes", "y", "1"]:
            return True
        elif s.lower() in ["false", "no", "n", "0"]:
            return False
        else:
            return s
    elif type(s) == int:
        return False if s == 0 else True


@pyaedt_function_handler()
def from_rkm_to_aedt(code):
    """Parameters
    ----------
    code : str


    Returns
    -------
    str

    """
    return to_aedt(from_rkm(code))


unit_val = {
    "": 1.0,
    "uV": 1e-6,
    "mV": 1e-3,
    "V": 1.0,
    "kV": 1e3,
    "MegV": 1e6,
    "ns": 1e-9,
    "us": 1e-6,
    "ms": 1e-3,
    "s": 1.0,
    "min": 60,
    "hour": 3600,
    "rad": 1.0,
    "deg": math.pi / 180,
    "Hz": 1.0,
    "kHz": 1e3,
    "MHz": 1e6,
    "nm": 1e-9,
    "um": 1e-6,
    "mm": 1e-3,
    "in": 0.0254,
    "inches": 0.0254,
    "mil": 2.54e-5,
    "cm": 1e-2,
    "dm": 1e-1,
    "meter": 1.0,
    "km": 1e3,
}
resynch_maxwell2D_control_program_for_design = """
from pyaedt.desktop import Desktop
from pyaedt.maxwell import Maxwell2d
design_name = os.getenv('design')
setup = os.getenv('setup')

with Desktop() as d:
    maxwell_2d = Maxwell2d(designname=design_name, setup_name=setup)
    maxwell_2d.setup_ctrlprog(keep_modifications=True )
    d.logger.info("Successfully updated project definitions")
    maxwell_2d.save_project()
"""


@pyaedt_function_handler()
def float_units(val_str, units=""):
    """Retrieve units for a value.

    Parameters
    ----------
    val_str : str
        Name of the float value.

    units : str, optional
         The default is ``""``.

    Returns
    -------

    """
    if units not in unit_val:
        raise Exception("Specified unit string " + units + " not known!")

    loc = re.search("[a-zA-Z]", val_str)
    try:
        b = loc.span()[0]
        var = [float(val_str[0:b]), val_str[b:]]
        val = var[0] * unit_val[var[1]]
    except:
        val = float(val_str)

    val = val / unit_val[units]
    return val


@pyaedt_function_handler()
def json_to_dict(fn):
    """Load Json File to a dictionary.

    Parameters
    ----------
    fn : str
        json file full path.

    Returns
    -------
    dict
    """
    json_data = {}
    with open(fn) as json_file:
        try:
            json_data = json.load(json_file)
        except json.JSONDecodeError as e:  # pragma: no cover
            error = "Error reading json: {} at line {}".format(e.msg, e.lineno)
            settings.logger.error(error)
    return json_data
