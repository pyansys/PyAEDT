import json
import logging
import os
import re
import traceback

import pyaedt
from pyaedt import settings
from pyaedt.generic.general_methods import check_and_download_file, check_if_path_exists

logger = logging.getLogger(__name__)


class Component:
    """Component extracted from ibis model."""

    def __init__(self):
        self._name = None
        self._manufacturer = None
        self._pins = {}

    @property
    def name(self):
        """Name of the component.

        Examples
        --------
        >>> ibis = ibis_reader.IbisReader(os.path.join(path_to_ibis_files, "u26a_800_modified.ibs"), circuit)
        >>> ibis.components["MT47H64M4BP-3_25"].name
        'MT47H64M4BP-3_25'

        """
        return self._name

    @name.setter
    def name(self, value):
        self._name = value

    @property
    def manufacturer(self):
        """Manufacturer of the component.

        Examples
        --------
        >>> ibis = ibis_reader.IbisReader(os.path.join(path_to_ibis_files, 'u26a_800_modified.ibs'), circuit)
        >>> ibis.components["MT47H64M4BP-3_25"].manufacturer
        'Micron Technology, Inc.'

        """
        return self._manufacturer

    @manufacturer.setter
    def manufacturer(self, value):
        self._manufacturer = value

    @property
    def pins(self):
        """Pins of the component.

        Examples
        --------
        >>> ibis = ibis_reader.IbisReader(os.path.join(path_to_ibis_files, "u26a_800_modified.ibs"), circuit)
        >>> pins = ibis.components["MT47H64M4BP-3_25"].pins

        """
        return self._pins

    @pins.setter
    def pins(self, value):
        self._pins = value


