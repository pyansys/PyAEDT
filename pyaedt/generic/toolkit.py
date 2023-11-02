"""Toolkit Module.

This module contains a number of classes designed to support development of WPF GUI-based toolkits for AEDT
applications. The primary classes are:

    WPFToolkit             : Base Class to support UI Toolkit development
    WPFToolkitSettings     : Class to support UI settings for testing purposes
    ToolkitBuilder          : Class to support generation of a zip package with all needed dependencies

Examples
--------
**Example 1**
A toolkit is built by deriving a class called ApplicationWindow from WPFToolkit.
Parallel to this file, an xaml file should be present in the same directory.


>>> from pyaedt import Maxwell2d
>>> from pyaedt.generic.toolkit import WPFToolkit, launch

>>> class ApplicationWindow(WPFToolkit):
>>>
>>>     def __init__(self):
>>>         WPFToolkit.__init__(self, toolkit_file=__file__, aedt_design=Maxwell2d(), parent_design_name=None)
>>>         # Copy Xaml template
>>>         self.copy_xaml_template()

>>>         #Edit the UI
>>>        self.add_label("label1", "Input Parameter 1", 10, 10)
>>>        self.add_text_box(name="_input1", x_pos=150, y_pos=10, callback_method=self.validate_positive_float,
>>>                          callback_action='LostFocus')
>>>        self.add_label("label2", "Design Name", 10, 50)
>>>        self.add_text_box(name="_input2", x_pos=150, y_pos=50, callback_method=self.validate_string_no_spaces,
>>>                          callback_action='LostFocus')
>>>        self.add_check_box(name="_check1", content="Save Project", x_pos=150, y_pos=80,
>>>                           callback_method=self.enable_checkbox, callback_action="Checked")
>>>        self.add_combo_box(name="_combo1", x_pos=150, y_pos=120, callback_method=self.print_design_name)
>>>        self.add_button("run_method", "Click To Run", x_pos=300, y_pos=300, callback_method=self.custom_callback)
>>>        self.add_label("label3", "Design Type", 10, 150)
>>>        self.add_text_box(name="_input3", x_pos=150, y_pos=150)
>>>
>>>         #Launch the UI
>>>        self.launch_gui()
>>>
>>>         # Setup Additional Callbacks
>>>         self.add_combo_items("_combo1", self.aedtdesign.design_list)

>>>
>>>         # Get Values from UI
>>>         value1 = self.ui.float_value("_input1")
>>>         value2 = self.ui.text_value("_input2")
>>>
>>>     def custom_callback(self, sender, e):
>>>         self.aedtdesign.design_name = self.ui.text_value("_input2")
>>>         self.aedtdesign["param"] = self.ui.float_value("_input1")
>>>         print(self.ui.float_value("_input1"))
>>>         print(self.ui.text_value("_input2"))
>>>
>>>     def print_design_name(self, sender, e):
>>>         self.set_text_value("_input3", self.aedtdesign.solution_type)
>>>
>>>    def enable_checkbox(self, sender, e):
>>>        print("Enabled")
>>>
>>>    def disable_checkbox(self, sender, e):
>>>        print("Disabled")
>>> # Launch the toolkit
>>> if __name__ == '__main__':
>>>     launch(__file__, specified_version="2021.2", new_desktop_session=False, autosave=False)

"""
from datetime import datetime
import json
import os
import shutil
import sys
from zipfile import ZIP_DEFLATED, ZipFile

from pyaedt import is_ironpython, is_linux, is_windows
from pyaedt.desktop import Desktop
import pyaedt.edb_core.edb_data.simulation_configuration
from pyaedt.generic.clr_module import _clr
from pyaedt.generic.general_methods import pyaedt_function_handler

if is_linux and is_ironpython:
    import subprocessdotnet as subprocess
else:
    import subprocess

if is_ironpython:
    _clr.AddReference("PresentationFramework")
    _clr.AddReference("PresentationCore")
    _clr.AddReference("System.Windows")
    _clr.AddReference("System.Windows.Forms")
    _clr.AddReference("System.Drawing")
else:
    _clr.AddReference("System.Xml")
    _clr.AddReference("PresentationFramework, Version=3.0.0.0, Culture=neutral, PublicKeyToken=31bf3856ad364e35")
    _clr.AddReference("PresentationCore, Version=3.0.0.0, Culture=neutral, PublicKeyToken=31bf3856ad364e35")
    _clr.AddReference("System.Windows.Forms")
    _clr.AddReference("System")
    from System.IO import StreamReader
    from System.Windows.Markup import XamlReader

    _clr.AddReference("System.Windows")

from System import Environment, Uri, UriKind
from System.Drawing import Point, Size
from System.Threading import ApartmentState, Thread, ThreadStart
from System.Windows import Application, Input, LogicalTreeHelper, Thickness, Visibility, Window
from System.Windows.Forms import (
    Button,
    DialogResult,
    FolderBrowserDialog,
    Form,
    FormBorderStyle,
    ListBox,
    MessageBox,
    MessageBoxButtons,
    MessageBoxIcon,
    OpenFileDialog,
    SelectionMode,
    StatusBar,
)
from System.Windows.Media import Brushes
from System.Windows.Media.Imaging import BitmapCacheOption, BitmapCreateOptions, BitmapImage


@pyaedt_function_handler()
def select_file(initial_dir=None, filter=None):
    """Opens File Dialog and select a file.

    Parameters
    ----------
    initial_dir : str
        Initial dir where to look for file.
    filter : str
        Filter for file search.

    Returns
    -------
    str
        File full path.
    """
    browser = OpenFileDialog()
    browser.Title = "Select a file with optional filter and directory"
    if initial_dir:
        browser.InitialDirectory = initial_dir
    if filter:
        browser.Filter = filter
    ret_val = browser.ShowDialog()
    if ret_val == DialogResult.OK:
        return browser.FileName
    else:
        return None


@pyaedt_function_handler()
def select_directory(initial_dir=None, description=None):
    """Opens File Dialog and select a directory.

    Parameters
    ----------
    initial_dir : str
        Initial dir where to look for.
    description : str
        Dialog description.

    Returns
    -------
    str
        Directory full path.
    """
    browser = FolderBrowserDialog()

    if initial_dir:
        browser.RootFolder = Environment.SpecialFolder.Desktop
        browser.SelectedPath = initial_dir
    if description:
        browser.Description = description
    else:
        browser.Description = "Select an empty folder to create the toolkit"

    test = browser.ShowDialog()
    if test == DialogResult.OK:
        return browser.SelectedPath
    else:
        return None


