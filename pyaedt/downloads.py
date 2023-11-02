"""Download example datasets from https://github.com/pyansys/example-data"""
import os
import shutil
import tempfile
import zipfile

from pyaedt.generic.general_methods import is_ironpython, is_linux, settings
from pyaedt.misc import list_installed_ansysem

if is_ironpython:
    import urllib
else:
    import urllib.request

tmpfold = tempfile.gettempdir()
EXAMPLE_REPO = "https://github.com/ansys/example-data/raw/master/"
EXAMPLES_PATH = os.path.join(tmpfold, "PyAEDTExamples")


def delete_downloads():
    """Delete all downloaded examples to free space or update the files."""
    shutil.rmtree(EXAMPLES_PATH, ignore_errors=True)


def _get_file_url(directory, filename=None):
    if not filename:
        return EXAMPLE_REPO + "/".join([directory])
    else:
        return EXAMPLE_REPO + "/".join([directory, filename])


def _retrieve_file(url, filename, directory, destination=None, local_paths=[]):
    """Download a file from a url"""
    # First check if file has already been downloaded
    if not destination:
        destination = EXAMPLES_PATH
    local_path = os.path.join(destination, directory, os.path.basename(filename))
    local_path_no_zip = local_path.replace(".zip", "")
    if os.path.isfile(local_path_no_zip) or os.path.isdir(local_path_no_zip):
        local_paths.append(local_path_no_zip)

    # grab the correct url retriever
    if not is_ironpython:
        urlretrieve = urllib.request.urlretrieve
    destination_dir = os.path.join(destination, directory)
    if not os.path.isdir(destination_dir):
        os.makedirs(destination_dir)
    # Perform download
    if is_linux:
        command = "wget {} -O {}".format(url, local_path)
        os.system(command)
    elif is_ironpython:
        versions = list_installed_ansysem()
        if versions:
            cpython = os.listdir(os.path.join(os.getenv(versions[0]), "commonfiles", "CPython"))
            command = (
                '"'
                + os.path.join(
                    os.getenv(versions[0]),
                    "commonfiles",
                    "CPython",
                    cpython[0],
                    "winx64",
                    "Release",
                    "python",
                    "python.exe",
                )
                + '"'
            )
            commandargs = os.path.join(os.path.dirname(local_path), "download.py")
            command += ' "' + commandargs + '"'
            with open(os.path.join(os.path.dirname(local_path), "download.py"), "w") as f:
                f.write("import urllib.request\n")
                f.write("urlretrieve = urllib.request.urlretrieve\n")
                f.write("import urllib.request\n")
                f.write('url = r"{}"\n'.format(url))
                f.write('local_path = r"{}"\n'.format(local_path))
                f.write("urlretrieve(url, local_path)\n")
            print(command)
            os.system(command)
    else:
        _, resp = urlretrieve(url, local_path)
    local_paths.append(local_path)


def _retrieve_folder(url, directory, destination=None, local_paths=[]):
    """Download a folder from a url"""
    # First check if folder exists
    import json
    import re

    if not destination:
        destination = EXAMPLES_PATH
    if directory.startswith("pyaedt/"):
        local_path = os.path.join(destination, directory[7:])
    else:
        local_path = os.path.join(destination, directory)

    if is_ironpython:
        return False
    _get_dir = _get_file_url(directory)
    with urllib.request.urlopen(_get_dir) as response:  # nosec
        data = response.read().decode("utf-8").split("\n")

    if not os.path.isdir(local_path):
        try:
            os.mkdir(local_path)
        except FileNotFoundError:
            os.makedirs(local_path)

    try:
        tree = [i for i in data if '"payload"' in i][0]
        b = re.search(r'>({"payload".+)</script>', tree)
        itemsfromjson = json.loads(b.group(1))
        items = itemsfromjson["payload"]["tree"]["items"]
        for item in items:
            if item["contentType"] == "directory":
                _retrieve_folder(url, item["path"], destination, local_paths)
            else:
                dir_folder = os.path.split(item["path"])
                _download_file(dir_folder[0], dir_folder[1], destination, local_paths)
    except:
        return False


