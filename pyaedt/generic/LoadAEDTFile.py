# -*- coding: utf-8 -*-
import os.path
import re

from pyaedt.generic.general_methods import open_file, settings

# --------------------------------------------------------------------
# public interface


def load_entire_aedt_file(filename):
    """Load the entire AEDT file and return the dictionary

    Parameters
    ----------
    filename :
        AEDT filename with path

    Returns
    -------
    dict
        dictionary containing the decoded AEDT file

    """
    return _load_entire_aedt_file(os.path.normpath(filename))


def load_keyword_in_aedt_file(filename, keyword):
    """Load s specific keyword in the AEDT file and return the dictionary

    Parameters
    ----------
    filename :
        AEDT filename with path
    keyword :
        keyword to search and load

    Returns
    -------
    dict
        dictionary containing the decoded AEDT file

    """
    return _load_keyword_in_aedt_file(filename, keyword)


# --------------------------------------------------------------------
# internals


# precompile all Regular expressions
_remove_quotes = re.compile(r"^'(.*?)'$")
_split_list_elements = re.compile(",(?=(?:[^']*'[^']*')*[^']*$)")
_round_bracket_list = re.compile(r"^(?P<SKEY1>[^\s=]+?)\((?P<LIST1>.+)\)|^'(?P<SKEY2>.+?\s.+)'(?<=')\((?P<LIST2>.+)\)")
_square_bracket_list = re.compile(
    r"^(?P<SKEY1>\S+?)\[\d+:(?P<LIST1>.+)\]|^'(?P<SKEY2>.+?\s.+)'(?<=')\[\d+:(?P<LIST2>.+)\]"
)
_key_parse = re.compile(r"(^'(?P<KEY1>.+?)')(?<=')=(?P<VAL1>.+$)|(?P<KEY2>^.+?)=(?P<VAL2>.+$)")
_value_parse1 = re.compile(r"\s")
_value_parse2 = re.compile(r"^'([^']*\s[^']*)(?=')")
_begin_search = re.compile(r"\$begin '(.+)'")

# set recognized keywords
_recognized_keywords = [
    "CurvesInfo",
    "Sweep Operations",
    "PropDisplayMap",
    "Cells",
    "Active",
    "Rotation",
    "PostProcessingCells",
]
_recognized_subkeys = ["simple(", "IDMap(", "WireSeg(", "PC("]

# global variables
_all_lines = []
_len_all_lines = 0
_count = 0


def _parse_value(v):
    """Parameters
    ----------
    v :


    Returns
    -------

    """
    #  duck typing parse of the value 'v'
    if v is None:
        pv = v
    elif v == "true":
        pv = True
    elif v == "false":
        pv = False
    else:
        try:
            pv = int(v)
        except ValueError:
            try:
                pv = float(v)
            except ValueError:
                m = _remove_quotes.search(v)
                if m:
                    pv = m.group(1)
                else:
                    pv = v
    return pv


def _separate_list_elements(v):
    """Parameters
    ----------
    v :


    Returns
    -------

    """
    if "(" in v or "=" in v:
        l1 = _split_list_elements.split(v)
    else:
        l1 = v.split(",")
    l2 = [_parse_value(i.strip()) for i in l1]
    return l2