@pyaedt_function_handler()
def copy_files_mkdir(root, files_in_subdir):
    """Copies all files from source to destination in a root path.

    Parameters
    ----------
    root : str
        Root Path where copy new files.
    files_in_subdir : dict
        Dictionary of source and destinations files. key is source, value is destination

    Returns
    -------
    bool
        ``True`` when successful, ``False`` when failed.
    """
    if not os.path.exists(root):
        os.mkdir(root)
    for src_file, dest_file in files_in_subdir.items():
        shutil.copyfile(src_file, dest_file)
    return True


@pyaedt_function_handler()
def launch(
    workflow_module, specified_version=None, new_desktop_session=True, autosave=False, close_desktop_on_exit=False
):
    """Launches the ApplicationWindow class for the given module name which must lie within the path scope of
        the calling toolkit. Optionally the version can be specified in the form 20xx.y, e.g. 2021.2,
        IronPython calls the run_application function of the ApplicationThread class.
        For CPython, a Thread with Apartment State is generated to adhere to requirements of System.Windows


    Parameters
    ----------
    workflow_module : __file__
    name of the module file containing the application.
    specified_version : str
        Specified version of Desktop to launch
    new_desktop_session : bool
        Define if new Desktop session has always to be opened.
    autosave : bool
        Enable or disable autosave.
    close_desktop_on_exit : bool
        Define if Desktop has to be closed on exit.
    """
    sys.path.append(os.path.dirname(workflow_module))
    app = ApplicationThread(workflow_module, specified_version, new_desktop_session, autosave, close_desktop_on_exit)

    if sys.implementation.name != "ironpython":
        thread = Thread(ThreadStart(app.run_application))
        thread.SetApartmentState(ApartmentState.STA)
        thread.Start()
        thread.Join()
    else:
        if specified_version:
            app.run_application()
        else:
            app.open_form()


launch_script = """
import os
import sys

try:
    specified_version = sys.argv[1]
except IndexError:
    specified_version = None

# Ensure that this launch directory is included to the search path (needed for IronPython under AEDT)
toolkit_directory = os.path.abspath(os.path.dirname(__file__))
toolkit_lib_directory = os.path.join(toolkit_directory, 'lib')
sys.path.append(toolkit_directory)
sys.path.append(toolkit_lib_directory)

from lib.AEDTLib.Toolkit import launch
launch('{}', version=specified_version)
"""


@pyaedt_function_handler()
def message_box(text, caption=None, buttons=None, icon=None):
    """Displays Message Box.

    Parameters
    ----------
    text : str
        Main text of the message
    caption : str
        Caption of the window
    buttons : str
        Button type string (OK, OKCancel, YesNoCancel, YesNo).
    icon : str
        Valid icon type string.  Asterisk, Error, Exclamation, Hand, Information, None, Question, Stop, Warning
    """
    if not icon:
        icon_object = getattr(MessageBoxIcon, "Information")
    else:
        icon_object = getattr(MessageBoxIcon, "Information")

    if not caption:
        caption = ""

    if not buttons:
        buttons_object = MessageBoxButtons.OK
    else:
        buttons_object = getattr(MessageBoxButtons, buttons)

    result = MessageBox.Show(text, caption, buttons_object, icon_object)
    return result


class ToolkitBuilder:
    """Helps to create a deployable zip file of the application and any dependencies that are not available via pip.

    Parameters
    ----------
        local_path : str
            Path of the top-level toolkit files containing the *.py and *.xaml files.
            Optionally a file located in the toolkit directory (typically __file__)
            can also be given.

        app_name : str, optional
            Name of the toolkit (optional).
            If not defined, then the name of the parent directory is used.

    Examples
    --------
    Build file placed in the Toolkit directory

    >>> from pyaedt.generic.toolkit import ToolkitBuilder
    >>>  bld = ToolkitBuilder(__file__)
    >>>  bld.copy_from_local(extension=['py', 'xaml'])
    >>>  bld.copy_from_repo(sub_dir='pyaedt')
    >>>  bld.zip_archive()
    """

    def __init__(self, local_path, app_name=None):
        """Instantiates a ToolkitBuilder object. This object manages the packaging of the WPF GUI to ensure
        that any dependencies not available via pip are stored with the toolkit deployable asset.
        """
        # if the local_path is defined as a file, take the path of that file
        if os.path.isfile(local_path):
            self.local_path = os.path.dirname(os.path.realpath(local_path))
        else:
            self.local_path = local_path

        if app_name:
            self.py_name = app_name
        else:
            self.py_name = os.path.basename(os.path.dirname(os.path.realpath(local_path)))

        self.toolkit_path = os.path.join(self.local_path, "..")

        # Extract the commit ID from the global repository
        self.global_lib_path = os.path.abspath(os.path.join(self.local_path, "..", "..", ".."))
        os.chdir(self.global_lib_path)
        command = ["git", "rev-parse", "HEAD"]
        sh = False
        res = subprocess.check_output(command, shell=sh).rstrip()

        # Create a directory called 'build' in the xml directory
        self.build_path = os.path.join(self.local_path, ".build")
        if not os.path.isdir(self.build_path):
            os.mkdir(self.build_path)

        # Create a drectory named by the datetime (remove contents if already exists)
        self.build_name = "{0}-{date:%Y%m%d_%H%M}".format(self.py_name, date=datetime.now())
        self.commit_path = os.path.join(self.build_path, self.build_name)
        self.commit_lib_path = os.path.join(self.commit_path, "lib")
        if os.path.isdir(self.commit_path):
            shutil.rmtree(self.commit_path)
        os.mkdir(self.commit_path)
        os.mkdir(self.commit_lib_path)

        # Add the commit hash to the module __init__.py files
        init_files = []
        init_files.append(os.path.join(self.commit_lib_path, "__init__.py"))
        for file in init_files:
            with open(file, "w") as f:
                f.write("#{0}\n".format(res))

        # Create a launch file
        script_file = os.path.join(self.commit_path, "launch.py")
        with open(script_file, "w") as f:
            f.write(launch_script.format(self.py_name))

    def copy_from_local(self, extension=None, ignore_dir=None):
        """Copies recursively all files in the local directory and all subdirectories of a given list of
            extensions

        :param extension: list of extensions to be copied, e.g. ['py', 'xaml']
        :param ignore_dir: boolean: ignore directories starting with "." or "_"
        """
        self.copy_from_repo(self.local_path, extension=extension, ignore_dir=ignore_dir)

    def copy_from_repo(self, root_dir=None, sub_dir=None, extension=None, ignore_dir=None):
        """Copies recursively all files from a specified root directory and all subdirectories of a given list of
            extensions

        :param root_dir: optional root directory to copy from, default is the AnsysAutomation repository
        :param sub_dir: optional specific sub-directory within the root directory
        :param extension: list of extensions to be copied, e.g. ['py', 'xaml']
        :param ignore_dir: boolean: ignore directories starting with "." or "_"
        """
        if not extension:
            extension = ["py"]
        elif isinstance(extension, str):
            extension = [extension]
        assert isinstance(extension, list), "Extension input parameter must be a string or a list"

        if not ignore_dir:
            ignore_dir = [".", "_"]
        elif isinstance(ignore_dir, str):
            extension = [ignore_dir]
        assert isinstance(ignore_dir, list), "Extension input parameter must be a string or a list"

        if not root_dir:
            root_dir = self.global_lib_path
        walk_dir = root_dir
        if sub_dir:
            if isinstance(sub_dir, str):
                sub_dir = [sub_dir]
            assert isinstance(sub_dir, list), "sub_dir must be a list or a string"
            for x in sub_dir:
                walk_dir = os.path.join(walk_dir, x)

        ignored_paths = []
        for root, dir, files in os.walk(walk_dir):
            ignore_path = False
            if ignore_dir:
                for x in ignore_dir:
                    if os.path.basename(root).startswith(x):
                        ignored_paths.append(root)
                        ignore_path = True
                        break
                for x in ignored_paths:
                    if root.startswith(x):
                        ignore_path = True
                        break
            if not ignore_path:
                files_in_subdir = {}
                dest_dir = root.replace(root_dir, self.commit_lib_path)
                for name in files:
                    for ext in extension:
                        if name.endswith((ext)):
                            src_file = os.path.join(root, name)
                            dst_file = src_file.replace(root_dir, self.commit_lib_path)
                            files_in_subdir[src_file] = dst_file
                            break
                copy_files_mkdir(dest_dir, files_in_subdir)

    def zip_archive(self):
        """Zip the collected data in the build path"""
        zip_archive = os.path.join(self.build_path, self.build_name + ".zip")
        with ZipFile(zip_archive, "w", ZIP_DEFLATED) as myzip:
            for root, dirs, files in os.walk(self.commit_path):
                for filename in files:
                    abs_path = os.path.join(root, filename)
                    rel_path = os.path.relpath(abs_path, self.commit_path)
                    myzip.write(abs_path, arcname=rel_path)

        # remove the commit directory
        shutil.rmtree(self.commit_path)