def _download_file(directory, filename=None, destination=None, local_paths=[]):
    if not filename:
        if not directory.startswith("pyaedt/"):
            directory = "pyaedt/" + directory
        _retrieve_folder(EXAMPLE_REPO, directory, destination, local_paths)
    else:
        if directory.startswith("pyaedt/"):
            url = _get_file_url(directory, filename)
            directory = directory[7:]
        else:
            url = _get_file_url("pyaedt/" + directory, filename)
        _retrieve_file(url, filename, directory, destination, local_paths)
    if settings.remote_rpc_session:
        remote_path = os.path.join(settings.remote_rpc_session_temp_folder, os.path.split(local_paths[-1])[-1])
        if not settings.remote_rpc_session.filemanager.pathexists(settings.remote_rpc_session_temp_folder):
            settings.remote_rpc_session.filemanager.makedirs(settings.remote_rpc_session_temp_folder)
        settings.remote_rpc_session.filemanager.upload(local_paths[-1], remote_path)
        local_paths[-1] = remote_path
    return local_paths[-1]


###############################################################################
# front-facing functions


def download_aedb(destination=None):
    """Download an example of AEDB File and return the def path.

    Examples files are downloaded to a persistent cache to avoid
    re-downloading the same file twice.

    Parameters
    ----------
    destination : str, optional
        Path for downloading files. The default is the user's temp folder.

    Returns
    -------
    str
        Path to the example file.

    Examples
    --------
    Download an example result file and return the path of the file.
    >>> import pyaedt
    >>> path = pyaedt.downloads.download_aedb()
    >>> path
    'C:/Users/user/AppData/local/temp/Galileo.aedb'
    """
    local_paths = []
    _download_file("pyaedt/edb/Galileo.aedb", "GRM32ER72A225KA35_25C_0V.sp", destination, local_paths)
    _download_file("pyaedt/edb/Galileo.aedb", "edb.def", destination, local_paths)
    return local_paths[-1]


def download_edb_merge_utility(force_download=False, destination=None):
    """Download an example of WPF Project which allows to merge 2aedb files.

    Examples files are downloaded to a persistent cache to avoid
    re-downloading the same file twice.

    Parameters
    ----------
    force_download : bool
        Force to delete cache and download files again.
    destination : str, optional
        Path for downloading files. The default is the user's temp folder.

    Returns
    -------
    str
        Path to the example file.

    Examples
    --------
    Download an example result file and return the path of the file.
    >>> import pyaedt
    >>> path = pyaedt.downloads.download_edb_merge_utility(force_download=True)
    >>> path
    'C:/Users/user/AppData/local/temp/wpf_edb_merge/merge_wizard.py'
    """
    if not destination:
        destination = EXAMPLES_PATH
    if force_download:
        local_path = os.path.join(destination, "wpf_edb_merge")
        if os.path.exists(local_path):
            shutil.rmtree(local_path, ignore_errors=True)
    local_paths = []
    _download_file("pyaedt/wpf_edb_merge/board.aedb", "edb.def", destination, local_paths)
    _download_file("pyaedt/wpf_edb_merge/package.aedb", "edb.def", destination, local_paths)
    _download_file("pyaedt/wpf_edb_merge", "merge_wizard_settings.json", destination, local_paths)

    _download_file("pyaedt/wpf_edb_merge", "merge_wizard.py", destination, local_paths)
    return local_paths[0]


def download_netlist(destination=None):
    """Download an example of netlist File and return the def path.
    Examples files are downloaded to a persistent cache to avoid
    re-downloading the same file twice.

    Parameters
    ----------
    destination : str, optional
        Path for downloading files. The default is the user's temp folder.

    Returns
    -------
    str
        Path to the example file.

    Examples
    --------
    Download an example result file and return the path of the file.

    >>> import pyaedt
    >>> path = pyaedt.downloads.download_netlist()
    >>> path
    'C:/Users/user/AppData/local/temp/pyaedtexamples/netlist_small.cir'
    """
    local_paths = []
    _download_file("pyaedt/netlist", "netlist_small.cir", destination, local_paths)
    return local_paths[0]


def download_antenna_array(destination=None):
    """Download an example of Antenna Array and return the def path.

    Examples files are downloaded to a persistent cache to avoid
    re-downloading the same file twice.

    Parameters
    ----------
    destination : str, optional
        Path for downloading files. The default is the user's temp folder.

    Returns
    -------
    str
        Path to the example file.

    Examples
    --------
    Download an example result file and return the path of the file.

    >>> import pyaedt
    >>> path = pyaedt.downloads.download_antenna_array()
    >>> path
    'C:/Users/user/AppData/local/temp/pyaedtexamples/FiniteArray_Radome_77GHz_3D_CADDM.aedt'
    """
    local_paths = []
    _download_file("pyaedt/array_antenna", "FiniteArray_Radome_77GHz_3D_CADDM.aedt", destination, local_paths)
    return local_paths[0]