class Pin:
    """Pin from a component with all its data feature.

    Parameters
    ----------
    name : str
        Name of the pin.
    circuit : class:`pyaedt.circuit.Circuit`
        Circuit in which the pin will be added to.
    """

    def __init__(self, name, buffername, circuit):
        self._name = name
        self._buffer_name = buffername
        self._circuit = circuit
        self._short_name = None
        self._signal = None
        self._model = None
        self._r_value = None
        self._l_value = None
        self._c_value = None

    @property
    def name(self):
        """Full name of the pin including the component name and the ibis filename.

        Examples
        --------
        >>> ibis = ibis_reader.IbisReader(os.path.join(path_to_ibis_files, "u26a_800_modified.ibs"), circuit)
        >>> ibis.components["MT47H64M4BP-3_25"].pins["A1_MT47H64M4BP-3_25_u26a_800"].name
        'A1_MT47H64M4BP-3_25_u26a_800'

        """
        return self._name

    @property
    def buffer_name(self):
        """Full name of the buffer including the component name and the ibis filename."""
        return self._buffer_name

    @property
    def short_name(self):
        """Name of the pin without the name of the component.

        Examples
        --------
        >>> ibis = ibis_reader.IbisReader(os.path.join(path_to_ibis_files, "u26a_800_modified.ibs"), circuit)
        >>> ibis.components["MT47H64M4BP-3_25"].pins["A1_MT47H64M4BP-3_25_u26a_800"].short_name
        'A1'

        """
        return self._short_name

    @short_name.setter
    def short_name(self, value):
        self._short_name = value

    @property
    def signal(self):
        """Signal of the pin.

        Examples
        --------
        >>> ibis = ibis_reader.IbisReader(os.path.join(path_to_ibis_files, "u26a_800_modified.ibs"), circuit)
        >>> ibis.components["MT47H64M4BP-3_25"].pins["A1_MT47H64M4BP-3_25_u26a_800"].signal
        'VDD'

        """
        return self._signal

    @signal.setter
    def signal(self, value):
        self._signal = value

    @property
    def model(self):
        """Model of the pin.

        Examples
        --------
        >>> ibis = ibis_reader.IbisReader(os.path.join(path_to_ibis_files, "u26a_800_modified.ibs"), circuit)
        >>> ibis.components["MT47H64M4BP-3_25"].pins["A1_MT47H64M4BP-3_25_u26a_800"].signal
        'POWER'

        """
        return self._model

    @model.setter
    def model(self, value):
        self._model = value

    @property
    def r_value(self):
        """Resistance value in ohms.

        Examples
        --------
        >>> ibis = ibis_reader.IbisReader(os.path.join(path_to_ibis_files, "u26a_800_modified.ibs"), circuit)
        >>> ibis.components["MT47H64M4BP-3_25"].pins["A1_MT47H64M4BP-3_25_u26a_800"].r_value
        '44.3m'

        """
        return self._r_value

    @r_value.setter
    def r_value(self, value):
        self._r_value = value

    @property
    def l_value(self):
        """Inductance value in H.

        Examples
        --------
        >>> ibis = ibis_reader.IbisReader(os.path.join(path_to_ibis_files, "u26a_800_modified.ibs"), circuit)
        >>> ibis.components["MT47H64M4BP-3_25"].pins["A1_MT47H64M4BP-3_25_u26a_800"].l_value
        '1.99nH'

        """
        return self._l_value

    @l_value.setter
    def l_value(self, value):
        self._l_value = value

    @property
    def c_value(self):
        """Capacitance value in F.

        Examples
        --------
        >>> ibis = ibis_reader.IbisReader(os.path.join(path_to_ibis_files, "u26a_800_modified.ibs"), circuit)
        >>> ibis.components["MT47H64M4BP-3_25"].pins["A1_MT47H64M4BP-3_25_u26a_800"].c_value
        '0.59pF'

        """
        return self._c_value

    @c_value.setter
    def c_value(self, value):
        self._c_value = value

    def add(self):
        """Add a pin to the list of components in the Project Manager."""
        try:
            return self._circuit.modeler.schematic.o_component_manager.AddSolverOnDemandModel(
                self.buffer_name,
                [
                    "NAME:CosimDefinition",
                    "CosimulatorType:=",
                    7,
                    "CosimDefName:=",
                    "DefaultIBISNetlist",
                    "IsDefinition:=",
                    True,
                    "Connect:=",
                    True,
                    "Data:=",
                    [],
                    "GRef:=",
                    [],
                ],
            )
        except:
            logger.error("Error adding {} pin component.".format(self.short_name))
            return False

    def insert(self, x, y, angle=0.0):
        """Insert a pin at a defined location inside the graphical window.

        Parameters
        ----------
        x : float
            X position of the pin.
        y : float
            Y position of the pin.
        angle : float, optional
            Angle of the pin. The default value is ``"0.0"``.

        Returns
        -------
        :class:`pyaedt.modeler.Object3d.CircuitComponent`
            Circuit Component Object.

        """
        return self._circuit.modeler.schematic.create_component(
            component_library=None,
            component_name=self.buffer_name,
            location=[x, y],
            angle=angle,
        )


class Buffer:
    def __init__(self, ibis_name, short_name, circuit):
        self._ibis_name = ibis_name
        self._short_name = short_name
        self._circuit = circuit

    @property
    def name(self):
        """Full name of the buffer including the ibis filename."""
        return "{}_{}".format(self.short_name, self._ibis_name)

    @property
    def short_name(self):
        """Short name of the buffer without the ibis filename included."""
        return self._short_name

    def add(self):
        """Add a buffer to the list of components in the Project Manager."""
        self._circuit.modeler.schematic.o_component_manager.AddSolverOnDemandModel(
            self.name,
            [
                "NAME:CosimDefinition",
                "CosimulatorType:=",
                7,
                "CosimDefName:=",
                "DefaultIBISNetlist",
                "IsDefinition:=",
                True,
                "Connect:=",
                True,
                "Data:=",
                [],
                "GRef:=",
                [],
            ],
        )

    def insert(self, x, y, angle=0.0):
        """Insert a buffer at a defined location inside the graphical window.

        Parameters
        ----------
        x : float
            X position of the buffer.
        y : float
            Y position of the buffer.
        angle : float, optional
            Angle of the buffer. The default value is ``"0.0"``.

        Returns
        -------
        :class:`pyaedt.modeler.Object3d.CircuitComponent`
            Circuit Component Object.

        """
        return self._circuit.modeler.schematic.create_component(
            component_library=None,
            component_name=self.name,
            location=[x, y],
            angle=angle,
        )


