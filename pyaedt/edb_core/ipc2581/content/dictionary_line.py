from pyaedt.edb_core.ipc2581.content.entry_line import EntryLine
from pyaedt.generic.general_methods import ET


class DictionaryLine(object):
    def __init__(self, content):
        self._dict_lines = {}
        self.units = content.units

    @property
    def dict_lines(self):
        return self._dict_lines

    @dict_lines.setter
    def dict_lines(self, value):  # pragma no cover
        if isinstance(value, EntryLine):
            self._dict_lines = value

    def add_line(self, width=None):  # pragma no cover
        if width:
            line = EntryLine()
            line._line_width = width
            if "ROUND_{}".format(width) not in self._dict_lines:
                self._dict_lines["ROUND_{}".format(width)] = line

    def write_xml(self, content=None):  # pragma no cover
        dict_line = ET.SubElement(content, "DictionaryLineDesc")
        dict_line.set("units", self.units)
        for line in list(self._dict_lines.values()):
            line.write_xml(dict_line)
