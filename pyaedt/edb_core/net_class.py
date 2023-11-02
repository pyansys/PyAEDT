from __future__ import absolute_import  # noreorder

import re

from pyaedt.edb_core.edb_data.nets_data import EDBDifferentialPairData, EDBExtendedNetData, EDBNetClassData
from pyaedt.generic.general_methods import pyaedt_function_handler


class EdbCommon:
    def __init__(self, pedb):
        self._pedb = pedb

    @property
    def _layout(self):
        """Get layout.

        Returns
        -------
        :class:` :class:`pyaedt.edb_core.dotnet.layout.LayoutDotNet`
        """
        return self._pedb.layout

    @property
    def _logger(self):
        """EDB logger."""
        return self._pedb.logger

    @pyaedt_function_handler()
    def __getitem__(self, name):
        """Get  a net from the EDB project.

        Parameters
        ----------
        name : str, int
            Name or ID of the net.

        Returns
        -------
        :class:` :class:`pyaedt.edb_core.edb_data.nets_data.EDBExtendedNetsData`

        """
        if name in self.items:
            return self.items[name]
        self._pedb.logger.error("Component or definition not found.")


class EdbNetClasses(EdbCommon, object):
    """Manages EDB methods for managing nets accessible from the ``Edb.net_classes`` property.

    Examples
    --------
    >>> from pyaedt import Edb
    >>> edbapp = Edb("myaedbfolder", edbversion="2021.2")
    >>> edb_nets = edbapp.net_classes
    """

    def __init__(self, p_edb):
        super().__init__(p_edb)

    @property
    def items(self):
        """Extended nets.

        Returns
        -------
        dict[str, :class:`pyaedt.edb_core.edb_data.nets_data.EDBDifferentialPairData`]
            Dictionary of extended nets.
        """
        net_classes = {}
        for net_class in self._layout.net_classes:
            net_classes[net_class.GetName()] = EDBNetClassData(self._pedb, net_class)
        return net_classes

    @pyaedt_function_handler
    def create(self, name, net):
        # type: (str, str|list)->EDBNetClassData
        """Create a new net class.

        Parameters
        ----------
        name : str
            Name of the net class.
        net : str, list
           Name of the nets to be added into this net class.

        Returns
        -------
        :class:`pyaedt.edb_core.edb_data.nets_data.EDBNetClassData`
        """
        if name in self.items:
            self._pedb.logger.error("{} already exists.".format(name))
            return False

        temp = EDBNetClassData(self._pedb)
        api_obj = temp.api_create(name)
        if isinstance(net, str):
            net = [net]
        for i in net:
            api_obj.add_net(i)

        return self.items[name]


class EdbExtendedNets(EdbCommon, object):
    """Manages EDB methods for managing nets accessible from the ``Edb.extended_nets`` property.

    Examples
    --------
    >>> from pyaedt import Edb
    >>> edbapp = Edb("myaedbfolder", edbversion="2021.2")
    >>> edb_nets = edbapp.extended_nets
    """

    def __init__(self, p_edb):
        super().__init__(p_edb)

    @property
    def items(self):
        """Extended nets.

        Returns
        -------
        dict[str, :class:`pyaedt.edb_core.edb_data.nets_data.EDBExtendedNetsData`]
            Dictionary of extended nets.
        """
        nets = {}
        for extended_net in self._layout.extended_nets:
            nets[extended_net.GetName()] = EDBExtendedNetData(self._pedb, extended_net)
        return nets

    @pyaedt_function_handler
    def create(self, name, net):
        # type: (str, str|list)->EDBExtendedNetData
        """Create a new Extended net.

        Parameters
        ----------
        name : str
            Name of the extended net.
        net : str, list
           Name of the nets to be added into this extended net.

        Returns
        -------
        :class:`pyaedt.edb_core.edb_data.nets_data.EDBExtendedNetsData`
        """
        if name in self.items:
            self._pedb.logger.error("{} already exists.".format(name))
            return False

        extended_net = EDBExtendedNetData(self._pedb)
        api_extended_net = extended_net.api_create(name)
        if isinstance(net, str):
            net = [net]
        for i in net:
            api_extended_net.add_net(i)

        return self.items[name]

    @pyaedt_function_handler
    def auto_identify_signal(self, resistor_below=10, inductor_below=1, capacitor_above=1e-9, exception_list=None):
        # type: (int | float, int | float, int |float, list) -> list
        """Get extended signal net and associated components.

        Parameters
        ----------
        resistor_below : int, float, optional
            Threshold for the resistor value. Search the extended net across resistors that
            have a value lower than the threshold.
        inductor_below : int, float, optional
            Threshold for the inductor value. Search the extended net across inductances
            that have a value lower than the threshold.
        capacitor_above : int, float, optional
            Threshold for the capacitor value. Search the extended net across capacitors
            that have a value higher than the threshold.
        exception_list : list, optional
            List of components to bypass when performing threshold checks. Components
            in the list are considered as serial components. The default is ``None``.

        Returns
        -------
        list
            List of all extended nets.

        Examples
        --------
        >>> from pyaedt import Edb
        >>> app = Edb()
        >>> app.extended_nets.auto_identify_signal()
        """
        return self._pedb.nets.generate_extended_nets(
            resistor_below, inductor_below, capacitor_above, exception_list, True, False
        )

    @pyaedt_function_handler
    def auto_identify_power(self, resistor_below=10, inductor_below=1, capacitor_above=1, exception_list=None):
        # type: (int | float, int | float, int |float, list) -> list
        """Get all extended power nets and their associated components.

        Parameters
        ----------
        resistor_below : int, float, optional
            Threshold for the resistor value. Search the extended net across resistors that
            have a value lower than the threshold.
        inductor_below : int, float, optional
            Threshold for the inductor value. Search the extended net across inductances that
            have a value lower than the threshold.
        capacitor_above : int, float, optional
            Threshold for the capacitor value. Search the extended net across capacitors that
            have a value higher than the threshold.
        exception_list : list, optional
            List of components to bypass when performing threshold checks. Components
            in the list are considered as serial components. The default is ``None``.

        Returns
        -------
        list
            List of all extended nets and their associated components.

        Examples
        --------
        >>> from pyaedt import Edb
        >>> app = Edb()
        >>> app.extended_nets.auto_identify_power()
        """
        return self._pedb.nets.generate_extended_nets(
            resistor_below, inductor_below, capacitor_above, exception_list, False, True
        )