class ModelSelector:
    def __init__(self):
        self._model_selector_items = []
        self._name = None

    @property
    def model_selector_items(self):
        """Model selector items."""
        return self._model_selector_items

    @model_selector_items.setter
    def model_selector_items(self, value):
        self._model_selector_items = value

    @property
    def name(self):
        """Name of the model selector."""
        return self._name

    @name.setter
    def name(self, value):
        self._name = value


class ModelSelectorItem:
    def __init__(self):
        self._description = []
        self._name = None

    @property
    def description(self):
        """Description of the item."""
        return self._description

    @description.setter
    def description(self, value):
        self._description = value

    @property
    def name(self):
        """Name of the item."""
        return self._name

    @name.setter
    def name(self, value):
        self._name = value


class Model:
    def __init__(self):
        self._description = []
        self._name = None
        self._clamp = None
        self._enable = None
        self._ami = None
        self._c_comp = None

    @property
    def name(self):
        """Name of the item."""
        return self._name

    @name.setter
    def name(self, value):
        self._name = value

    @property
    def model_type(self):
        """Type of the model."""
        return self._model_type

    @model_type.setter
    def model_type(self, value):
        self._model_type = value

    @property
    def clamp(self):
        """Clamp."""
        return self._clamp

    @clamp.setter
    def clamp(self, value):
        self._clamp = value

    @property
    def enable(self):
        """Is model enabled or not."""
        return self._enable

    @enable.setter
    def enable(self, value):
        self._enable = value

    @property
    def ami(self):
        """Is model enabled or not."""
        return self._ami

    @ami.setter
    def ami(self, value):
        self._ami = value

    @property
    def c_comp(self):
        """Is model enabled or not."""
        return self._c_comp

    @c_comp.setter
    def c_comp(self, value):
        self._c_comp = value


class Ibis:
    """Ibis model with all data extracted: name, components, models.

    Parameters
    ----------
    name : str
        Name of ibis model.
    circuit : class:`pyaedt.circuit.Circuit`
        Circuit in which the ibis components will be used.
    """

    # Ibis reader must work independently or in Circuit.
    def __init__(self, name, circuit):
        self.circuit = circuit
        self._name = name
        self._components = {}
        self._model_selectors = []
        self._models = []

    @property
    def name(self):
        """Name of the ibis model."""
        return self._name

    @property
    def components(self):
        """List of all components included in the ibis file."""
        return self._components

    @components.setter
    def components(self, value):
        self._components = value

    @property
    def model_selectors(self):
        """List of all model selectors included in the ibis file."""
        return self._model_selectors

    @model_selectors.setter
    def model_selectors(self, value):
        self._model_selectors = value

    @property
    def models(self):
        """List of all models included in the ibis file."""
        return self._models

    @models.setter
    def models(self, value):
        self._models = value

    @property
    def buffers(self):
        """Buffers included into the ibis model."""
        return self._buffers

    @buffers.setter
    def buffers(self, value):
        self._buffers = value


class AMI:
    """Ibis-AMI model with all data extracted: name, components, models.

    Parameters
    ----------
    name : str
        Name of ibis model.
    circuit : class:`pyaedt.circuit.Circuit`
        Circuit in which the ibis components will be used.
    """

    # Ibis reader must work independently or in Circuit.
    def __init__(self, name, circuit):
        self.circuit = circuit
        self._name = name
        self._components = {}
        self._model_selectors = []
        self._models = []

    @property
    def name(self):
        """Name of the ibis model."""
        return self._name

    @property
    def components(self):
        """List of all components included in the ibis file."""
        return self._components

    @components.setter
    def components(self, value):
        self._components = value

    @property
    def model_selectors(self):
        """List of all model selectors included in the ibis file."""
        return self._model_selectors

    @model_selectors.setter
    def model_selectors(self, value):
        self._model_selectors = value

    @property
    def models(self):
        """List of all models included in the ibis file."""
        return self._models

    @models.setter
    def models(self, value):
        self._models = value

    @property
    def buffers(self):
        """Buffers included into the ibis model."""
        return self._buffers

    @buffers.setter
    def buffers(self, value):
        self._buffers = value