class ApplicationThread:
    """Class to allow data to be passed to the run_application member function in a new thread.
    The run_application function connects to Desktop and instantiates an ApplicationWindow
    object of the calling module
    """

    def __init__(self, workflow_module, version, new_desktop_session=True, autosave=False, close_desktop_on_exit=False):
        self.workflow_module = os.path.basename(workflow_module).replace(".py", "")
        self.version = version
        self.autosave = autosave
        self.new_desktop = new_desktop_session
        self.close_desktop_on_exit = close_desktop_on_exit

    @pyaedt_function_handler()
    def run_application(self):
        """Starts the application and run WPF."""
        d = Desktop(self.version, new_desktop_session=self.new_desktop)
        if self.autosave:
            d.enable_autosave()
        else:
            d.disable_autosave()
        form_object = __import__(self.workflow_module)
        with form_object.ApplicationWindow() as form:
            form.display()
            print(self.close_desktop_on_exit)
            if self.close_desktop_on_exit:
                d.release_desktop(True, True)
            else:
                d.release_desktop(False, False)

    @pyaedt_function_handler()
    def open_form(self):
        """Opens the Application Windows Form."""
        form_object = __import__(self.workflow_module)
        with form_object.ApplicationWindow() as form:
            form.display()


# Manages the settings data for the toolkit
class WPFToolkitSettings:
    """This class provides a minimal implementation of the Toolkit providing assess to the
    settings file and allowing to call the toolkit_functionality without the
    GUI to speed up debugging (or potentially to deploy the function in batch mode.

    Examples
    --------
    Typical usage looks like this

    >>> with Desktop(version="2021.2") as d:
    >>>    app = WPFToolkitSettings(toolkit_file=__file__, aedt_app=Maxwell2d())
    >>>    app.settings_data = {'param 1': 3, 'param 2': 'house' }
    >>>    toolkit_function(app)
    """

    def __init__(self, aedtdesign=None, working_directory=None, toolkit_name=None):
        if aedtdesign:
            self._parent = aedtdesign
            self._working = None
        elif working_directory:
            assert os.path.exists(working_directory), "Working Directory {} does not exist"
            self._working = working_directory
        else:
            self._parent = None
            self._working = None
            # raise Exception("Toolkit name/file not defined")

        self.toolkit_name = toolkit_name

    @property
    def settings_file(self):
        """Settings json file path."""
        return os.path.join(self.settings_path, self.toolkit_name + "_Settings.json")

    @property
    def results_path(self):
        """Results folder path."""
        return os.path.join(self._parent.working_directory, "_results")

    @property
    def data_path(self):
        """Data folder path."""
        return os.path.join(self._working, "_data")

    @property
    def local_path(self):
        """Working folder path."""
        if self._working:
            return self._working
        else:
            return self._parent.working_directory

    @property
    def settings_path(self):
        """Working directory of the parent design - checks the current design settings
        file for the key "parent" to find the name of the parent design
        """
        my_path = self.local_path
        my_settings_file = os.path.join(self.local_path, self.toolkit_name + "_Settings.json")
        if os.path.exists(my_settings_file):
            settings_data = self.read_settings_file(my_settings_file)
            if "parent" in settings_data:
                if settings_data["parent"]:
                    my_dir = os.path.basename(my_path)
                    my_path = my_path.replace(my_dir, settings_data["parent"])
        return my_path

    @pyaedt_function_handler()
    def read_settings_file(self, filename):
        """Read the json file and returns dictionary."""
        with open(filename, "r") as f:
            try:
                settings_data = json.load(f)
            except ValueError:
                try:
                    msg_string = "Invalid json file {0} will be overwritten.".format(filename)
                    self._parent.logger.warning(msg_string)
                except:
                    pass
                return None
        return settings_data

    @property
    def settings_data(self):
        """Reads the json file and returns dictionary."""
        settings_file = self.settings_file
        if os.path.exists(settings_file):
            return self.read_settings_file(self.settings_file)
        else:
            return {"parent": None}

    @pyaedt_function_handler()
    def append_toolkit_dir(self):
        """Appends toolkit directory to sys.path."""
        assert os.path.exists(self.settings_file), "Settings File not defined!"
        try:
            toolkit_dir = self.settings_data["_toolkit_dir"]
            sys.path.append(toolkit_dir)
        except KeyError:
            pass


