import imp
from importlib import import_module
import os
import sys

from pyaedt.aedt_logger import pyaedt_logger as logger
from pyaedt.emit_core.emit_constants import EmiCategoryFilter, InterfererType, ResultType, TxRxMode, UnitType

EMIT_API_PYTHON = None


def emit_api_python():
    """Get the EMIT backend API.

    The backend API is available once a pyaedt.Emit() object has been created. An exception is raised if this method is called before a ``pyaedt.Emit()`` object has been created.
    """
    if not EMIT_API_PYTHON:
        raise Exception("A pyaedt.Emit() object must be initialized before using the EMIT API.")
    return EMIT_API_PYTHON


def _init_enums(aedt_version):
    ResultType.EMI = emit_api_python().result_type().emi
    ResultType.DESENSE = emit_api_python().result_type().desense
    ResultType.SENSITIVITY = emit_api_python().result_type().sensitivity
    ResultType.POWER_AT_RX = emit_api_python().result_type().powerAtRx

    TxRxMode.TX = emit_api_python().tx_rx_mode().tx
    TxRxMode.RX = emit_api_python().tx_rx_mode().rx
    TxRxMode.BOTH = emit_api_python().tx_rx_mode().both

    InterfererType.TRANSMITTERS = emit_api_python().interferer_type().transmitters
    InterfererType.EMITTERS = emit_api_python().interferer_type().emitters
    InterfererType.TRANSMITTERS_AND_EMITTERS = emit_api_python().interferer_type().transmitters_and_emitters

    UnitType.POWER = emit_api_python().unit_type().power
    UnitType.FREQUENCY = emit_api_python().unit_type().frequency
    UnitType.LENGTH = emit_api_python().unit_type().length
    UnitType.TIME = emit_api_python().unit_type().time
    UnitType.VOLTAGE = emit_api_python().unit_type().voltage
    UnitType.DATA_RATE = emit_api_python().unit_type().dataRate
    UnitType.RESISTANCE = emit_api_python().unit_type().resistance

    numeric_version = int(aedt_version[-3:])
    if numeric_version >= 241:
        emi_cat_filter = emit_api_python().emi_category_filter()
        EmiCategoryFilter.IN_CHANNEL_TX_FUNDAMENTAL = emi_cat_filter.in_channel_tx_fundamental
        EmiCategoryFilter.IN_CHANNEL_TX_HARMONIC_SPURIOUS = emi_cat_filter.in_channel_tx_harmonic_spurious
        EmiCategoryFilter.IN_CHANNEL_TX_INTERMOD = emi_cat_filter.in_channel_tx_intermod
        EmiCategoryFilter.IN_CHANNEL_TX_BROADBAND = emi_cat_filter.in_channel_tx_broadband
        EmiCategoryFilter.OUT_OF_CHANNEL_TX_FUNDAMENTAL = emi_cat_filter.out_of_channel_tx_fundamental
        EmiCategoryFilter.OUT_OF_CHANNEL_TX_HARMONIC_SPURIOUS = emi_cat_filter.out_of_channel_tx_harmonic_spurious
        EmiCategoryFilter.OUT_OF_CHANNEL_TX_INTERMOD = emi_cat_filter.out_of_channel_tx_intermod


# need this as a function so that it can be set
# for the correct aedt version that the user is running
def _set_api(aedt_version):
    numeric_version = int(aedt_version[-3:])
    desktop_path = os.environ.get(aedt_version)
    if desktop_path and numeric_version > 231:
        path = os.path.join(desktop_path, "Delcross")
        override_path_key = "ANSYS_DELCROSS_PYTHON_PATH"
        if override_path_key in os.environ:
            path = os.environ.get(override_path_key)
        sys.path.insert(0, path)
        module_path = imp.find_module("EmitApiPython")[1]
        logger.info("Importing EmitApiPython from: {}".format(module_path))
        global EMIT_API_PYTHON
        EMIT_API_PYTHON = import_module("EmitApiPython")
        logger.info("Loaded {}".format(EMIT_API_PYTHON.EmitApi().get_version(True)))
        _init_enums(aedt_version)