class IbisReader(object):
    """Reads *.ibis file content.
    Setup an Ibis object exposing all the extracted data.

    Parameters
    ----------
    filename : str
        Name of ibis model.
    circuit : class:`pyaedt.circuit.Circuit`
        Circuit in which the ibis components will be used.
    """

    def __init__(self, filename, circuit):
        self._filename = filename
        self._circuit = circuit
        self._ibis_model = None

    @property
    def ibis_model(self):
        "Ibis model gathering the entire set of data extracted from the \\*.ibis file."
        return self._ibis_model

    def parse_ibis_file(self):
        """Reads \\*.ibis file content.

        Parameters
        ----------
        filename : str
            Name of ibis model.
        circuit : class:`pyaedt.circuit.Circuit`
            Circuit in which the ibis components will be used.

        Returns
        -------
        :class:`pyaedt.generic.ibis_reader.Ibis`
            Ibis object exposing all data from the ibis file.

        Examples
        --------
        Read u26a_800.ibs file provided in the AEDT suit installation.
        >>> import os
        >>> from pyaedt import Desktop
        >>> from pyaedt.circuit import Circuit
        >>> from pyaedt.generic import ibis_reader
        >>> desktop = Desktop()
        >>> circuit = Circuit()
        >>> ibis = ibis_reader.IbisReader(os.path.join(desktop.install_path, "buflib", "IBIS", "u26a_800.ibs"), circuit)

        """
        if not check_if_path_exists(self._filename):
            raise Exception("{} does not exist.".format(self._filename))

        ibis_name = pyaedt.generic.general_methods.get_filename_without_extension(self._filename)
        ibis = Ibis(ibis_name, self._circuit)
        if settings.remote_rpc_session_temp_folder:
            local_path = os.path.join(settings.remote_rpc_session_temp_folder, os.path.split(self._filename)[-1])
            file_to_open = check_and_download_file(local_path, self._filename)
        else:
            file_to_open = self._filename

        # Read *.ibis file.
        ibis_info = ibis_parsing(self._filename)
        component_selector = [ibis_info[item] for item in ibis_info if "component" in item]

        self.read_component(ibis, component_selector)

        model_selector = [ibis_info[item] for item in ibis_info if "model selector" in item]
        self.read_model_selector(ibis, model_selector)

        # model = [ibis_info[item] for item in ibis_info if 'selector' not in item and 'model' in item]
        model = [ibis_info[item] for item in ibis_info if re.match(r"^model\d*$", item) is not None]

        self.read_model(ibis, model)

        buffers = {}
        for model_selector in ibis.model_selectors:
            buffer = Buffer(ibis_name, model_selector.name, self._circuit)
            buffers[buffer.name] = buffer

        for model in ibis.models:
            buffer = Buffer(ibis_name, model.name, self._circuit)
            buffers[buffer.name] = buffer

        ibis.buffers = buffers

        if self._circuit:
            args = [
                "NAME:Options",
                "Mode:=",
                4,
                "Overwrite:=",
                False,
                "SupportsSimModels:=",
                False,
                "LoadOnly:=",
                False,
            ]
            arg_buffers = ["NAME:Buffers"]
            for buffer_item in buffers.values():
                arg_buffers.append("{}:=".format(buffer_item.short_name))
                arg_buffers.append([True, "IbisSingleEnded"])
            model_selector_names = [i.name for i in ibis.model_selectors]
            arg_components = ["NAME:Components"]
            for comp_value in ibis.components.values():
                arg_component = ["NAME:{}".format(comp_value.name)]
                for pin in comp_value.pins.values():
                    arg_component.append("{}:=".format(pin.short_name))
                    if pin.model not in model_selector_names:
                        arg_component.append([False, False])
                    else:
                        arg_component.append([True, False])
                arg_components.append(arg_component)

            args.append(arg_buffers)
            args.append(arg_components)

            self._circuit.modeler.schematic.o_component_manager.ImportModelsFromFile(self._filename, args)

        self._ibis_model = ibis
        return ibis_info

    # Model
    def read_model(self, ibis, model_list):
        """Extracts model's info.

        Parameters
        ----------
        ibis : :class:`pyaedt.generic.ibis_reader.Ibis`
            ibis object containing all info.
        current_line : str
            Current line content.
        ibis_file : TextIO
            File's stream.

        """
        for model_info in model_list:
            model_spec_info = model_info["model"].strip().split("\n")
            for idx, model_spec in enumerate(model_spec_info):
                if not idx:
                    model = Model()
                    model.name = model_spec
                else:
                    if is_started_with(model_spec.lower(), "model_type"):
                        # model.model_type = model_spec.split()[-1].strip()
                        model.model_type = model_spec.split()[-1].strip()
                        # iStart = model_spec.index(" ", 1)
                        # if iStart > 0:
                        #     model.ModelType = model_spec[iStart:].strip()
                    elif is_started_with(model_spec.lower(), "c_comp"):
                        model.c_comp = model_spec.split()[1:]

                    elif is_started_with(model_spec.lower(), "enable ", True):
                        model.enable = model_spec.split()[-1].strip()

            model_info_lower = {key.lower(): value for key, value in model_info.items()}

            if "gnd clamp" in [key.lower() for key in model_info.keys()]:
                model.clamp = True
            if "algorithmic model" in [key.lower() for key in model_info.keys()]:
                matching_key = next((key for key in model_info.keys() if "algorithmic model" in key.lower()), None)
                ami_info = model_info[matching_key][matching_key].split()
                model.ami = model_info[matching_key][matching_key].split()
                ibis.AMI = True
            else:
                ibis.AMI = False

            ibis.models.append(model)

    # Model Selector
    def read_model_selector(self, ibis, model_selector_list):
        """Extracts model selector's info.

        Parameters
        ----------
        ibis : :class:`pyaedt.generic.ibis_reader.Ibis`
            ibis object containing all info.
        current_line : str
            Current line content.
        ibis_file : TextIO
            File's stream.

        """
        for model_selector_info in model_selector_list:
            model_selector_info = model_selector_info["model selector"].strip().split("\n")
            for idx, model in enumerate(model_selector_info):
                if not idx:
                    model_selector = ModelSelector()
                    model_selector.model_selector_items = []
                    model_selector.name = model
                else:
                    model_selector.model_selector_items.append(self.make_model(model.strip()))

            # ModelSelectorItem
            ibis.model_selectors.append(model_selector)

    @classmethod
    def make_model(cls, current_line):
        """Creates model object.

        Parameters
        ----------
        current_line : str
            Current line content.

        Returns
        -------
        :class:`pyaedt.generic.ibis_reader.ModelSelectorItem`
            Model selector item.

        """
        item = ModelSelectorItem()
        i_start = current_line.index(" ", 1)

        if i_start > 0:
            item.name = current_line[:i_start].strip()
            item.description = current_line[i_start:].strip()

        return item

    # Component
    def read_component(self, ibis, comp_infos):
        """Extracts component's info.

        Parameters
        ----------
        ibis : :class:`pyaedt.generic.ibis_reader.Ibis`
            ibis object containing all info.
        comp_infos : list

        """
        if not isinstance(comp_infos, list):
            comp_infos = [comp_infos]
        for comp_info in comp_infos:
            component = Component()
            component.name = comp_info["component"]
            component.manufacturer = comp_info["manufacturer"]["manufacturer"]
            self.fill_package_info(component, comp_info["package"]["package"])
            pin_list = comp_info["pin"]["pin"].strip().split("\n")[1:]
            for pin_info in pin_list:
                pin = self.make_pin_object(pin_info, component.name, ibis)
                component.pins[pin.name] = pin

            ibis.components[component.name] = component

    @classmethod
    def fill_package_info(cls, component, pkg_info):
        """Extracts model's info.

        Parameters
        ----------
        component : :class:`pyaedt.generic.ibis_reader.Component`
            Current line content.
        current_line : str
            Current line content.
        ibis_file : TextIO
            File's stream.

        """
        pkg_info = pkg_info.strip().split("\n")
        for rlc in pkg_info:
            if is_started_with(rlc, "R_pkg"):
                component.R_pkg = rlc.strip()
            elif is_started_with(rlc, "L_pkg"):
                component.L_pkg = rlc.strip()
            elif is_started_with(rlc, "C_pkg"):
                component.C_pkg = rlc.strip()

    @classmethod
    def get_component_name(cls, line):
        """Gets the name of the component.

        Parameters
        ----------
        line : str
            Current line content.

        Returns
        -------
        str
            Name of the component.

        """
        return line.replace("[Component]", "").strip()

    def make_pin_object(self, line, component_name, ibis):
        """Extracts model's info.

        Parameters
        ----------
        line : str
            Current line content.
        component_name : str
            Name of the component.
        ibis : :class:`pyaedt.generic.ibis_reader.Ibis`
            ibis object containing all info.

        Returns
        -------
        :class:`pyaedt.generic.ibis_reader.Pin`
            Pin object.

        """
        current_string = ""

        current_string = line.strip().replace("\t", " ")

        pin_name = self.get_first_parameter(current_string)
        current_string = current_string[len(pin_name) + 1 :].strip()

        signal = self.get_first_parameter(current_string)
        current_string = current_string[len(signal) + 1 :].strip()

        model = self.get_first_parameter(current_string)
        current_string = current_string[len(model) + 1 :].strip()

        r_value = self.get_first_parameter(current_string)
        current_string = current_string[len(r_value) + 1 :].strip()

        l_value = self.get_first_parameter(current_string)
        current_string = current_string[len(l_value) + 1 :].strip()

        c_value = self.get_first_parameter(current_string)

        pin = Pin(
            pin_name + "_" + component_name + "_" + ibis.name,
            signal + "_" + component_name + "_" + ibis.name,
            ibis.circuit,
        )
        pin.short_name = pin_name
        pin.signal = signal
        pin.model = model
        pin.r_value = r_value
        pin.l_value = l_value
        pin.c_value = c_value

        return pin

    @classmethod
    def get_first_parameter(cls, line):
        """Gets first parameter string value.

        Parameters
        ----------
        line : str
            Current line content.

        Returns
        -------
        str
            First info extracted from the current line.

        """
        if line == "":
            return ""

        data = line.split(" ")
        return data[0].strip()