def _decode_recognized_subkeys(sk, d):
    """Special decodings for sub-keys belonging to _recognized_subkeys

    Parameters
    ----------
    sk : str
        dictionary sub-key recognized

    d : dict
        Active dictionary.

    Returns
    -------
    bool
        Returns ``True`` if it finds and decodes a recognized value, ``False`` otherwise.

    """
    if sk.startswith(_recognized_subkeys[0]):  # 'simple(' is at the beginning of the value
        m = _round_bracket_list.search(sk)
        if m and m.group("SKEY1") == "simple":  # extra verification. SKEY2 is with spaces, so it's not considered here.
            elems = _separate_list_elements(m.group("LIST1"))
            if elems[0] == "thermal_expansion_coeffcient":
                elems[0] = "thermal_expansion_coefficient"  # fix a typo in the amat files. AEDT supports both strings!
            d[elems[0]] = str(elems[1])  # convert to string as it is dedicated to material props
            return True
    elif re.search(r"^\w+IDMap\(.*\)$", sk, re.IGNORECASE):  # check if the format is AAKeyIDMap('10'=56802, '7'=56803)
        m = re.search(r"^(?P<SKEY>[^\s=]+?)\((?P<LIST>.*)\)", sk)
        if m and "idmap" in m.group("SKEY").lower():  # extra verification.
            k = m.group("SKEY")
            if m.group("LIST"):
                elems = m.group("LIST").split(",")
            else:
                elems = None
            d[k] = elems
            return True
    if sk.startswith(_recognized_subkeys[2]):
        wire_seg_list = [_parse_value(i) for i in sk.lstrip("WireSeg(").rstrip(")").split(", ")]
        if "WireSeg" in d.keys():
            d["WireSeg"].append(wire_seg_list)
        else:
            d["WireSeg"] = []
            d["WireSeg"].append(wire_seg_list)
        return True
    if sk.startswith(_recognized_subkeys[3]):
        pclist = [i for i in sk.lstrip("PC(").rstrip(")").split(", ")]
        if "PC" in d.keys():
            d["PC"].append(pclist)
        else:
            d["PC"] = []
            d["PC"].append(pclist)
        return True
    return False


def _decode_recognized_key(keyword, line, d):
    """Special decodings for keys belonging to _recognized_keywords

    Parameters
    ----------
    keyword : str
        dictionary key recognized

    line : str
        The line following the recognized key

    d : dict
        Active dictionary.

    Returns
    -------
    bool
        Returns ``True`` if it confirms and decodes a recognized key, ``False`` otherwise.

    """
    global _count
    if keyword == _recognized_keywords[0]:  # 'CurvesInfo'
        m = re.search(r"\'(\d+)\'\((.*)\)$", line)
        if m:
            k = m.group(1)
            v = m.group(2)
            v2 = v.replace("\\'", '"')
            v3 = _separate_list_elements(v2)
            d[k] = v3
        else:  # pragma: no cover
            return False
    elif keyword == _recognized_keywords[1]:  # 'Sweep Operations'
        d["add"] = []
        line = _all_lines[_count + 1]
        while line.startswith("add("):
            d["add"].append(line.replace("add", "").translate({ord(i): None for i in " ()'"}).split(","))
            _count += 1
            line = _all_lines[_count + 1]
    elif keyword == _recognized_keywords[2]:  # PropDisplayMap
        pattern = ".+\((.+) Text\((.+) ExtentRect\((.+)\)\)\)"
        match = re.search(pattern, line)
        d["Name"] = []
        for i in match.group(1).split(", "):
            d["Name"].append(_parse_value(i))
        d["Name"].append("Text:=")
        temp_list = []
        for i in match.group(2).split(", "):
            temp_list.append(_parse_value(i))
        temp_list.append("ExtentRect:=")
        temp_list.append([_parse_value(i) for i in match.group(3).split(", ")])
        d["Name"].append(temp_list)
    elif keyword in _recognized_keywords[3:6]:  # Cells, Active, Rotation
        li = _count
        line_m = _all_lines[li]
        li += 1
        line_n = _all_lines[li]
        if line_m[:2] != "m=" or line_n[:2] != "n=":  # pragma: no cover
            return False
        m = int(re.search(r"[m|n]=(\d+)", line_m).group(1))
        d["rows"] = m
        n = int(re.search(r"[m|n]=(\d+)", line_n).group(1))
        d["columns"] = n
        d["matrix"] = []
        for i in range(m):
            li += 1
            r = re.search(r"\$begin 'r(\d+)'", _all_lines[li])
            if not r or i != int(r.group(1)):  # pragma: no cover
                return False  # there should be a row definition
            d["matrix"].append([])
            for _ in range(n):
                li += 1
                c = re.search(r"c\((.+)\)", _all_lines[li])
                if not c:  # pragma: no cover
                    return False  # there should be a column definition
                if keyword == "Cells":
                    c = int(c.group(1))
                elif keyword == "Active":
                    c = c.group(1).lower() == "true"
                elif keyword == "Rotation":
                    c = int(c.group(1)) * 90
                d["matrix"][i].append(c)
            li += 1
            r = re.search(r"\$end 'r(\d+)'", _all_lines[li])
            if not r or i != int(r.group(1)):  # pragma: no cover
                return False  # there should be a row definition
        _count = li
    elif keyword == _recognized_keywords[6]:  # PostProcessingCells
        li = _count
        while _all_lines[li].startswith("OneCell"):
            m = re.search(r"OneCell\((\d+), '(\d+)', '(\d+)'\)", _all_lines[li])
            if m:
                try:
                    d[int(m.group(1))] = [int(m.group(2)), int(m.group(3))]
                except ValueError:  # pragma: no cover
                    continue
            li += 1
        _count = li - 1
    else:  # pragma: no cover
        raise AttributeError("Keyword {} is supposed to be in the recognized_keywords list".format(keyword))
    return True