class EdbDifferentialPairs(EdbCommon, object):
    """Manages EDB methods for managing nets accessible from the ``Edb.differential_pairs`` property.

    Examples
    --------
    >>> from pyaedt import Edb
    >>> edbapp = Edb("myaedbfolder", edbversion="2021.2")
    >>> edb_nets = edbapp.differential_pairs.items
    >>> edb_nets = edbapp.differential_pairs["DQ4"]
    """

    def __init__(self, p_edb):
        super().__init__(p_edb)

    @property
    def items(self):
        """Extended nets.

        Returns
        -------
        dict[str, :class:`pyaedt.edb_core.edb_data.nets_data.EDBDifferentialPairData`]
            Dictionary of extended nets.
        """
        diff_pairs = {}
        for diff_pair in self._layout.differential_pairs:
            diff_pairs[diff_pair.GetName()] = EDBDifferentialPairData(self._pedb, diff_pair)
        return diff_pairs

    @pyaedt_function_handler
    def create(self, name, net_p, net_n):
        # type: (str, str, str) -> EDBDifferentialPairData
        """Parameters
        ----------
        name : str
            Name of the differential pair.
        net_p : str
            Name of the positive net.
        net_n : str
            Name of the negative net.

        Returns
        -------
        :class:`pyaedt.edb_core.edb_data.nets_data.EDBDifferentialPairData`
        """
        if name in self.items:
            self._pedb.logger.error("{} already exists.".format(name))
            return False

        diff_pair = EDBDifferentialPairData(self._pedb)
        diff_pair.api_create(name)._api_set_differential_pair(net_p, net_n)

        return self.items[name]

    @pyaedt_function_handler
    def auto_identify(self, positive_differentiator="_P", negative_differentiator="_N"):
        """Auto identify differential pairs by naming conversion.

        Parameters
        ----------
        positive_differentiator: str, optional
            Differentiator of the positive net. The default is ``"_P"``.
        negative_differentiator: str, optional
            Differentiator of the negative net. The default is ``"_N"``.

        Returns
        -------
        list
            A list containing identified differential pair names.

        Examples
        --------
        >>> from pyaedt import Edb
        >>> edbapp = Edb("myaedbfolder", edbversion="2023.1")
        >>> edb_nets = edbapp.differential_pairs.auto_identify()
        """
        nets = self._pedb.nets.nets
        pos_net = []
        neg_net = []
        for name, _ in nets.items():
            if name.endswith(positive_differentiator):
                pos_net.append(name)
            elif name.endswith(negative_differentiator):
                neg_net.append(name)
            else:
                pass

        temp = []
        for p in pos_net:
            pattern_p = r"^(.+){}$".format(positive_differentiator)
            match_p = re.findall(pattern_p, p)[0]

            for n in neg_net:
                pattern_n = r"^(.+){}$".format(negative_differentiator)
                match_n = re.findall(pattern_n, n)[0]

                if match_p == match_n:
                    diff_name = "DIFF_{}".format(match_p)
                    self.create(diff_name, p, n)
                    temp.append(diff_name)
        return temp