def download_sbr(destination=None):
    """Download an example of SBR+ Array and return the def path.

    Examples files are downloaded to a persistent cache to avoid
    re-downloading the same file twice.

    Parameters
    ----------
    destination : str, optional
        Path for downloading files. The default is the user's temp folder.

    Returns
    -------
    str
        Path to the example file.

    Examples
    --------
    Download an example result file and return the path of the file.

    >>> import pyaedt
    >>> path = pyaedt.downloads.download_antenna_array()
    >>> path
    'C:/Users/user/AppData/local/temp/pyaedtexamples/FiniteArray_Radome_77GHz_3D_CADDM.aedt'
    """
    local_paths = []
    _download_file("pyaedt/sbr", "Cassegrain.aedt", destination, local_paths)
    return local_paths[0]


def download_sbr_time(destination=None):
    """Download an example of SBR+ Time domain animation and return the def path.

    Examples files are downloaded to a persistent cache to avoid
    re-downloading the same file twice.

    Parameters
    ----------
    destination : str, optional
        Path for downloading files. The default is the user's temp folder.

    Returns
    -------
    str
        Path to the example file.

    Examples
    --------
    Download an example result file and return the path of the file.

    >>> import pyaedt
    >>> path = pyaedt.downloads.download_sbr_time()
    >>> path
    'C:/Users/user/AppData/local/temp/pyaedtexamples/sbr/poc_scat_small.aedt'
    """
    return _download_file("pyaedt/sbr", "poc_scat_small.aedt", destination)


def download_icepak(destination=None):
    """Download an example of Icepak Array and return the def path.

    Examples files are downloaded to a persistent cache to avoid
    re-downloading the same file twice.

    Parameters
    ----------
    destination : str, optional
        Path for downloading files. The default is the user's temp folder.

    Returns
    -------
    str
        Path to the example file.

    Examples
    --------
    Download an example result file and return the path of the file.

    >>> import pyaedt
    >>> path = pyaedt.downloads.download_icepak()
    >>> pathavoid
    'C:/Users/user/AppData/local/temp/pyaedtexamples/Graphic_Card.aedt'
    """
    _download_file("pyaedt/icepak", "Graphics_card.aedt", destination)
    return _download_file("pyaedt/icepak", "Graphics_card.aedt", destination)


def download_icepak_3d_component(destination=None):  # pragma: no cover
    """Download an example of Icepak Array and return the def pathsw.

    Examples files are downloaded to a persistent cache to avoid
    re-downloading the same file twice.

    Parameters
    ----------
    destination : str, optional
        Path for downloading files. The default is the user's temp folder.

    Returns
    -------
    str
        Path to PCBAssembly the example file.
    str
        Path to QFP2 the example file.

    Examples
    --------
    Download an example result file and return the path of the file.

    >>> import pyaedt
    >>> path1, path2 = pyaedt.downloads.download_icepak_3d_component()
    >>> path1
    'C:/Users/user/AppData/local/temp/pyaedtexamples/PCBAssembly.aedt',
    """
    local_paths = []
    _download_file("pyaedt/icepak_3dcomp//PCBAssembly.aedb", destination=destination)
    _download_file("pyaedt/icepak_3dcomp", "PCBAssembly.aedt", destination, local_paths)
    _download_file("icepak_3dcomp", "QFP2.aedt", destination, local_paths)
    return local_paths


def download_via_wizard(destination=None):
    """Download an example of Hfss Via Wizard and return the def path.

    Examples files are downloaded to a persistent cache to avoid
    re-downloading the same file twice.

    Parameters
    ----------
    destination : str, optional
        Path for downloading files. The default is the user's temp folder.

    Returns
    -------
    str
        Path to the example file.

    Examples
    --------
    Download an example result file and return the path of the file.

    >>> import pyaedt
    >>> path = pyaedt.downloads.download_via_wizard()
    >>> path
    'C:/Users/user/AppData/local/temp/pyaedtexamples/Graphic_Card.aedt'
    """
    return _download_file("pyaedt/via_wizard", "viawizard_vacuum_FR4.aedt", destination)


def download_touchstone(destination=None):
    """Download an example of touchstone File and return the def path.

    Examples files are downloaded to a persistent cache to avoid
    re-downloading the same file twice.

    Parameters
    ----------
    destination : str, optional
        Path for downloading files. The default is the user's temp folder.

    Returns
    -------
    str
        Path to the example file.

    Examples
    --------
    Download an example result file and return the path of the file.
    >>> import pyaedt
    >>> path = pyaedt.downloads.download_touchstone()
    >>> path
    'C:/Users/user/AppData/local/temp/pyaedtexamples/ssn_ssn.s6p'
    """
    local_paths = []
    _download_file("pyaedt/touchstone", "SSN_ssn.s6p", destination, local_paths)
    return local_paths[0]