class AMIReader(IbisReader):
    """Reads *.ibis file content.
    Setup an Ibis object exposing all the extracted data.

    Parameters
    ----------
    filename : str
        Name of ibis model.
    circuit : class:`pyaedt.circuit.Circuit`
        Circuit in which the ibis components will be used.
    """

    def __init__(self, filename, circuit):
        self._filename = filename
        self._circuit = circuit
        self._ami_model = None

    @property
    def ami_model(self):
        "Ibis-AMI model gathering the entire set of data extracted from the \\*.ami file."
        return self._ami_model

    def parse_ibis_file(self):
        """Reads \\*.ami file content.

        Parameters
        ----------
        filename : str
            Name of ibis model.
        circuit : class:`pyaedt.circuit.Circuit`
            Circuit in which the ibis components will be used.

        Returns
        -------
        :class:`pyaedt.generic.ibis_reader.Ibis`
            Ibis object exposing all data from the ibis file.

        Examples
        --------
        Read u26a_800.ibs file provided in the AEDT suit installation.
        >>> import os
        >>> from pyaedt import Desktop
        >>> from pyaedt.circuit import Circuit
        >>> from pyaedt.generic import ibis_reader
        >>> desktop = Desktop()
        >>> circuit = Circuit()
        >>> ibis = ibis_reader.IbisReader(os.path.join(desktop.install_path, "buflib", "IBIS", "u26a_800.ibs"), circuit)
        """
        if not check_if_path_exists(self._filename):
            raise Exception("{} does not exist.".format(self._filename))

        ami_name = pyaedt.generic.general_methods.get_filename_without_extension(self._filename)
        ibis = AMI(ami_name, self._circuit)
        if settings.remote_rpc_session_temp_folder:
            local_path = os.path.join(settings.remote_rpc_session_temp_folder, os.path.split(self._filename)[-1])
            file_to_open = check_and_download_file(local_path, self._filename)
        else:
            file_to_open = self._filename

        # Read *.ibis file.
        ibis_info = ibis_parsing(self._filename)
        component_selector = [ibis_info[item] for item in ibis_info if "component" in item]

        self.read_component(ibis, component_selector)

        model_selector = [ibis_info[item] for item in ibis_info if "model selector" in item]
        self.read_model_selector(ibis, model_selector)

        # model = [ibis_info[item] for item in ibis_info if 'selector' not in item and 'model' in item]
        model = [ibis_info[item] for item in ibis_info if item.startswith("model")]

        self.read_model(ibis, model)

        buffers = {}
        for model_selector in ibis.model_selectors:
            buffer = Buffer(ami_name, model_selector.name, self._circuit)
            buffers[buffer.name] = buffer

        for model in ibis.models:
            buffer = Buffer(ami_name, model.name, self._circuit)
            buffers[buffer.name] = buffer

        ibis.buffers = buffers

        if self._circuit:
            args = [
                "NAME:Options",
                "Mode:=",
                4,
                "Overwrite:=",
                False,
                "SupportsSimModels:=",
                False,
                "LoadOnly:=",
                False,
            ]
            arg_buffers = ["NAME:Buffers"]
            for buffer in buffers:
                arg_buffers.append("{}:=".format(buffers[buffer].short_name))
                arg_buffers.append([True, "IbisSingleEnded"])
            model_selector_names = [i.name for i in ibis.model_selectors]
            arg_components = ["NAME:Components"]
            for component in ibis.components:
                arg_component = ["NAME:{}".format(ibis.components[component].name)]
                for pin in ibis.components[component].pins:
                    arg_component.append("{}:=".format(ibis.components[component].pins[pin].short_name))
                    if ibis.components[component].pins[pin].model not in model_selector_names:
                        arg_component.append([False, False])
                    else:
                        arg_component.append([True, False])
                arg_components.append(arg_component)

            args.append(arg_buffers)
            args.append(arg_components)

            self._circuit.modeler.schematic.o_component_manager.ImportModelsFromFile(self._filename, args)

        self._ibis_model = ibis
        return ibis_info