class ListBoxForm(Form):
    @property
    def ResultOK(self):
        if self.DialogResult == DialogResult.OK:
            return True
        else:
            return False

    def __init__(self, list_items, default_item=None):
        self.MinimizeBox = False
        self.MaximizeBox = False
        self.Text = "Select Export Objects"

        self.lb = ListBox()
        self.lb.Parent = self
        for item in list_items:
            self.lb.Items.Add(item)
        self.lb.Location = Point(10, 10)
        self.lb.Size = Size(200, 250)
        self.lb.SelectedIndexChanged += self.OnChanged
        self.lb.SelectionMode = SelectionMode.MultiExtended
        self.sb = StatusBar()
        self.sb.Parent = self
        self.Size = Size(300, 350)
        self.CenterToScreen()

        # Define the border style of the form to a dialog box.
        self.FormBorderStyle = FormBorderStyle.FixedDialog
        button1 = Button()
        button2 = Button()

        # Set the text of button1 to "OK".
        button1.Text = "OK"
        button2.Text = "Cancel"

        button1.Location = Point(10, self.lb.Bottom + 5)
        button2.Location = Point(button1.Left + button1.Width + 10, button1.Top)

        button1.DialogResult = DialogResult.OK
        button2.DialogResult = DialogResult.Cancel

        self.AcceptButton = button1
        self.CancelButton = button2

        # Add buttons to the form.
        self.Controls.Add(button1)
        self.Controls.Add(button2)

        if default_item:
            if default_item in self.lb.Items:
                index_of_default_item = self.lb.Items.IndexOf(default_item)
                self.lb.SelectedIndex = index_of_default_item

    def OnChanged(self, sender, event):
        self.sb.Text = ";".join(sender.SelectedItems)


class UIObjectGetter:
    """Child class of a parent supplying a get_ui_object function returning a WPF GUI object.
    The class implementa a __getitem__ method to allow for accessing the GUI objects from the parent class
    through the syntax:
    parent.UIObjectGetter[ui_object_name]

    Additionally methods are provided to extract specific data types from the GUI object:
    float_value
    text_value
    """

    def __init__(self, parent):
        self.parent = parent

    def __getitem__(self, ui_object_name):
        return self.parent.get_ui_object(ui_object_name)

    @pyaedt_function_handler()
    def float_value(self, ui_object_name):
        """Converts the text entry to a float and return the value. If the string is empty, return 0

        Parameters
        ----------
        ui_object_name : str
            Name of UI object.

        Returns
        -------
        float
        """
        text_value = self[ui_object_name].Text
        if not text_value:
            return 0
        else:
            return float(text_value)

    def text_value(self, ui_object_name):
        """Converts the text entry to a string and return the value. If the string is empty, return 0

        Parameters
        ----------
        ui_object_name : str
            Name of UI object.

        Returns
        -------
        str
        """
        return self[ui_object_name].Text