def download_sherlock(destination=None):
    """Download an example of sherlock needed files and return the def path.

    Examples files are downloaded to a persistent cache to avoid
    re-downloading the same file twice.

    Parameters
    ----------
    destination : str, optional
        Path for downloading files. The default is the user's temp folder.

    Returns
    -------
    str
        Path to the example file.

    Examples
    --------
    Download an example result file and return the path of the file.

    >>> import pyaedt
    >>> path = pyaedt.downloads.download_sherlock()
    >>> path
    'C:/Users/user/AppData/local/temp/Galileo.aedb'
    """
    if not destination:
        destination = EXAMPLES_PATH
    local_paths = []
    _download_file("pyaedt/sherlock", "MaterialExport.csv", destination, local_paths)
    _download_file("pyaedt/sherlock", "TutorialBoardPartsList.csv", destination, local_paths)
    _download_file("pyaedt/sherlock", "SherlockTutorial.aedt", destination, local_paths)
    _download_file("pyaedt/sherlock", "TutorialBoard.stp", destination, local_paths)
    _download_file("pyaedt/sherlock/SherlockTutorial.aedb", "edb.def", destination, local_paths)

    return os.path.join(destination, "sherlock")


def download_leaf(destination=None):
    """Download an example of Nissan leaf files and return the def path.

    Examples files are downloaded to a persistent cache to avoid
    re-downloading the same file twice.

    Parameters
    ----------
    destination : str, optional
        Path for downloading files. The default is the user's temp folder.

    Returns
    -------
    (str, str)
        Path to the 30DH_20C_smooth and BH_Arnold_Magnetics_N30UH_80C tabular material data file file.

    Examples
    --------
    Download an example result file and return the path of the file.

    >>> import pyaedt
    >>> path = pyaedt.downloads.download_leaf(r"c:\temp")
    >>> path
    ('C:/temp/BH_Arnold_Magnetics_N30UH_80C.tab', 'C:/temp/BH_Arnold_Magnetics_N30UH_80C.tab')
    """
    if not destination:
        destination = EXAMPLES_PATH
    local_paths = []
    _download_file("pyaedt/nissan", "30DH_20C_smooth.tab", destination, local_paths)
    _download_file("pyaedt/nissan", "BH_Arnold_Magnetics_N30UH_80C.tab", destination, local_paths)

    return local_paths[0], local_paths[1]


def download_custom_reports(force_download=False, destination=None):
    """Download an example of CISPR25 with customer reports json template files.

    Examples files are downloaded to a persistent cache to avoid
    re-downloading the same file twice.

    Parameters
    ----------
    force_download : bool
        Force to delete cache and download files again.
    destination : str, optional
        Path for downloading files. The default is the user's temp folder.

    Returns
    -------
    str
        Path to the example folder containing all example files.

    Examples
    --------
    Download an example result file and return the path of the file.
    >>> import pyaedt
    >>> path = pyaedt.downloads.download_custom_reports(force_download=True)
    >>> path
    'C:/Users/user/AppData/local/temp/custom_reports'
    """
    if not destination:
        destination = EXAMPLES_PATH
    if force_download:
        local_path = os.path.join(destination, "custom_reports")
        if os.path.exists(local_path):
            shutil.rmtree(local_path, ignore_errors=True)
    download_file("pyaedt/custom_reports", destination=destination)

    return os.path.join(destination, "custom_reports")


def download_3dcomponent(force_download=False, destination=None):
    """Download an example of 3d component array with json template files.

    Examples files are downloaded to a persistent cache to avoid
    re-downloading the same file twice.

    Parameters
    ----------
    force_download : bool
        Force to delete cache and download files again.
    destination : str, optional
        Path for downloading files. The default is the user's temp folder.

    Returns
    -------
    str
        Path to the example folder containing all example files.

    Examples
    --------
    Download an example result file and return the path of the file.
    >>> import pyaedt
    >>> path = pyaedt.downloads.download_3dcomponent(force_download=True)
    >>> path
    'C:/Users/user/AppData/local/temp/array_3d_component'
    """
    if not destination:
        destination = EXAMPLES_PATH
    if force_download:
        local_path = os.path.join(destination, "array_3d_component")
        if os.path.exists(local_path):
            shutil.rmtree(local_path, ignore_errors=True)
    download_file("pyaedt/array_3d_component", destination=destination)
    return os.path.join(destination, "array_3d_component")


