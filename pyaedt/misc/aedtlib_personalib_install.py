import argparse
import os
import shutil
import sys
import warnings
from xml.dom.minidom import parseString
import xml.etree.ElementTree as ET
from xml.etree.ElementTree import ParseError

current_dir = os.path.dirname(os.path.realpath(__file__))
pyaedt_path = os.path.normpath(
    os.path.join(
        current_dir,
        "..",
    )
)
sys.path.append(os.path.normpath(os.path.join(pyaedt_path, "..")))

is_linux = os.name == "posix"
is_windows = not is_linux
pid = 0


def main():
    args = parse_arguments()
    add_pyaedt_to_aedt(
        args.version, is_student_version=args.student, use_sys_lib=args.sys_lib, new_desktop_session=args.new_session
    )


def parse_arguments():
    parser = argparse.ArgumentParser(description="Install PyAEDT and setup PyAEDT toolkits in AEDT.")
    parser.add_argument(
        "--version", "-v", default="231", metavar="XY.Z", help="AEDT three-digit version (e.g. 231). Default=231"
    )
    parser.add_argument(
        "--student", "--student_version", action="store_true", help="Install toolkits for AEDT Student Version."
    )
    parser.add_argument("--sys_lib", "--syslib", action="store_true", help="Install toolkits in SysLib.")
    parser.add_argument(
        "--new_session", action="store_true", help="Start a new session of AEDT after installing PyAEDT."
    )

    args = parser.parse_args()
    args = process_arguments(args, parser)
    return args


def process_arguments(args, parser):
    if len(args.version) != 3:
        parser.print_help()
        parser.error("Version should be a three digit number (e.g. 231)")

    args.version = "20" + args.version[-3:-1] + "." + args.version[-1:]
    return args


def add_pyaedt_to_aedt(
    aedt_version, is_student_version=False, use_sys_lib=False, new_desktop_session=False, sys_dir="", pers_dir=""
):
    if not (sys_dir or pers_dir):
        from pyaedt import Desktop, settings
        from pyaedt.generic.general_methods import grpc_active_sessions

        sessions = grpc_active_sessions(aedt_version, is_student_version)
        close_on_exit = True
        if not sessions:
            if not new_desktop_session:
                print("Launching a new AEDT desktop session.")
            new_desktop_session = True
        else:
            close_on_exit = False
        settings.use_grpc_api = True
        with Desktop(
            specified_version=aedt_version,
            non_graphical=new_desktop_session,
            new_desktop_session=new_desktop_session,
            student_version=is_student_version,
            close_on_exit=close_on_exit,
        ) as d:
            desktop = sys.modules["__main__"].oDesktop
            pers1 = os.path.join(desktop.GetPersonalLibDirectory(), "pyaedt")
            pid = desktop.GetProcessID()
            # Linking pyaedt in PersonalLib for IronPython compatibility.
            if os.path.exists(pers1):
                d.logger.info("PersonalLib already mapped.")
            else:
                if is_windows:
                    os.system('mklink /D "{}" "{}"'.format(pers1, pyaedt_path))
                else:
                    os.system('ln -s "{}" "{}"'.format(pyaedt_path, pers1))
            sys_dir = d.syslib
            pers_dir = d.personallib
        if pid and new_desktop_session:
            try:
                os.kill(pid, 9)
            except:
                pass

    toolkits = ["Project"]
    # Bug on Linux 23.1 and before where Project level toolkits don't show up. Thus copying to individual design
    # toolkits.
    if is_linux and aedt_version <= "2023.1":
        toolkits = [
            "2DExtractor",
            "CircuitDesign",
            "HFSS",
            "HFSS-IE",
            "HFSS3DLayoutDesign",
            "Icepak",
            "Maxwell2D",
            "Maxwell3D",
            "Q3DExtractor",
            "Mechanical",
        ]

    for product in toolkits:
        if use_sys_lib:
            try:
                sys_dir = os.path.join(sys_dir, "Toolkits")
                install_toolkit(sys_dir, product, aedt_version)
                print("Installed toolkit for {} in sys lib.".format(product))
                # d.logger.info("Installed toolkit for {} in sys lib.".format(product))

            except IOError:
                pers_dir = os.path.join(pers_dir, "Toolkits")
                install_toolkit(pers_dir, product, aedt_version)
                print("Installed toolkit for {} in sys lib.".format(product))
                # d.logger.info("Installed toolkit for {} in personal lib.".format(product))
        else:
            pers_dir = os.path.join(pers_dir, "Toolkits")
            install_toolkit(pers_dir, product, aedt_version)
            print("Installed toolkit for {} in sys lib.".format(product))
            # d.logger.info("Installed toolkit for {} in personal lib.".format(product))