def _decode_subkey(line, d):
    """Parameters
    ----------
    line : str
        Line.

    d : dict
        Active dictionary.

    -------

    """
    # send recognized sub-keys to _decode_recognized_subkeys (Case insensitive search, detailed search is inside)
    for rsk in _recognized_subkeys:
        if rsk.lower() in line.lower():  # here we simply search if one of the _recognized_subkeys is in line
            if _decode_recognized_subkeys(line, d):  # the exact search is done inside the _decode_recognized_subkeys
                return  # if there is a match we stop the _decode_key, otherwise we keep going

    # create a list for subkey(l1, l2, l3)
    m = _round_bracket_list.search(line)
    if m and m.group("SKEY1"):
        v = _separate_list_elements(m.group("LIST1"))
        k = m.group("SKEY1")
        d[k] = v
        return  # if there is a match we stop the _decode_key, otherwise we keep going
    elif m and m.group("SKEY2"):
        v = _separate_list_elements(m.group("LIST2"))
        k = m.group("SKEY2")
        d[k] = v
        return  # if there is a match we stop the _decode_key, otherwise we keep going

    # create a list for subkey[n: 1, 2, ...n]
    m = _square_bracket_list.search(line)
    if m and m.group("SKEY1"):
        v = _separate_list_elements(m.group("LIST1"))
        k = m.group("SKEY1")
        d[k] = v
        return  # if there is a match we stop the _decode_key, otherwise we keep going
    elif m and m.group("SKEY2"):
        v = _separate_list_elements(m.group("LIST2"))
        k = m.group("SKEY2")
        d[k] = v
        return  # if there is a match we stop the _decode_key, otherwise we keep going

    # search for equal sign
    m = _key_parse.search(line)
    if m and m.group("KEY1"):  # key btw ''
        v = m.group("VAL1")
        if "\\'" in v:
            v2 = v.replace("\\'", '"')
        else:
            v2 = v
        # if there are no spaces in value   or   values with spaces are between quotes
        if not _value_parse1.search(v2) or _value_parse2.search(v2):
            k = m.group("KEY1")
            d[k] = _parse_value(v)
        else:  # spaces in value without quotes
            k = line  # save the line as a whole
            d[k] = None
    elif m and m.group("KEY2"):  # key without ''
        v = m.group("VAL2")
        if "\\'" in v:
            v2 = v.replace("\\'", '"')
        else:
            v2 = v
        # if there are no spaces in value   or   values with spaces are between quotes
        if not _value_parse1.search(v2) or _value_parse2.search(v2):
            k = m.group("KEY2")
            d[k] = _parse_value(v)
        else:  # spaces in value without quotes
            k = line  # save the line as a whole
            d[k] = None
    else:  # no = sign found
        k = line  # save the line as a whole
        d[k] = None