def download_FSS_3dcomponent(force_download=False, destination=None):
    """Download an example of 3d component array with json template files.

    Examples files are downloaded to a persistent cache to avoid
    re-downloading the same file twice.

    Parameters
    ----------
    force_download : bool
        Force to delete cache and download files again.
    destination : str, optional
        Path for downloading files. The default is the user's temp folder.

    Returns
    -------
    str
        Path to the example folder containing all example files.

    Examples
    --------
    Download an example result file and return the path of the file.
    >>> import pyaedt
    >>> path = pyaedt.downloads.download_FSS_3dcomponent(force_download=True)
    >>> path
    'C:/Users/user/AppData/local/temp/array_3d_component'
    """
    if not destination:  # pragma: no cover
        destination = EXAMPLES_PATH
    if force_download:  # pragma: no cover
        local_path = os.path.join(destination, "fss_3d_component")
        if os.path.exists(local_path):  # pragma: no cover
            shutil.rmtree(local_path, ignore_errors=True)
    download_file("pyaedt/fss_3d_component", destination=destination)
    return os.path.join(destination, "fss_3d_component")


def download_multiparts(destination=None):
    """Download an example of 3DComponents Multiparts.

    Examples files are downloaded to a persistent cache to avoid
    re-downloading the same file twice.

    Parameters
    ----------
    destination : str, optional
        Path for downloading files. The default is the user's temp folder.

    Returns
    -------
    str
        Path to the example file.

    Examples
    --------
    Download an example result file and return the path of the file.

    >>> import pyaedt
    >>> path = pyaedt.downloads.download_multiparts()
    >>> path
    'C:/Users/user/AppData/local/temp/multiparts/library'
    """
    if not destination:
        destination = EXAMPLES_PATH
    dest_folder = os.path.join(destination, "multiparts")
    if os.path.exists(os.path.join(dest_folder, "library")):
        shutil.rmtree(os.path.join(dest_folder, "library"), ignore_errors=True)
    _download_file("pyaedt/multiparts", "library.zip", destination)
    if os.path.exists(os.path.join(destination, "multiparts", "library.zip")):
        unzip(os.path.join(destination, "multiparts", "library.zip"), dest_folder)
    return os.path.join(dest_folder, "library")


def download_twin_builder_data(file_name, force_download=False, destination=None):
    """Download a Twin Builder example data file.

    Examples files are downloaded to a persistent cache to avoid
    downloading the same file twice.

    Parameters
    ----------
    file_name : str
        Path of the file in the Twin Builder folder.
    force_download : bool, optional
        Force to delete file and download file again. Default value is ``False``.
    destination : str, optional
        Path to download files to. The default is the user's temporary folder.

    Returns
    -------
    str
        Path to the folder containing all Twin Builder example data files.

    Examples
    --------
    Download an example result file and return the path of the file.
    >>> import pyaedt
    >>> path = pyaedt.downloads.download_twin_builder_data(file_name="Example1.zip",force_download=True)
    >>> path
    'C:/Users/user/AppData/local/temp/twin_builder'
    """
    if not destination:
        destination = EXAMPLES_PATH
    if force_download:
        local_path = os.path.join(destination, os.path.join("twin_builder", file_name))
        if os.path.exists(local_path):
            os.unlink(local_path)
    _download_file("pyaedt/twin_builder", file_name, destination)
    return os.path.join(destination, "twin_builder")


def download_file(directory, filename=None, destination=None):
    """Download file from directory.

    Files are downloaded to a destination. If filename is not specified, the full directory will be downloaded.

    Parameters
    ----------
    directory : str
        Directory name.
    filename : str, optional
        File name to download. The default is all files inside directory.
    destination : str, optional
        Path where files will be downloaded. Default is user temp folder.

    Returns
    -------
    str
        Path to the example file.

    Examples
    --------
    Download an example result file and return the path of the file.

    >>> import pyaedt
    >>> path = pyaedt.downloads.download_file("motorcad", "IPM_Vweb_Hairpin.mot")
    >>> path
    'C:/Users/user/AppData/local/temp/PyAEDTExamples/motorcad'
    """
    local_paths = []
    _download_file(directory, filename, destination, local_paths)
    if filename:
        return list(set(local_paths))[0]
    else:
        if not destination:
            destination = EXAMPLES_PATH
        destination_dir = os.path.join(destination, directory)
        return destination_dir


def unzip(source_filename, dest_dir):
    with zipfile.ZipFile(source_filename) as zf:
        zf.extractall(dest_dir)
