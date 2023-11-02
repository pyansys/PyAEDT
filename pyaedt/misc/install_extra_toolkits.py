import os
import shutil
import warnings
import xml.etree.ElementTree as ET
from xml.etree.ElementTree import ParseError

from pyaedt.misc.aedtlib_personalib_install import current_dir, write_pretty_xml

available_toolkits = {
    "AntennaWizard": {
        "pip": "git+https://github.com/ansys/pyaedt-antenna-toolkit.git",
        "image": "pyansys.png",
        "toolkit_script": "ansys/aedt/toolkits/antenna/run_toolkit.py",
        "installation_path": "HFSS",
        "package_name": "ansys.aedt.toolkits.antenna",
    },
    "ChokeWizard": {
        "pip": "git+https://github.com/ansys/pyaedt-choke-toolkit.git",
        "image": "pyansys.png",
        "toolkit_script": "ansys/aedt/toolkits/choke/choke_toolkit.py",
        "installation_path": "Project",
        "package_name": "ansys.aedt.toolkits.choke",
    },
}


def write_toolkit_config(product_toolkit_dir, pyaedt_lib_dir, toolkitname, toolkit, force_write=False):
    """Write a toolkit configuration file and, if needed a button in Automation menu."""
    tab_config_file_path = os.path.join(product_toolkit_dir, "TabConfig.xml")
    if not os.path.isfile(tab_config_file_path) or force_write:
        root = ET.Element("TabConfig")
    else:
        try:
            tree = ET.parse(tab_config_file_path)
        except ParseError as e:
            warnings.warn("Unable to parse %s\nError received = %s" % (tab_config_file_path, str(e)))
            return
        root = tree.getroot()

    panels = root.findall("./panel")
    if panels:
        panel_names = [panel.attrib["label"] for panel in panels]
        if "Panel_PyAEDT_Toolkits" in panel_names:
            # Remove previously existing PyAEDT panel and update with newer one.
            panel = [panel for panel in panels if panel.attrib["label"] == "Panel_PyAEDT_Toolkits"][0]
        else:
            panel = ET.SubElement(root, "panel", label="Panel_PyAEDT_Toolkits")
    else:
        panel = ET.SubElement(root, "panel", label="Panel_PyAEDT_Toolkits")

    # Write a new "Panel_PyAEDT_Toolkits" sub-element.
    image_rel_path = os.path.relpath(pyaedt_lib_dir, product_toolkit_dir).replace("\\", "/") + "/"
    if image_rel_path == "./":
        image_rel_path = ""

    buttons = panel.findall("./button")
    if buttons:
        button_names = [button.attrib["label"] for button in buttons]
        if toolkitname in button_names:
            # Remove previously existing PyAEDT panel and update with newer one.
            b = [button for button in buttons if button.attrib["label"] == toolkitname][0]
            panel.remove(b)
    if isinstance(toolkit, str) and os.path.exists(toolkit):
        image_name = os.path.split(toolkit)[-1]
    else:
        image_name = toolkit["image"]
    image_abs_path = image_rel_path + "images/large/{}".format(image_name)
    ET.SubElement(
        panel,
        "button",
        label=toolkitname,
        isLarge="1",
        image=image_abs_path,
        script="{}/Run PyAEDT Toolkit Script".format(toolkitname),
    )

    # Backup any existing file if present
    if os.path.isfile(tab_config_file_path):
        shutil.copy(tab_config_file_path, tab_config_file_path + ".orig")

    write_pretty_xml(root, tab_config_file_path)

    files_to_copy = ["images/large/{}".format(image_name)]
    for file_name in files_to_copy:
        dest_file = os.path.normpath(os.path.join(pyaedt_lib_dir, file_name))
        os.makedirs(os.path.dirname(dest_file), exist_ok=True)
        if isinstance(toolkit, str):
            shutil.copy(toolkit, dest_file)
        else:
            shutil.copy(os.path.normpath(os.path.join(current_dir, file_name)), dest_file)


def remove_toolkit_config(product_toolkit_dir, toolkitname):
    """Remove a toolkit configuration file and, if needed a button in Automation menu."""
    tab_config_file_path = os.path.join(product_toolkit_dir, "TabConfig.xml")
    if not os.path.isfile(tab_config_file_path):
        return True
    try:
        tree = ET.parse(tab_config_file_path)
    except ParseError as e:
        warnings.warn("Unable to parse %s\nError received = %s" % (tab_config_file_path, str(e)))
        return
    root = tree.getroot()

    panels = root.findall("./panel")
    if panels:
        panel_names = [panel.attrib["label"] for panel in panels]
        if "Panel_PyAEDT_Toolkits" in panel_names:
            # Remove previously existing PyAEDT panel and update with newer one.
            panel = [panel for panel in panels if panel.attrib["label"] == "Panel_PyAEDT_Toolkits"][0]
        else:
            panel = ET.SubElement(root, "panel", label="Panel_PyAEDT_Toolkits")
    else:
        panel = ET.SubElement(root, "panel", label="Panel_PyAEDT_Toolkits")

    buttons = panel.findall("./button")
    if buttons:
        button_names = [button.attrib["label"] for button in buttons]
        if toolkitname in button_names:
            # Remove previously existing PyAEDT panel and update with newer one.
            b = [button for button in buttons if button.attrib["label"] == toolkitname][0]
            panel.remove(b)

    write_pretty_xml(root, tab_config_file_path)