def _walk_through_structure(keyword, save_dict):
    """Parameters
    ----------
    keyword :

    save_dict :


    Returns
    -------

    """
    global _count
    begin_key = "$begin '{}'".format(keyword)
    end_key = "$end '{}'".format(keyword)
    found = False
    saved_value = None
    while _count < _len_all_lines:
        line = _all_lines[_count]
        # begin_key is found
        if begin_key == line:
            found = True
            saved_value = save_dict.get(keyword)  # if the keyword is already present, save it
            save_dict[keyword] = {}
            _count += 1
            continue
        # end_key is found
        if end_key == line:
            break
        # between begin_key and end_key
        if found:
            b = _begin_search.search(line)
            if b:  # walk down a level
                nextlvl_begin_key = b.group(1)
                _walk_through_structure(nextlvl_begin_key, save_dict[keyword])
            elif keyword in _recognized_keywords:
                confirmed = _decode_recognized_key(keyword, line, save_dict[keyword])
                if not confirmed:  # pragma: no cover
                    # decode the line normally, since recognized key is not successful
                    _decode_subkey(line, save_dict[keyword])
            else:  # decode key
                _decode_subkey(line, save_dict[keyword])
        _count += 1
    # recompose value if list
    if saved_value:
        # makes the value a list, if it's not already
        if type(saved_value) is not list:
            saved_value = [saved_value]
        saved_value.append(save_dict[keyword])
        save_dict[keyword] = saved_value
    return _count


def _read_aedt_file(filename):
    """Read the entire AEDT file discard binary and put ascii line in a list

    Parameters
    ----------
    filename :
        AEDT filename with path

    Returns
    -------

    """
    global _all_lines
    global _len_all_lines
    global _count

    # read the AEDT file
    with open_file(filename, "rb") as aedt_fh:
        raw_lines = aedt_fh.read().splitlines()
    ascii_lines = []
    for raw_line in raw_lines:
        try:
            ascii_lines.append(raw_line.decode("utf-8").lstrip(" \t"))
        except UnicodeDecodeError:
            continue
    ascii_content = "\n".join(ascii_lines)
    # combine subsequent lines when the line ends in \
    _all_lines = ascii_content.replace("\\\n", "").splitlines()
    _len_all_lines = len(_all_lines)
    _count = 0


def _load_entire_aedt_file(filename):
    """Load the entire AEDT file and return the dictionary

    Parameters
    ----------
    filename :
        AEDT filename with path

    Returns
    -------
    type
        dictionary containing the decoded AEDT file

    """
    global _count
    _read_aedt_file(filename)
    main_dict = {}
    # load the aedt file
    while _count < _len_all_lines:
        line = _all_lines[_count]
        m = _begin_search.search(line)
        if m:
            _walk_through_structure(m.group(1), main_dict)
        _count += 1
    if settings.aedt_version and settings.aedt_version > "2022.2":
        project_preview = load_keyword_in_aedt_file(filename, "ProjectPreview")
        if project_preview and "ProjectPreview" in project_preview:
            main_dict["ProjectPreview"] = project_preview["ProjectPreview"]
    return main_dict


def _load_keyword_in_aedt_file(filename, keyword):
    """Load a specific keyword in the AEDT file and return the dictionary

    Parameters
    ----------
    filename :
        AEDT filename with path
    keyword :
        keyword to search and load

    Returns
    -------
    type
        dictionary containing the decoded AEDT file

    """
    _read_aedt_file(filename)
    # load the aedt file
    main_dict = {}
    _walk_through_structure(keyword, main_dict)
    return main_dict