def install_toolkit(toolkit_dir, product, aedt_version):
    tool_dir = os.path.join(toolkit_dir, product, "PyAEDT")
    lib_dir = os.path.join(tool_dir, "Lib")
    toolkit_rel_lib_dir = os.path.relpath(lib_dir, tool_dir)
    # Bug on Linux 23.1 and before where Project level toolkits don't show up. Thus copying to individual design
    # toolkits.
    if is_linux and aedt_version <= "2023.1":
        toolkit_rel_lib_dir = os.path.join("Lib", "PyAEDT")
        lib_dir = os.path.join(toolkit_dir, toolkit_rel_lib_dir)
        toolkit_rel_lib_dir = "../../" + toolkit_rel_lib_dir
        tool_dir = os.path.join(toolkit_dir, product, "PyAEDT")
    os.makedirs(lib_dir, exist_ok=True)
    os.makedirs(tool_dir, exist_ok=True)
    files_to_copy = ["Console", "Run_PyAEDT_Script", "Jupyter"]
    # Remove hard-coded version number from Python virtual environment path, and replace it with the corresponding AEDT
    # version's Python virtual environment.
    version_agnostic = False
    if aedt_version[2:6].replace(".", "") in sys.executable:
        executable_version_agnostic = sys.executable.replace(aedt_version[2:6].replace(".", ""), "%s")
        version_agnostic = True
    else:
        executable_version_agnostic = sys.executable
    jupyter_executable = executable_version_agnostic.replace("python" + exe(), "jupyter" + exe())
    ipython_executable = executable_version_agnostic.replace("python" + exe(), "ipython" + exe())
    for file_name in files_to_copy:
        with open(os.path.join(current_dir, file_name + ".py_build"), "r") as build_file:
            file_name_dest = file_name.replace("_", " ") + ".py"
            with open(os.path.join(tool_dir, file_name_dest), "w") as out_file:
                print("Building to " + os.path.join(tool_dir, file_name_dest))
                build_file_data = build_file.read()
                build_file_data = (
                    build_file_data.replace("##TOOLKIT_REL_LIB_DIR##", toolkit_rel_lib_dir)
                    .replace("##PYTHON_EXE##", executable_version_agnostic)
                    .replace("##IPYTHON_EXE##", ipython_executable)
                    .replace("##JUPYTER_EXE##", jupyter_executable)
                )
                if not version_agnostic:
                    build_file_data = build_file_data.replace(" % version", "")
                out_file.write(build_file_data)
    shutil.copyfile(os.path.join(current_dir, "console_setup.py"), os.path.join(lib_dir, "console_setup.py"))
    shutil.copyfile(
        os.path.join(current_dir, "jupyter_template.ipynb"),
        os.path.join(lib_dir, "jupyter_template.ipynb"),
    )
    if aedt_version >= "2023.2":
        write_tab_config(os.path.join(toolkit_dir, product), lib_dir)


def write_tab_config(product_toolkit_dir, pyaedt_lib_dir, force_write=False):
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
        if "Panel_PyAEDT" in panel_names:
            # Remove previously existing PyAEDT panel and update with newer one.
            panel = [panel for panel in panels if panel.attrib["label"] == "Panel_PyAEDT"][0]
            root.remove(panel)

    # Write a new "Panel_PyAEDT" sub-element.
    panel = ET.SubElement(root, "panel", label="Panel_PyAEDT")
    gallery = ET.SubElement(panel, "gallery", imagewidth="120", imageheight="72")
    image_rel_path = os.path.relpath(pyaedt_lib_dir, product_toolkit_dir).replace("\\", "/") + "/"
    if image_rel_path == "./":
        image_rel_path = ""
    ET.SubElement(gallery, "button", label="PyAEDT", isLarge="1", image=image_rel_path + "images/large/pyansys.png")
    group = ET.SubElement(gallery, "group", label="PyAEDT Menu", image=image_rel_path + "images/gallery/PyAEDT.png")
    ET.SubElement(group, "button", label="Console", script="PyAEDT/Console")
    ET.SubElement(group, "button", label="Jupyter Notebook", script="PyAEDT/Jupyter")
    ET.SubElement(group, "button", label="Run PyAEDT Script", script="PyAEDT/Run PyAEDT Script")

    # Backup any existing file if present
    if os.path.isfile(tab_config_file_path):
        shutil.copy(tab_config_file_path, tab_config_file_path + ".orig")

    write_pretty_xml(root, tab_config_file_path)

    files_to_copy = ["images/large/pyansys.png", "images/gallery/PyAEDT.png"]
    for file_name in files_to_copy:
        dest_file = os.path.normpath(os.path.join(pyaedt_lib_dir, file_name))
        os.makedirs(os.path.dirname(dest_file), exist_ok=True)
        shutil.copy(os.path.normpath(os.path.join(current_dir, file_name)), dest_file)


def write_pretty_xml(root, file_path):
    """Write the XML in a pretty format."""
    # If we use the commented code below, then the previously existing lines will have double lines added. We need to
    # split and ignore the double lines.
    # xml_str = parseString(ET.tostring(root)).toprettyxml(indent=" " * 4)
    lines = [line for line in parseString(ET.tostring(root)).toprettyxml(indent=" " * 4).split("\n") if line.strip()]
    xml_str = "\n".join(lines)

    with open(file_path, "w") as f:
        f.write(xml_str)


def exe():
    if is_windows:
        return ".exe"
    return ""


if __name__ == "__main__":
    main()