def is_started_with(src, find, ignore_case=True):
    """Verifies if a string content starts with a specific string or not.

    This is identical to ``str.startswith``, except that it includes
    the ``ignore_case`` parameter.

    Parameters
    ----------
    src : str
        Current line content.
    find : str
        Current line content.
    ignore_case : bool, optional
        Case sensitive or not. The default value is ``True``.

    Returns
    -------
    bool
        ``True`` if the src string starts with the pattern.

    """
    if ignore_case:
        return src.lower().startswith(find.lower())
    return src.startswith(find)


def lowercase_json(json_data):
    """Convert a json structure to lower case."""
    if isinstance(json_data, str):
        return json_data.lower()
    elif isinstance(json_data, dict):
        return {lowercase_json(k): lowercase_json(v) for k, v in json_data.items()}
    elif isinstance(json_data, list):
        return [lowercase_json(item) for item in json_data]
    else:
        return json_data


def ibis_parsing(file):
    """Open and parse ibis file using json Ibis template.

    Parameters
    ----------
    file : str
        File name to parse.
    """
    ibis = {}
    # OPEN AND READ IBIS FILE
    with open(file, "r") as fp:
        ibis_data = list(enumerate(fp))

    with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "ibis_v7.json"), "r") as f:
        ibis_ref = json.load(f)
    ibis_ref = lowercase_json(ibis_ref)

    # FOR EACH LINE
    try:
        level = -1
        key_iter = [0, 0, 0, 0]
        pre_key_ref = ["", "", "", ""]
        pre_key_save = ["", "", "", ""]
        for idx, line in ibis_data:
            # COMMENT
            if line[0] == "|":
                pass

            # KEYWORD START
            elif line[0] == "[":
                # FIND IBIS KEYWORD : [keyword]
                key = line.split("[")[-1].split("]")[0].replace("_", " ")
                key_ref = key.lower()
                # if key == 'End':
                #     print("JH")
                val = line.split("]")[-1].strip()
                if key_ref == "model":
                    pass

                if "end" in key_ref:
                    pass

                # FOR TOP LEVEL KEYWORD
                elif key_ref in ibis_ref.keys():
                    level = 0
                    if key_ref in ibis.keys():
                        key_iter[0] += 1
                        key_save = key_ref + str(key_iter[0])
                    else:
                        key_save = key_ref

                    ibis[key_save] = {}
                    ibis[key_save][key_ref] = val
                    pre_key_ref[0] = key_ref
                    pre_key_save[0] = key_save

                # FOR 2ND LEVEL KEYWORD
                elif key_ref in ibis_ref[pre_key_ref[0]].keys():
                    level = 1
                    if key_ref in ibis[pre_key_save[0]].keys():
                        key_iter[1] += 1
                        key_save = key_ref + str(key_iter[1])
                    else:
                        key_save = key_ref
                    ibis[pre_key_save[0]][key_save] = {}
                    ibis[pre_key_save[0]][key_save][key_ref] = val
                    pre_key_ref[1] = key_ref
                    pre_key_save[1] = key_save

                # FOR third LEVEL KEYWORD
                elif key_ref in ibis_ref[pre_key_ref[0]][pre_key_ref[1]].keys():
                    level = 2
                    if key_ref in ibis[pre_key_save[0]][pre_key_save[1]].keys():
                        key_iter[2] += 1
                        key_save = key_ref + str(key_iter[2])
                    else:
                        key_save = key_ref
                    ibis[pre_key_save[0]][pre_key_save[1]][key_save] = {}
                    ibis[pre_key_save[0]][pre_key_save[1]][key_save][key_ref] = val
                    pre_key_ref[2] = key_ref
                    pre_key_save[2] = key_save

                # FOR 4TH LEVEL KEYWORD
                elif key_ref in ibis_ref[pre_key_ref[0]][pre_key_ref[1]][pre_key_ref[2]].keys():
                    level = 3
                    if key_ref in ibis[pre_key_save[0]][pre_key_save[1]][pre_key_save[2]].keys():
                        key_iter[3] += 1
                        key_save = key_ref + str(key_iter[3])
                    else:
                        key_save = key_ref
                    ibis[pre_key_save[0]][pre_key_save[1]][pre_key_save[2]][key_save] = {}
                    ibis[pre_key_save[0]][pre_key_save[1]][pre_key_save[2]][key_save][key_ref] = val
                    pre_key_ref[3] = key_ref
                    pre_key_save[3] = key_save

                else:
                    logger.error("Invalid IBIS Keyword : {}".format(key))
                    return False

            # ALREADY FIND OUT KEYWORD
            else:
                # IF NOT BLANK LINE
                if not line.strip() == "":
                    # FOR TOP LEVEL KEYWORD
                    if level == 0:
                        ibis[pre_key_save[0]][key_ref] += "\n" + line.strip()

                    elif level == 1:
                        ibis[pre_key_save[0]][pre_key_save[1]][key_ref] += "\n" + line.strip()

                    elif level == 2:
                        ibis[pre_key_save[0]][pre_key_save[1]][pre_key_save[2]][key_ref] += "\n" + line.strip()

                    elif level == 3:
                        ibis[pre_key_save[0]][pre_key_save[1]][pre_key_save[2]][pre_key_save[3]][key_ref] += (
                            "\n" + line.strip()
                        )
    except Exception:
        logger.error(traceback.format_exc())
        return False

    # RETURN IBIS PARSING RESULT
    return ibis