class WPFToolkit(Window):
    """This class provides a base class allowing the creation of a WPF-GUI-Based toolkit for AEDT.
    This class provides functionality for launching the GUI, reading and writing to settings
    files, path handling and error handling.
    Data validation functions are also provided as callbacks from the WPF GUI
    """

    def __init__(self, toolkit_file, aedt_design=None, parent_design_name=None):
        self.toolkit_file = toolkit_file
        self._aedtdesign = None
        self.aedtdesign = aedt_design
        self.parent_design_name = parent_design_name
        self.window = None
        self.ui = UIObjectGetter(self)
        my_path = os.path.abspath(os.path.dirname(__file__))
        self.toolkit_directory = os.path.abspath(os.path.dirname(toolkit_file))
        self.aedtlib_directory = os.path.abspath(os.path.join(my_path, ".."))
        sys.path.append(self.toolkit_directory)
        sys.path.append(self.aedtlib_directory)
        self.image_path = os.path.join(self.aedtlib_directory, "misc")

        self.dsoconfigfile = os.path.join(self.toolkit_directory, "dso.cfg")

        # Read existing settings and update the library path
        self._read_and_synch_settings_file()
        self._callbacks = []
        # LOCAL_INSTALL = self.aedtdesign.odesktop.GetExeDir()
        # self.desktopjob = os.path.join(LOCAL_INSTALL, "desktopjob.exe")

    @property
    def aedtdesign(self):
        """Return Aedt Object."""
        return self._aedtdesign

    @aedtdesign.setter
    def aedtdesign(self, design):
        my_path = os.path.abspath(os.path.dirname(__file__))
        self._aedtdesign = design
        self.toolkit_name = os.path.basename(self.toolkit_file).replace(".py", "")
        if self._aedtdesign:
            self.settings_manager = WPFToolkitSettings(aedtdesign=self._aedtdesign, toolkit_name=self.toolkit_name)
            self._parent_design_name = self._aedtdesign.design_name
        else:
            self.settings_manager = WPFToolkitSettings(working_directory=my_path, toolkit_name=self.toolkit_name)
            self._parent_design_name = None

    @property
    def parent_design_name(self):
        """Aedt Design Name."""
        if self.aedtdesign:
            self._parent_design_name = self.aedtdesign.design_name
        else:
            self._parent_design_name = None
        return self._parent_design_name

    @parent_design_name.setter
    def parent_design_name(self, design_name=None):
        if not self.aedtdesign:
            self._parent_design_name = None
        elif design_name:
            self._parent_design_name = design_name
            if design_name not in self.aedtdesign.design_list:
                orig_design_name = self.aedtdesign.design_name
                if self._parent_design_name != orig_design_name:
                    self._write_parent_link()
                    self.aedtdesign.duplicate_design(self._parent_design_name)
                    self.aedtdesign.save_project()
            else:
                self.aedtdesign.set_active_design(design_name)
        else:
            self._parent_design_name = self.aedtdesign.design_name

    @property
    def results_path(self):
        """Results folder path."""
        return os.path.join(self.aedtdesign.working_directory, "_results")

    @property
    def data_path(self):
        """Data folder path."""
        return os.path.join(self.aedtdesign.working_directory, "_data")

    @property
    def local_path(self):
        """Local folder path."""
        return self.settings_manager.local_path

    @property
    def settings_file(self):
        """Settings json file path."""
        try:
            return self.settings_manager.settings_file
        except:
            return ""

    @property
    def settings_data(self):
        """Settings json file data."""
        try:
            return self.settings_manager.settings_data
        except:
            return None

    @property
    def local_settings_file(self):
        """Settings json file path."""
        return self.settings_manager.settings_file

    @property
    def settings_path(self):
        """Settings json folder path."""
        return self.settings_manager.settings_path

    @property
    def xaml_file(self):
        """Wpf xaml file path."""
        return os.path.join(self.toolkit_directory, self.toolkit_name + ".xaml")

    @pyaedt_function_handler()
    def copy_xaml_template(self):
        """Copies the xaml template to local folder and rename it to be used with current application."""
        local_path = os.path.abspath(os.path.dirname(__file__))
        print("xaml file = {}".format(self.xaml_file))
        shutil.copy2(os.path.join(local_path, "wpf_template.xaml"), self.xaml_file)
        return True

    @pyaedt_function_handler()
    def _add_line_to_xml(self, line_to_add):
        with open(self.xaml_file, "r") as file:
            file = file.readlines()
        with open(self.xaml_file[:-5] + "_tmp.xaml", "w") as f:
            for line in file:
                if "</Grid>" in line:
                    f.write(line_to_add + "\n")
                f.write(line)
        shutil.move(self.xaml_file[:-5] + "_tmp.xaml", self.xaml_file)

    @pyaedt_function_handler()
    def edit_window_size(self, width=800, height=600, title="PyAEDT WPF Application", background="#FFD1CFCF"):
        """Edit the Wpf windows size.

        Parameters
        ----------
        width : int, optional
            Windows width.
        height : int, optional
            Windows height.
        title : str, optional
            Windows title.
        background : str, optional
            Windows color in hex mode.

        Returns
        -------
        bool
            `True` if succeeded.
        """
        with open(self.xaml_file, "r") as file:
            file = file.readlines()
        line_to_add = '        Title="{}" Height="{}" Width="{}" Background="{}">'.format(
            title, height, width, background
        )

        with open(self.xaml_file[:-5] + "_tmp.xaml", "w") as f:
            for line in file:
                if "       Title=" in line:
                    f.write(line_to_add + "\n")
                else:
                    f.write(line)
        shutil.move(self.xaml_file[:-5] + "_tmp.xaml", self.xaml_file)
        return True

    @pyaedt_function_handler()
    def add_label(self, name, content, x_pos, y_pos):
        """Adds a label to Wpf.

        Parameters
        ----------
        name : str
            Name of the label.
        content : str
            Content of the label.
        x_pos : float
            Horizontal position in UI.
        y_pos : float
            Vertical position in UI.

        Returns
        -------
        bool
        """
        new_label = '        <Label x:Name="{}" Content="{}" HorizontalAlignment="Left" '.format(name, content)
        new_label += 'Margin="{},{},0,0" VerticalAlignment="Top"/>'.format(x_pos, y_pos)
        self._add_line_to_xml(new_label)
        return True

    @pyaedt_function_handler()
    def add_text_box(self, name, x_pos, y_pos, width=120, callback_method=None, callback_action="LostFocus"):
        """Adds a text box to Wpf.

        Parameters
        ----------
        name : str
            Name of the text box.
        x_pos : float
            Horizontal position in UI.
        y_pos : float
            Vertical position in UI.
        width : float
            Width of the text box.
        callback_method : func
            Name of the method assigned to the call back action. `None` to disable it.
        callback_action : str, optional
            Call back action on which callback will be applied. Default is `"Click"`.

        Returns
        -------
        bool
        """
        new_label = '        <TextBox x:Name="{}" HorizontalAlignment="Left" Height="23" '.format(name)
        new_label += 'Margin="{},{},0,0" TextWrapping="Wrap" VerticalAlignment="Top" Width="{}"/>'.format(
            x_pos, y_pos, width
        )
        if callback_method:
            self._callbacks.append([name, callback_action, callback_method])
        self._add_line_to_xml(new_label)
        return True

    @pyaedt_function_handler()
    def add_combo_box(self, name, x_pos, y_pos, width=120, callback_method=None, callback_action="SelectionChanged"):
        """Adds a combo box to Wpf.

        Parameters
        ----------
        name : str
            Name of the combo.
        x_pos : float
            Horizontal position in UI.
        y_pos : float
            Vertical position in UI.
        width : float
            Width of the combo box.
        callback_method : func
            Name of the method assigned to the call back action. `None` to disable it.
        callback_action : str, optional
            Call back action on which callback will be applied. Default is `"Click"`.

        Returns
        -------
        bool
        """
        new_label = '        <ComboBox x:Name="{}" HorizontalAlignment="Left" Height="23" '.format(name)
        new_label += 'Margin="{},{},0,0" VerticalAlignment="Top" Width="{}"/>'.format(x_pos, y_pos, width)
        if callback_method:
            self._callbacks.append([name, callback_action, callback_method])
        self._add_line_to_xml(new_label)
        return True

    @pyaedt_function_handler()
    def add_check_box(self, name, content, x_pos, y_pos, callback_method=None, callback_action="Checked"):
        """Adds a check box to Wpf.

        Parameters
        ----------
        name : str
            Name of the check.
        content : str
            Caption of the check box.
        x_pos : float
            Horizontal position in UI.
        y_pos : float
            Vertical position in UI.
        callback_method : func
            Name of the method assigned to the call back action. `None` to disable it.
        callback_action : str, optional
            Call back action on which callback will be applied. Default is `"Click"`.

        Returns
        -------
        bool
        """
        new_label = '        <CheckBox x:Name="{}" Content="{}" HorizontalAlignment="Left" '.format(name, content)
        new_label += 'Margin="{},{},0,0" VerticalAlignment="Top"/>'.format(x_pos, y_pos)
        if callback_method:
            self._callbacks.append([name, callback_action, callback_method])
        self._add_line_to_xml(new_label)
        return True

    @pyaedt_function_handler()
    def add_button(self, name, content, x_pos, y_pos, width=120, callback_method=None, callback_action="Click"):
        """Adds a button to Wpf.

        Parameters
        ----------
        name : str
            Name of the button.
        content : str
            Caption of the button box.
        x_pos : float
            Horizontal position in UI.
        y_pos : float
            Vertical position in UI.
        width : float
            Button width.
        callback_method : func
            Name of the method assigned to the call back action. `None` to disable it.
        callback_action : str, optional
            Call back action on which callback will be applied. Default is `"Click"`.

        Returns
        -------
        bool
        """
        new_label = '        <Button x:Name="{}" Content="{}" HorizontalAlignment="Left" '.format(name, content)
        new_label += 'Margin="{},{},0,0" VerticalAlignment="Top" Width="{}"/>'.format(x_pos, y_pos, width)
        if callback_method:
            self._callbacks.append([name, callback_action, callback_method])
        self._add_line_to_xml(new_label)
        return True

    @pyaedt_function_handler()
    def launch_gui(self):
        """Shows the Wpf UI."""
        if sys.implementation.name == "ironpython":
            _clr.AddReference("IronPython.wpf")
            import wpf

            wpf.LoadComponent(self, self.xaml_file)
            self.window = self
        else:
            stream = StreamReader(self.xaml_file)
            self.window = XamlReader.Load(stream.BaseStream)

        workarea = __import__("System.Windows").Windows.SystemParameters.WorkArea
        desktopWorkingArea = workarea
        self.window.Left = desktopWorkingArea.Right - self.window.Width
        self.window.Top = desktopWorkingArea.Top

        self.SetText = self._get_objects_from_xaml_of_type("TextBox")
        self.SetCombo = self._get_objects_from_xaml_of_type("ComboBox")
        self.SetBool = self._get_objects_from_xaml_of_type(["RadioButton", "CheckBox"])
        self.read_settings()
        uri = Uri(os.path.join(self.image_path, "pyansys-logo-black-cropped.png"))
        logo = self.get_ui_object("logo")
        pyaedt.edb_core.edb_data.simulation_configuration.Source = BitmapImage(uri)
        if self._callbacks:
            for el in self._callbacks:
                self.set_callback(el[0], el[1], el[2])
            self._callbacks = []

    @pyaedt_function_handler()
    def validate_object_name_prefix(self, sender, e):
        """Validates the text box with object name prefix."""
        valid = False
        try:
            object_list = self.aedtdesign.modeler.get_matched_object_name(sender.Text + "*")
            assert object_list
            valid = True
        except AssertionError:
            pass
        self.update_textbox_status(sender, valid)

    @pyaedt_function_handler()
    def validate_string_no_spaces(self, sender, e):
        """Validates the text box with no spaces."""
        valid = False
        if sender.Text.find(" ") < 0:
            valid = True
        self.update_textbox_status(sender, valid)

    @pyaedt_function_handler()
    def validate_integer(self, sender, e):
        """Validates the text box with to integer."""
        valid = False
        try:
            value = int(sender.Text)
            valid = True
        except ValueError:
            pass
        if not valid:
            value = None
        self.update_textbox_status(sender, valid)
        return value

    @pyaedt_function_handler()
    def validate_positive_odd_integer(self, sender, e):
        """Validates the text box with to positive odd integer."""
        valid = False
        try:
            value = int(sender.Text)
            if value > 0 and value % 2 != 0:
                sender.Text = str(value)
                valid = True
        except ValueError:
            pass
        if not valid:
            value = None
        self.update_textbox_status(sender, valid)
        return value

    @pyaedt_function_handler()
    def validate_positive_integer(self, sender, e):
        """Validates the text box with to strictly positive integer."""
        valid = False
        try:
            value = int(sender.Text)
            if value > 0:
                sender.Text = str(value)
                valid = True
        except ValueError:
            pass
        if not valid:
            value = None
        self.update_textbox_status(sender, valid)
        return value

    def validate_non_negative_integer(self, sender, e):
        """Validates the text box with to non negative integer."""
        valid = False
        try:
            value = int(sender.Text)
            if value >= 0:
                sender.Text = str(value)
                valid = True
        except ValueError:
            pass
        if not valid:
            value = None
        self.update_textbox_status(sender, valid)
        return value

    @pyaedt_function_handler()
    def validate_negative_integer(self, sender, e):
        """Validates the text box with to negative integer."""
        valid = False
        try:
            value = int(sender.Text)
            if value < 0:
                valid = True
        except ValueError:
            pass
        if not valid:
            value = None
        self.update_textbox_status(sender, valid)
        return value

    @pyaedt_function_handler()
    def validate_float(self, sender, e):
        """Validates the text box with to float."""
        valid = False
        try:
            value = float(sender.Text)
            sender.Text = str(value)
            valid = True
        except ValueError:
            value = None
        self.update_textbox_status(sender, valid)
        return value

    @pyaedt_function_handler()
    def validate_float_variable(self, sender, e):
        """Validates the text box with to float variable."""
        proj_and_des_variables = self.aedtdesign.variable_manager.variable_names
        if sender.Text in proj_and_des_variables:
            self.update_textbox_status(sender, True)
        else:
            self.validate_float(sender, e)

    @pyaedt_function_handler()
    def validate_positive_float_variable(self, sender, e):
        """Validates the text box with to positive float variable."""
        proj_and_des_variables = self.aedtdesign.variable_manager.variable_names
        if sender.Text in proj_and_des_variables:
            self.update_textbox_status(sender, True)
        else:
            self.validate_positive_float(sender, e)

    @pyaedt_function_handler()
    def validate_positive_integer_variable(self, sender, e):
        """Validates the text box with to positive integer variable."""
        proj_and_des_variables = self.aedtdesign.variable_manager.variable_names
        if sender.Text in proj_and_des_variables:
            self.update_textbox_status(sender, True)
        else:
            self.validate_positive_integer(sender, e)

    @pyaedt_function_handler()
    def validate_positive_integer_global(self, sender, e):
        """Validates the text box with to positive integer global variable."""
        proj_variables = self.aedtdesign.variable_manager.project_variable_names
        if sender.Text in proj_variables:
            self.update_textbox_status(sender, True)
        else:
            self.validate_positive_integer(sender, e)

    @pyaedt_function_handler()
    def validate_positive_float_global(self, sender, e):
        """Validates the text box with to positive float global variable."""
        proj_variables = self.aedtdesign.variable_manager.project_variable_names
        if sender.Text in proj_variables:
            self.update_textbox_status(sender, True)
        else:
            self.validate_positive_float(sender, e)

    @pyaedt_function_handler()
    def validate_positive_float(self, sender, e):
        """Validates the text box with to positive float."""
        valid = False
        try:
            value = float(sender.Text)
            if value > 0:
                valid = True
        except ValueError:
            pass
        if not valid:
            value = None
        self.update_textbox_status(sender, valid)
        return value

    @pyaedt_function_handler()
    def validate_non_negative_float(self, sender, e):
        """Validates the text box with to non-negative float."""
        valid = False
        try:
            value = float(sender.Text)
            if value >= 0.0:
                valid = True
        except ValueError:
            pass
        if not valid:
            value = None
        self.update_textbox_status(sender, valid)
        return value

    @pyaedt_function_handler()
    def update_textbox_status_with_default_text(self, sender, valid, default_text):
        """Updates a text box with a default text value."""
        if not valid:
            sender.Text = default_text
            sender.BorderBrush = Brushes.Red
        else:
            sender.BorderBrush = Brushes.Green

    @pyaedt_function_handler()
    def update_textbox_status(self, sender, valid):
        """Updates a text box status."""
        if not valid:
            sender.Text = ""
            sender.BorderBrush = Brushes.Red
        else:
            sender.BorderBrush = Brushes.Green

    @pyaedt_function_handler()
    def create_child_design(self, design_name):
        """Duplicates a design and makes a link to the parent design in the settings file.

        Parameters
        ----------
        design_name : str
            Design name.

        Returns
        -------
        bool
        """
        self.aedtdesign.duplicate_design(design_name)
        self._write_parent_link()
        bool

    @pyaedt_function_handler()
    def _read_and_synch_settings_file(self):
        """Reads in existing settings data and updates the path of the library directory in case the project was
        moved to a new location, file system or operating system.
        """
        settings_file = self.settings_file
        if os.path.exists(settings_file):
            settings_data = self.settings_data
            with open(settings_file, "w") as f:
                settings_data["_lib_dir"] = self.aedtlib_directory
                settings_data["_toolkit_dir"] = self.toolkit_directory
                json.dump(settings_data, f, indent=4)

    @pyaedt_function_handler()
    def _write_parent_link(self):
        with open(self.local_settings_file, "w") as f:
            settings_data = {"parent": self.parent_design_name}
            json.dump(settings_data, f, indent=4)

    @pyaedt_function_handler()
    def dummy_callback(self, sender, e):
        """Dummy callback."""
        pass

    @pyaedt_function_handler()
    def display(self):
        """Displays the wpf application as a Dialoq (IronPython) or an Application (CPython)."""
        if sys.implementation.name == "ironpython":
            Window.ShowDialog(self)
        else:
            Application().Run(self.window)

    @pyaedt_function_handler()
    def open_explorer(self, sender, e):
        """Opens a windows explorer window pointing to the selected path in the sender control."""
        if is_windows:
            selected_path = os.path.normpath(sender.Text)
            if os.path.exists(selected_path):
                os_command_string = r'explorer "{}"'.format(selected_path)
                subprocess.Popen(os_command_string)
            pass

    @pyaedt_function_handler()
    def set_callback(self, control, callback, function):
        """Sets up the callback functions from the xaml GUI.

        Parameters
        ----------
        control : str
            Name of the control (Button, TextBox, etc) as a string
        callback : str
            Name of the callback function, e.g. "Click", "LostFocus", etc
        function : func
            Reference to the callback function (requires 2 arguments: sender, e)
        """
        test_control = LogicalTreeHelper.FindLogicalNode(self.window, control)
        a = getattr(test_control, callback)
        a += function

    @pyaedt_function_handler()
    def set_margin(self, object_name, margin):
        """Sets the outer dimensions of the GUI window.

        Parameters
        ----------
        object_name : str
            Object name.
        margin : list
            vector of floats [left, top, bottom, right].
        """
        myThickness = Thickness()
        myThickness.Bottom = margin[2]
        myThickness.Left = margin[0]
        myThickness.Right = margin[3]
        myThickness.Top = margin[1]
        self.get_ui_object(object_name).Margin = myThickness

    @pyaedt_function_handler()
    def assign_image(self, ui_object_name, image_file):
        """Assigns an image to an object.

        Parameters
        ----------
        ui_object_name : str
            Object name.
        image_file : str
            Image full path.

        Returns
        -------

        """
        bi = BitmapImage()
        bi.BeginInit()
        bi.CacheOption = BitmapCacheOption.OnLoad
        bi.CreateOptions = BitmapCreateOptions.IgnoreImageCache
        bi.UriSource = Uri(image_file, UriKind.RelativeOrAbsolute)
        bi.EndInit()
        pyaedt.edb_core.edb_data.simulation_configuration.Source = bi

    @pyaedt_function_handler()
    def set_visible(self, object_list):
        """Defines one or more GUI objects to be visible.

        Parameters
        ----------
        object_list : list
            List of objects to make visible.

        Returns
        -------

        """
        if isinstance(object_list, str):
            object_list = [object_list]
        for object_name in object_list:
            self.get_ui_object(object_name).Visibility = Visibility.Visible

    @pyaedt_function_handler()
    def set_hidden(self, object_list):
        """Defines one or more GUI objects to be hidden.

        Parameters
        ----------
        object_list : list
            List of objects to make hidden.

        Returns
        -------

        """
        if isinstance(object_list, str):
            object_list = [object_list]
        for object_name in object_list:
            self.get_ui_object(object_name).Visibility = Visibility.Hidden

    @pyaedt_function_handler()
    def wait_cursor(self):
        """Turns on the "Wait" cursor and stores the current cursor"""
        self.previous_cursor = self.Cursor
        self.Cursor = Input.Cursors.Wait

    @pyaedt_function_handler()
    def standard_cursor(self):
        """Restores the current cursor"""
        self.Cursor = self.previous_cursor

    @pyaedt_function_handler()
    def _get_objects_from_xaml_of_type(self, type_list):
        if isinstance(type_list, str):
            type_list = [type_list]
        text_list = []
        with open(self.xaml_file, "r") as f:
            for line in f:
                rstrip_line = line.lstrip()[1:]
                pp = rstrip_line.find(" ")
                object_type = rstrip_line[0:pp]
                if object_type in type_list:
                    attribute_list = rstrip_line.split(" ")
                    name = attribute_list[1].split('"')[1]
                    text_list.append(name)
        return text_list

    @pyaedt_function_handler()
    def message_box(self, text, caption=None, buttons=None, icon=None):
        """Message Box."""
        return message_box(text, caption, buttons, icon)

    @pyaedt_function_handler()
    def ok_cancel_message_box(self, text, caption=None, icon=None):
        response = message_box(text, caption, "OKCancel", icon)
        if response == DialogResult.OK:
            return True
        else:
            return False

    @pyaedt_function_handler()
    def add_combo_items(self, combo_box_name, options, default=None):
        """Fills a combo box with a list of options and sets the selected value if nothing is present already.

        Parameters
        ----------
        combo_box_name : str
            Object name.
        options : list
            list of options.
        default : str
            Default value.

        Returns
        -------

        """
        if not isinstance(options, list):
            options = [options]
        control = self.get_ui_object(combo_box_name)
        for each_option in options:
            control.Items.Add(each_option)
        if default and not control.SelectedValue:
            control.SelectedValue = default

    @pyaedt_function_handler()
    def get_combobox_selection(self, ui_object_name):
        """Returns the selected value from a combobox

        Parameters
        ----------
        ui_object_name : str
            Object name.

        Returns str
            The selected value.
        """
        control = self.get_ui_object(ui_object_name)
        item_selected = str(control.SelectedItem)
        return item_selected

    @pyaedt_function_handler()
    def clear_combobox_items(self, ui_object_name):
        """ """
        control = self.get_ui_object(ui_object_name)
        control.Items.Clear()

    @pyaedt_function_handler()
    def set_text_value(self, ui_object_name, text_val):
        """Sets a text box value.

        Parameters
        ----------
        ui_object_name : str
            Object name.
        text_val : str
            Text value to apply.
        """
        control = self.get_ui_object(ui_object_name)
        control.Text = text_val

    @pyaedt_function_handler()
    def get_text_value(self, ui_object_name):
        """ """
        control = self.get_ui_object(ui_object_name)
        return control.Text

    @pyaedt_function_handler()
    def get_checkbox_status(self, ui_object_name):
        """ """
        control = self.get_ui_object(ui_object_name)
        if control.IsChecked:
            return True
        else:
            return False

    @pyaedt_function_handler()
    def set_chechbox_status(self, ui_object_name, flag=True):
        """Sets a check box value.

        Parameters
        ----------
        ui_object_name : str
            Object name.
        flag : bool
            Check Box status.
        """
        control = self.get_ui_object(ui_object_name)
        control.IsChecked = flag

    @pyaedt_function_handler()
    def get_ui_object(self, control_name):
        """Gets a UI object.

        Parameters
        ----------
        control_name : str
            Object name.
        """
        wpf_control = LogicalTreeHelper.FindLogicalNode(self.window, control_name)
        assert wpf_control, "WPF GUI object name {0} does not exist !".format(control_name)
        return wpf_control

    @pyaedt_function_handler()
    def read_settings(self):
        """Reads the setting data from the toolkit settings file in the parent design

        Returns
        -------
        dict
            Dictionary of settings data
        """
        settings_data = self.settings_data

        if settings_data:
            if len(settings_data) > 1:
                for text_control in self.SetText:
                    wpf_control = self.get_ui_object(text_control)
                    try:
                        txt_line = settings_data[text_control]
                        wpf_control.Text = txt_line
                        if txt_line:
                            wpf_control.BorderBrush = Brushes.Green
                    except KeyError:
                        if wpf_control.IsEnabled:
                            wpf_control.BorderBrush = Brushes.Red

                for combo_control in self.SetCombo:
                    wpf_control = self.get_ui_object(combo_control)
                    try:
                        txt_line = settings_data[wpf_control.Name]
                        wpf_control.SelectedValue = txt_line
                        try:
                            self.aedtdesign.logger.info("Trying to set: " + txt_line)
                        except:
                            pass
                        if txt_line:
                            wpf_control.BorderBrush = Brushes.Green
                    except KeyError:
                        if wpf_control.IsEnabled:
                            wpf_control.BorderBrush = Brushes.Red

                for bool_control in self.SetBool:
                    wpf_control = self.get_ui_object(bool_control)
                    try:
                        txt_line = int(settings_data[wpf_control.Name])
                    except KeyError:
                        txt_line = 0
                    except ValueError:
                        txt_line = 0
                    wpf_control.IsChecked = bool(txt_line)
                    if txt_line:
                        wpf_control.BorderBrush = Brushes.Green

        return settings_data

    @pyaedt_function_handler()
    def write_settings(self, user_defined_data=None):
        """Writes UI settings Textbox, Checkbox, Combobox only at present
            also write any user defined data from a json-serializable dictionary

        Parameters
        ----------
        user_defined_data: dict
            Dictionary with arbitrary user data (needs to be json serializable).
        """
        settings_data = self.settings_data
        if not settings_data:
            return False
        with open(self.settings_file, "w") as f:
            for text_control in self.SetText:
                wpf_control = self.get_ui_object(text_control)
                settings_data[wpf_control.Name] = wpf_control.Text

            for bool_control in self.SetBool:
                wpf_control = self.get_ui_object(bool_control)
                if wpf_control.IsChecked:
                    settings_data[wpf_control.Name] = "1"
                else:
                    settings_data[wpf_control.Name] = "0"

            for combo_control in self.SetCombo:
                wpf_control = self.get_ui_object(combo_control)
                settings_data[wpf_control.Name] = wpf_control.Text

            if isinstance(user_defined_data, dict):
                for key, entry in user_defined_data.items():
                    settings_data[key] = entry

            json.dump(settings_data, f, indent=4)

    def __enter__(self):
        return self

    def __exit__(self, ex_type, ex_value, ex_traceback):
        # write the UI data to json
        self.write_settings()

        # If an error occurred in the context of this object, close the window to avoid AEDT crashing
        if ex_type and self.window:
            self.Close()
