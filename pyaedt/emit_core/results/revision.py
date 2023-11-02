import warnings

from pyaedt.emit_core.emit_constants import EmiCategoryFilter, InterfererType, ResultType, TxRxMode
from pyaedt.generic.general_methods import pyaedt_function_handler


class Revision:
    """Provides the ``Revision`` object.

    Parameters
    ----------
    parent_results :
        ``Results`` object that this revision is associated with.
    emit_obj :
         ``Emit`` object that this revision is associated with.
    name : str, optional
        Name of the revision to create. The default is ``None``, in which
        case the name of the current design revision is used.

    Raises
    ------
    RuntimeError if the name given is not the name of an existing result set and a current result set already exists.

    Examples
    --------
    Create a ``Revision`` instance.

    >>> aedtapp = Emit()
    >>> rev = Revision(results, aedtapp, "Revision 1")
    >>> domain = aedtapp.interaction_domain()
    >>> rev.run(domain)
    """

    def __init__(self, parent_results, emit_obj, name=None):
        if not name:
            name = emit_obj.odesign.GetCurrentResult()
            if not name:
                name = emit_obj.odesign.AddResult("")
        else:
            if name not in emit_obj.odesign.GetResultList():
                name = emit_obj.odesign.AddResult(name)
        full = emit_obj.odesign.GetResultDirectory(name)

        self.name = name
        """Name of the revision."""

        self.path = full
        """Full path of the revision."""

        self.emit_project = emit_obj
        """EMIT project."""

        raw_props = emit_obj.odesign.GetResultProperties(name)
        key = lambda s: s.split("=", 1)[0]
        val = lambda s: s.split("=", 1)[1]
        props = {key(s): val(s) for s in raw_props}

        self.revision_number = int(props["Revision"])
        """Unique revision number from the EMIT design"""

        self.timestamp = props["Timestamp"]
        """Unique timestamp for the revision"""

        self.parent_results = parent_results
        """Parent Results object"""

        # load the revision after creating it
        self.revision_loaded = False
        """``True`` if the revision is loaded and ``False`` if it is not."""
        self._load_revision()

    @pyaedt_function_handler()
    def _load_revision(self):
        """Load this revision.

        Examples
        --------
        >>> aedtapp.results.revision.load_revision()
        """
        if self.revision_loaded:
            return
        self.parent_results._unload_revisions()
        self.emit_project._emit_api.load_project(self.path)
        self.revision_loaded = True

    @staticmethod
    def result_mode_error():
        """Print the function mode error message.

        Returns
        -------
        err_msg : str
            Error/warning message that the specified revision is not accessible.
        """
        err_msg = "This function is inaccessible when the revision is not loaded."
        print(err_msg)
        return err_msg

    @pyaedt_function_handler()
    def get_interaction(self, domain):
        """Create a new interaction for a domain.

        Parameters
        ----------
        domain : class:`Emit.InteractionDomain`
            ``InteractionDomain`` object for constraining the analysis parameters.

        Returns
        -------
        interaction:class: `Interaction`
            Interaction object.

        Examples
        --------
        >>> domain = aedtapp.results.interaction_domain()
        >>> rev.get_interaction(domain)

        """
        self._load_revision()
        engine = self.emit_project._emit_api.get_engine()
        if domain.interferer_names and engine.max_simultaneous_interferers != len(domain.interferer_names):
            raise ValueError("The max_simultaneous_interferers must equal the number of interferers in the domain.")
        interaction = engine.get_interaction(domain)
        return interaction

    @pyaedt_function_handler()
    def run(self, domain):
        """Load the revision and then analyze along the given domain.

        Parameters
        ----------
        domain :
            ``InteractionDomain`` object for constraining the analysis parameters.

        Returns
        -------
        interaction:class: `Interaction`
            Interaction object.

        Examples
        --------
        >>> domain = aedtapp.results.interaction_domain()
        >>> rev.run(domain)

        """
        if domain.receiver_channel_frequency > 0:
            raise ValueError("The domain must not have channels specified.")
        if len(domain.interferer_channel_frequencies) != 0:
            for freq in domain.interferer_channel_frequencies:
                if freq > 0:
                    raise ValueError("The domain must not have channels specified.")
        self._load_revision()
        engine = self.emit_project._emit_api.get_engine()
        if self.emit_project._aedt_version < "2024.1":
            if len(domain.interferer_names) == 1:
                engine.max_simultaneous_interferers = 1
            if len(domain.interferer_names) > 1:
                raise ValueError("Multiple interferers cannot be specified prior to AEDT version 2024 R1.")
        interaction = engine.run(domain)
        # save the revision
        self.emit_project._emit_api.save_project()
        return interaction

    @pyaedt_function_handler()
    def is_domain_valid(self, domain):
        """Return ``True`` if the given domain is valid for the current revision.

        Parameters
        ----------
        domain :
            ``InteractionDomain`` object for constraining the analysis parameters.

        Examples
        --------
        >>> domain = aedtapp.interaction_domain()
        >>> aedtapp.results.current_revision.is_domain_valid(domain)
        True
        """
        self._load_revision()
        engine = self.emit_project._emit_api.get_engine()
        return engine.is_domain_valid(domain)

    @pyaedt_function_handler()
    def get_instance_count(self, domain):
        """Return the number of instances in the domain for the current revision.

        Parameters
        ----------
        domain :
            ``InteractionDomain`` object for constraining the analysis parameters.

        Returns
        -------
        count : int
            Number of instances in the domain for the current revision.

        Examples
        --------
        >>> domain = aedtapp.interaction_domain()
        >>> num_instances = aedtapp.results.current_revision.get_instance_count(domain)
        """
        self._load_revision()
        engine = self.emit_project._emit_api.get_engine()
        return engine.get_instance_count(domain)

    @pyaedt_function_handler()
    def get_receiver_names(self):
        """Get a list of all receivers in the project.

        Parameters
        ----------
        None

        Returns
        -------
        radios:class:`list of str`
            List of receiver names.

        Examples
        --------
        >>> rxs = aedtapp.results.current_revision.get_reciver_names()
        """
        if self.revision_loaded:
            radios = self.emit_project._emit_api.get_radio_names(TxRxMode.RX, InterfererType.TRANSMITTERS_AND_EMITTERS)
        else:
            radios = None
            err_msg = self.result_mode_error()
            warnings.warn(err_msg)
            return radios
        if len(radios) == 0:
            warnings.warn("No valid receivers in the project.")
        return radios

    @pyaedt_function_handler()
    def get_interferer_names(self, interferer_type=None):
        """Get a list of all interfering transmitters/emitters in the project.

        Parameters
        ----------
        interferer_type : interferer_type object, optional
            Type of interferer to return. The default is ``None``, in which
            case both transmitters and emitters are returned. Options are:
                - transmitters
                - emitters
                - transmitters_and_emitters

        Returns
        -------
        radios:class:`list of str`
            List of interfering systems' names.

        Examples
        --------
        >>> transmitters = aedtapp.results.current_revision.get_interferer_names(InterfererType.TRANSMITTERS)
        >>> emitters = aedtapp.results.current_revision.get_interferer_names(InterfererType.EMITTERS)
        >>> both = aedtapp.results.current_revision.get_interferer_names(InterfererType.TRANSMITTERS_AND_EMITTERS)
        """
        if interferer_type is None:
            interferer_type = InterfererType.TRANSMITTERS_AND_EMITTERS
        if self.revision_loaded:
            radios = self.emit_project._emit_api.get_radio_names(TxRxMode.TX, interferer_type)
        else:
            radios = None
            err_msg = self.result_mode_error()
            warnings.warn(err_msg)
            return radios
        if len(radios) == 0:
            warnings.warn("No valid radios or emitters in the project.")
            return None
        return radios

    @pyaedt_function_handler()
    def get_band_names(self, radio_name, tx_rx_mode=None):
        """Get a list of all ``tx`` or ``rx`` bands (or waveforms) in
        a given radio/emitter.

        Parameters
        ----------
        radio_name : str
            Name of the radio/emitter.
        tx_rx_mode : :class:`emit_constants.TxRxMode`, optional
            Specifies whether to get ``tx`` or ``rx`` band names. The default
            is ``None``, in which case the names of all enabled bands are returned.

        Returns
        -------
        bands:class:`list of str`
            List of ``tx`` or ``rx`` band/waveform names.

        Examples
        --------
        >>> bands = aedtapp.results.current_revision.get_band_names('Bluetooth', TxRxMode.RX)
        >>> waveforms = aedtapp.results.current_revision.get_band_names('USB_3.x', TxRxMode.TX)
        """
        if tx_rx_mode is None:
            tx_rx_mode = TxRxMode.BOTH
        if self.revision_loaded:
            bands = self.emit_project._emit_api.get_band_names(radio_name, tx_rx_mode)
        else:
            bands = None
            self.result_mode_error()
            err_msg = self.result_mode_error()
            warnings.warn(err_msg)
            return bands
        return bands

    @pyaedt_function_handler()
    def get_active_frequencies(self, radio_name, band_name, tx_rx_mode, units=""):
        """Get a list of active frequencies for a ``tx`` or ``rx`` band in a radio/emitter.

        Parameters
        ----------
        radio_name : str
            Name of the radio/emitter.
        band_name : str
           Name of the band.
        tx_rx_mode : :class:`emit_constants.TxRxMode`
            Specifies whether to get ``tx`` or ``rx`` radio frequencies.
        units : str, optional
            Units for the frequencies. The default is ``None`` which uses the units
            specified globally for the project.

        Returns
        -------
        freqs : List of float
            List of ``tx`` or ``rx`` radio/emitter frequencies.

        Examples
        --------
        >>> freqs = aedtapp.results.current_revision.get_active_frequencies(
                'Bluetooth', 'Rx - Base Data Rate', TxRxMode.RX)
        """
        if tx_rx_mode is None or tx_rx_mode == TxRxMode.BOTH:
            raise ValueError("The mode type must be specified as either Tx or Rx.")
        if self.revision_loaded:
            freqs = self.emit_project._emit_api.get_active_frequencies(radio_name, band_name, tx_rx_mode, units)
        else:
            freqs = None
            err_msg = self.result_mode_error()
            warnings.warn(err_msg)
            return freqs
        return freqs

    @property
    def notes(self):
        """Add notes to the revision.

        Examples
        --------
        >>> aedtapp.results.current_revision.notes = "Added a filter to the WiFi Radio."
        >>> aedtapp.results.current_revision.notes
        'Added a filter to the WiFi Radio.'
        """
        design = self.emit_project.odesign
        return design.GetResultNotes(self.name)

    @notes.setter
    def notes(self, notes):
        self.emit_project.odesign.SetResultNotes(self.name, notes)
        self.emit_project._emit_api.save_project()

    @property
    def n_to_1_limit(self):
        """Maximum number of interference combinations to run per receiver for N to 1.

        - A value of ``0`` disables N to 1 entirely.
        - A value of  ``-1`` allows unlimited N to 1. (N is set to the maximum.)

        Examples
        --------
        >>> aedtapp.results.current_revision.n_to_1_limit = 2**20
        >>> aedtapp.results.current_revision.n_to_1_limit
        1048576
        """
        if self.emit_project._aedt_version < "2024.1":  # pragma: no cover
            raise RuntimeError("This function only supported in AEDT version 2024.1 and later.")
        if self.revision_loaded:
            engine = self.emit_project._emit_api.get_engine()
            max_instances = engine.n_to_1_limit
        else:  # pragma: no cover
            max_instances = None
        return max_instances

    @n_to_1_limit.setter
    def n_to_1_limit(self, max_instances):
        if self.emit_project._aedt_version < "2024.1":  # pragma: no cover
            raise RuntimeError("This function only supported in AEDT version 2024.1 and later.")
        if self.revision_loaded:
            engine = self.emit_project._emit_api.get_engine()
            engine.n_to_1_limit = max_instances

    @pyaedt_function_handler()
    def interference_type_classification(self, domain, use_filter=False, filter_list=None):
        """Classify interference type as according to inband/inband,
        out of band/in band, inband/out of band, and out of band/out of band.

        Parameters
        ----------
            domain :
                ``InteractionDomain`` object for constraining the analysis parameters.
            use_filter : bool, optional
                Whether filtering is being used. The default is ``False``.
            filter_list : list, optional
                List of filter values selected by the user via the GUI if filtering is in use.

        Returns
        -------
            power_matrix : list
                List of worst case interference power at Rx.
            all_colors : list
                List of color classification of interference types.

        Examples
        --------
        >>> interference_results = rev.interference_type_classification(domain)
        """
        power_matrix = []
        all_colors = []

        # Get project results and radios
        modeRx = TxRxMode.RX
        modeTx = TxRxMode.TX
        mode_power = ResultType.POWER_AT_RX
        tx_interferer = InterfererType().TRANSMITTERS
        rx_radios = self.get_receiver_names()
        tx_radios = self.get_interferer_names(tx_interferer)
        radios = self.emit_project.modeler.components.get_radios()

        for tx_radio in tx_radios:
            rx_powers = []
            rx_colors = []
            for rx_radio in rx_radios:
                # powerAtRx is the same for all Rx bands, so just use first one
                rx_bands = self.get_band_names(rx_radio, modeRx)
                rx_band_objects = radios[rx_radio].bands()
                if tx_radio == rx_radio:
                    # skip self-interaction
                    rx_powers.append("N/A")
                    rx_colors.append("white")
                    continue

                max_power = -200
                tx_bands = self.get_band_names(tx_radio, modeTx)

                for i, rx_band in enumerate(rx_bands):
                    # Find the highest power level at the Rx input due to each Tx Radio.
                    # Can look at any Rx freq since susceptibility won't impact
                    # powerAtRx, but need to look at all tx channels since coupling
                    # can change over a transmitter's bandwidth
                    rx_freq = self.get_active_frequencies(rx_radio, rx_band, modeRx)[0]

                    # The start and stop frequencies define the Band's extents,
                    # while the active frequencies are a subset of the Band's frequencies
                    # being used for this specific project as defined in the Radio's Sampling.
                    rx_start_freq = radios[rx_radio].band_start_frequency(rx_band_objects[i])
                    rx_stop_freq = radios[rx_radio].band_stop_frequency(rx_band_objects[i])
                    rx_channel_bandwidth = radios[rx_radio].band_channel_bandwidth(rx_band_objects[i])

                    for tx_band in tx_bands:
                        domain.set_receiver(rx_radio, rx_band)
                        domain.set_interferer(tx_radio, tx_band)
                        interaction = self.run(domain)
                        # check for valid interaction, this would catch any disabled radio pairs
                        if not interaction.is_valid():
                            continue

                        domain.set_receiver(rx_radio, rx_band, rx_freq)
                        tx_freqs = self.get_active_frequencies(tx_radio, tx_band, modeTx)
                        for tx_freq in tx_freqs:
                            domain.set_interferer(tx_radio, tx_band, tx_freq)
                            instance = interaction.get_instance(domain)
                            if not instance.has_valid_values():
                                # check for saturation somewhere in the chain
                                # set power so its flagged as strong interference
                                if instance.get_result_warning() == "An amplifier was saturated.":
                                    max_power = 200
                                else:
                                    # other warnings (e.g. no path from Tx to Rx,
                                    # no power received, error in configuration, etc)
                                    # should just be skipped
                                    continue
                            else:
                                tx_prob = (
                                    instance.get_largest_problem_type(ResultType.EMI).replace(" ", "").split(":")[1]
                                )
                                power = instance.get_value(ResultType.EMI)
                            if (
                                rx_start_freq - rx_channel_bandwidth / 2
                                <= tx_freq
                                <= rx_stop_freq + rx_channel_bandwidth / 2
                            ):
                                rx_prob = "In-band"
                            else:
                                rx_prob = "Out-of-band"
                            prob_filter_val = tx_prob + ":" + rx_prob

                            # Check if problem type is in filtered list of problem types to analyze
                            if use_filter:
                                in_filters = any(prob_filter_val in sublist for sublist in filter_list)
                            else:
                                in_filters = True

                            # Save the worst case interference values
                            if power > max_power and in_filters:
                                max_power = power
                                largest_rx_prob = rx_prob
                                prob = instance.get_largest_problem_type(ResultType.EMI)
                                largest_tx_prob = prob.replace(" ", "").split(":")

                if max_power > -200:
                    rx_powers.append(max_power)

                    if largest_tx_prob[-1] == "TxFundamental" and largest_rx_prob == "In-band":
                        rx_colors.append("red")
                    elif largest_tx_prob[-1] != "TxFundamental" and largest_rx_prob == "In-band":
                        rx_colors.append("orange")
                    elif largest_tx_prob[-1] == "TxFundamental" and not (largest_rx_prob == "In-band"):
                        rx_colors.append("yellow")
                    elif largest_tx_prob[-1] != "TxFundamental" and not (largest_rx_prob == "In-band"):
                        rx_colors.append("green")
                else:
                    rx_powers.append("<= -200")
                    rx_colors.append("white")

            all_colors.append(rx_colors)
            power_matrix.append(rx_powers)

        return all_colors, power_matrix

    @pyaedt_function_handler()
    def protection_level_classification(
        self,
        domain,
        global_protection_level=True,
        global_levels=None,
        protection_levels=None,
        use_filter=False,
        filter_list=None,
    ):
        """Classify worst-case power at each Rx radio according to interference type.

        Options for interference type are `inband/inband, out of band/in band,
        inband/out of band, and out of band/out of band.

        Parameters
        ----------
            domain :
                ``InteractionDomain`` object for constraining the analysis parameters.
            global_protection_level : bool, optional
                Whether to use the same protection levels for all radios. The default is ``True``.
            global_levels : list, optional
                List of protection levels to use for all radios.
            protection_levels : dict, optional
                Dictionary of protection levels for each Rx radio.
            use_filter : bool, optional
                Whether to use filtering. The default is ``False``.
            filter_list : list, optional
                List of filter values selected by the user via the GUI if filtering is in use.

        Returns
        -------
            power_matrix : list
                List of worst case interference according to power at each Rx radio.
            all_colors : list
                List of color classification of protection level.

        Examples
        --------
        >>> protection_results = rev.protection_level_classification(domain)
        """
        power_matrix = []
        all_colors = []

        # Get project results and radios
        modeRx = TxRxMode.RX
        modeTx = TxRxMode.TX
        mode_power = ResultType.POWER_AT_RX
        tx_interferer = InterfererType().TRANSMITTERS
        rx_radios = self.get_receiver_names()
        tx_radios = self.get_interferer_names(tx_interferer)

        if global_protection_level and global_levels == None:
            damage_threshold = 30
            overload_threshold = 4
            intermod_threshold = -20
        elif global_protection_level:
            damage_threshold = global_levels[0]
            overload_threshold = global_levels[1]
            intermod_threshold = global_levels[2]

        for tx_radio in tx_radios:
            rx_powers = []
            rx_colors = []
            for rx_radio in rx_radios:
                # powerAtRx is the same for all Rx bands, so just
                # use the first one
                if not (global_protection_level):
                    damage_threshold = protection_levels[rx_radio][0]
                    overload_threshold = protection_levels[rx_radio][1]
                    intermod_threshold = protection_levels[rx_radio][2]

                rx_band = self.get_band_names(rx_radio, modeRx)[0]
                if tx_radio == rx_radio:
                    # skip self-interaction
                    rx_powers.append("N/A")
                    rx_colors.append("white")
                    continue

                max_power = -200
                tx_bands = self.get_band_names(tx_radio, modeTx)

                for tx_band in tx_bands:
                    # Find the highest power level at the Rx input due to each Tx Radio.
                    # Can look at any Rx freq since susceptibility won't impact
                    # powerAtRx, but need to look at all tx channels since coupling
                    # can change over a transmitter's bandwidth
                    rx_freq = self.get_active_frequencies(rx_radio, rx_band, modeRx)[0]
                    domain.set_receiver(rx_radio, rx_band)
                    domain.set_interferer(tx_radio, tx_band)
                    interaction = self.run(domain)
                    # check for valid interaction, this would catch any disabled radio pairs
                    if not interaction.is_valid():
                        continue
                    domain.set_receiver(rx_radio, rx_band, rx_freq)
                    tx_freqs = self.get_active_frequencies(tx_radio, tx_band, modeTx)

                    power_list = []

                    for tx_freq in tx_freqs:
                        domain.set_interferer(tx_radio, tx_band, tx_freq)
                        instance = interaction.get_instance(domain)
                        if not instance.has_valid_values():
                            # check for saturation somewhere in the chain
                            # set power so its flagged as "damage threshold"
                            if instance.get_result_warning() == "An amplifier was saturated.":
                                max_power = 200
                            else:
                                # other warnings (e.g. no path from Tx to Rx,
                                # no power received, error in configuration, etc)
                                # should just be skipped
                                continue
                        else:
                            power = instance.get_value(mode_power)

                        if power > damage_threshold:
                            classification = "damage"
                        elif power > overload_threshold:
                            classification = "overload"
                        elif power > intermod_threshold:
                            classification = "intermodulation"
                        else:
                            classification = "desensitization"

                        power_list.append(power)

                        if use_filter:
                            filtering = classification in filter_list
                        else:
                            filtering = True

                        if power > max_power and filtering:
                            max_power = power

                # If the worst case for the band-pair is below the power thresholds, then
                # there are no interference issues and no offset is required.
                if max_power > -200:
                    rx_powers.append(max_power)
                    if max_power > damage_threshold:
                        rx_colors.append("red")
                    elif max_power > overload_threshold:
                        rx_colors.append("orange")
                    elif max_power > intermod_threshold:
                        rx_colors.append("yellow")
                    else:
                        rx_colors.append("green")
                else:
                    rx_powers.append("< -200")
                    rx_colors.append("white")

            all_colors.append(rx_colors)
            power_matrix.append(rx_powers)

        return all_colors, power_matrix

    def get_emi_category_filter_enabled(self, category: EmiCategoryFilter) -> bool:
        """Get whether the EMI category filter is enabled.

        Parameters
        ----------
        category : :class:`EmiCategoryFilter`
            EMI category filter.

        Returns
        -------
        bool
            ``True`` when the EMI category filter is enabled, ``False`` otherwise.
        """
        if self.emit_project._aedt_version < "2024.1":  # pragma: no cover
            raise RuntimeError("This function is only supported in AEDT version 2024 R1 and later.")
        engine = self.emit_project._emit_api.get_engine()
        return engine.get_emi_category_filter_enabled(category)

    def set_emi_category_filter_enabled(self, category: EmiCategoryFilter, enabled: bool):
        """Set whether the EMI category filter is enabled.

        Parameters
        ----------
        category : :class:`EmiCategoryFilter`
            EMI category filter.
        enabled : bool
            Whether to enable the EMI category filter.
        """
        if self.emit_project._aedt_version < "2024.1":  # pragma: no cover
            raise RuntimeError("This function is only supported in AEDT version 2024 R1 and later.")
        engine = self.emit_project._emit_api.get_engine()
        engine.set_emi_category_filter_enabled(category, enabled)
