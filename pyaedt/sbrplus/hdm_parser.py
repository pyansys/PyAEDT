import struct
import warnings

try:
    from enum import Enum
except ImportError:
    pass

try:
    import numpy as np
except ImportError:
    warnings.warn(
        "The NumPy module is required to run some functionalities of PostProcess.\n"
        "Install with \n\npip install numpy\n\nRequires CPython."
    )


class Parser:
    """Parser class that loads an HDM-format export file from HFSS SBR+, interprets
    its header and its binary content. Except for the header, the binary content is
    not parsed until an explicit call to parse_message.
    Usage:
    parser = Parser('filename')
    bundle = parser.parse_message()
    """

    def __init__(self, filename):
        """Initializes parser object with the interpreted header and a pointer to the binary data."""
        self.parser_types = {}
        self.parser_flags = {}
        self.parser_enums = {}
        self.objects = {}
        self.idx = 0
        with open(filename, "rb") as file:
            binarycontent = file.read(-1)
        header, binarycontent = binarycontent.split(b"#header end\n")
        header = header.decode().splitlines()[1:]
        header = [line for line in header if not line.startswith("#")]
        self.header = eval(" ".join(header))
        self._read_header()
        self.binarycontent = binarycontent

    def parse_message(self):
        """Parses the binary content of the HDM file."""
        return self._parse(self.message["type"])

    def _parse(self, type_name):
        """Generic parser method, dispatches to specialized ones."""
        if self.parser_types[type_name]["type"] == "object":
            return self._parse_object(type_name)
        elif self.parser_types[type_name]["type"] == "internal":
            return self._parse_simple_base_type(**self.parser_types[type_name]["args"])
        else:
            return self._parse_list(**self.parser_types[type_name])

    def _parse_simple_base_type(self, format="i", size=4, how_many=1, final_type=None):
        """Parser for int, float, complex, enum or flag.
        Can also parse a list of base types and convert them to another type if possible.
        """
        end = self.idx + how_many * size
        if how_many == 1:
            res = [
                x[0]
                for x in struct.iter_unpack("".join(["<", str(how_many), format]), self.binarycontent[self.idx : end])
            ]
            res = res[0]
            if final_type:
                res = final_type(res)
        else:
            res = [
                x[0:how_many]
                for x in struct.iter_unpack("".join(["<", str(how_many), format]), self.binarycontent[self.idx : end])
            ]
            res = res[0]
            if final_type:
                if final_type is complex:
                    res = [complex(*res[i : i + 2]) for i in range(0, len(res), 2)]
                else:
                    res = [final_type(*i) for i in res]
            if len(res) == 1:
                res = res[0]
        self.idx = end
        return res

    def _parse_list(self, type=None, base=None, size=1):
        """Parser for vector or list. 'vector's are to be interpreted in the linear algebra sense,
        and converted to numpy.array. 'list's are Python lists. Only simple base types can be
        interpreted as a numpy array
        """
        assert base != None
        res = []
        bt = self.parser_types[base]

        if bt["type"] == "internal":
            args = bt["args"]
            final_type = args["final_type"] if "final_type" in args else None
            res = self._parse_simple_base_type(
                format=args["format"], size=args["size"], how_many=size * args["how_many"], final_type=final_type
            )
            if not isinstance(res, tuple) and not isinstance(res, list):
                res = [
                    res,
                ]
            if type == "vector":
                res = np.array(res)
        else:
            res = [self._parse(base) for iel in range(size)]

        if len(res) == 1:
            return res[0]
        else:
            return res

    def _parse_object(self, name):
        """Parser for an object message"""
        namesdict = {}
        for l in self.parser_types[name]["layout"]:
            type_to_parse = l["type"]
            fields = l["field_names"]
            if isinstance(fields, str):
                fields = (fields,)

            # Decide if a field needs to be parsed based on the optional data structure
            optional = False
            if "optional" in l:
                var, cond = l["optional"]
                if isinstance(namesdict[var], Enum):
                    optional = namesdict[var].name != cond
                else:
                    optional = namesdict[var][cond] is False

            for field in fields:
                if optional:
                    # Skip parsing optional fields
                    namesdict[field] = None
                elif type_to_parse in ("vector", "list"):
                    # Parse explicit vectors or lists in the layout and convert the size to a number if it's a string
                    if isinstance(l["size"], str):
                        namesdict[field] = self._parse_list(type=l["type"], base=l["base"], size=namesdict[l["size"]])
                    else:
                        namesdict[field] = self._parse_list(type=l["type"], base=l["base"], size=l["size"])
                else:
                    # Parse anything else that is not explicitly a list or a vector. In this case, the field type
                    # could be a custom type referring indirectly to a list or vector, so handle that directly for
                    # efficiency
                    if self.parser_types[type_to_parse]["type"] in ("vector", "list"):
                        arrtype = self.parser_types[type_to_parse]["type"]
                        arrbase = self.parser_types[type_to_parse]["base"]
                        arrsize = self.parser_types[type_to_parse]["size"]
                        if isinstance(arrsize, str):
                            arrsize = namesdict[self.parser_types[type_to_parse]["size"]]
                        namesdict[field] = self._parse_list(type=arrtype, base=arrbase, size=arrsize)
                    elif type_to_parse in self.parser_flags:
                        flag_value = self._parse(type_to_parse)
                        flag_type = self.parser_flags[type_to_parse]
                        namesdict[field] = {k: bool(flag_value & v) for k, v in flag_type.items()}
                    else:
                        namesdict[field] = self._parse(type_to_parse)

        return self.objects[name](namesdict)

    def _read_header(self):
        """Parses the header and prepares all data structures to interpret the binary content."""

        def build_type(self, key, val):
            type_i = val["type"]
            result = {}
            if type_i in ["int", "flag", "enum"]:
                final_type = None
                if type_i == "flag":
                    self.parser_flags[key] = dict([(k, 1 << v) for k, v in val["values"].items()])
                    # final_type = self.parser_flags[key]
                elif type_i == "enum":
                    self.parser_enums[key] = Enum(key, val["values"], start=val["start"])
                    final_type = self.parser_enums[key]
                format_i = {1: "B", 2: "h", 4: "i"}
                result = {
                    "type": "internal",
                    "args": {
                        "format": format_i[val["size"]],
                        "how_many": 1,
                        "size": val["size"],
                        "final_type": final_type,
                    },
                }
            elif type_i == "float":
                format_i = {4: "f", 8: "d"}
                result = {
                    "type": "internal",
                    "args": {"format": format_i[val["size"]], "how_many": 1, "size": val["size"]},
                }
            elif type_i == "complex":
                format_i = {8: "f", 16: "d"}
                result = {
                    "type": "internal",
                    "args": {
                        "format": format_i[val["size"]],
                        "how_many": 2,
                        "size": val["size"] // 2,
                        "final_type": complex,
                    },
                }
            elif type_i == "vector" or type_i == "list":
                result = val
            elif type_i == "object":
                result = val

                class NewClass:
                    __qualname__ = key
                    __name__ = key

                    def __init__(self, dictionary):
                        for k, v in dictionary.items():
                            setattr(self, k, v)

                self.objects[key] = NewClass

            return result

        for key, val in self.header["types"].items():
            self.parser_types[key] = build_type(self, key, val)
        self.message = self.header["message"]

    def __repr__(self):
        return repr(self.parser_types)
