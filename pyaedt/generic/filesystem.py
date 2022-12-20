import os
import random
import shutil
import string
from distutils.dir_util import copy_tree
from glob import glob

from pyaedt import settings


def my_location():
    """ """
    return os.path.normpath(os.path.dirname(__file__))


def files_in_directory(path=".", ext=""):
    """

    Parameters
    ----------
    path :
         (Default value = '.')
    ext :
         (Default value = '')

    Returns
    -------

    """
    result = []
    if os.path.exists(path):
        for dir in os.listdir(path):
            bd = os.path.join(path, dir)
            if os.path.isfile(bd) and dir.endswith("." + ext):
                result.append(bd)
    return result


class Scratch:
    """ """

    @property
    def path(self):
        """ """
        return self._scratch_path

    @property
    def is_empty(self):
        """ """
        return self._cleaned

    def __init__(self, local_path, permission=0o777, volatile=False):
        self._volatile = volatile
        self._cleaned = True
        char_set = string.ascii_uppercase + string.digits
        self._scratch_path = os.path.normpath(os.path.join(local_path, "scratch" + "".join(random.sample(char_set, 6))))
        if os.path.exists(self._scratch_path):
            try:
                self.remove()
            except:
                self._cleaned = False
        if self._cleaned:
            try:
                os.mkdir(self.path)
                os.chmod(self.path, permission)
            except:
                pass

    def remove(self):
        """ """
        try:
            # TODO check why on Anaconda 3.7 get errors with os.path.exists
            shutil.rmtree(self._scratch_path, ignore_errors=True)
        except:
            pass

    def copyfile(self, src_file, dst_filename=None):
        """

        Parameters
        ----------
        src_file : str
            Source File with fullpath
        dst_filename : str, optional
            Destination filename with extension. If not provided attempt to copy the file
            with the same name in the local scratch folder.


        Returns
        -------

        """
        if dst_filename:
            dst_file = os.path.join(self.path, dst_filename)
        else:
            dst_file = os.path.join(self.path, os.path.basename(src_file))
        if os.path.exists(dst_file):
            try:
                os.unlink(dst_file)
            except OSError:  # pragma: no cover
                pass
        try:
            shutil.copy2(src_file, dst_file)
        except shutil.SameFileError:  # pragma: no cover
            pass

        return dst_file

    def copyfolder(self, src_folder, destfolder):
        """

        Parameters
        ----------
        src_folder :

        destfolder :


        Returns
        -------

        """
        copy_tree(src_folder, destfolder)
        return True

    def __enter__(self):
        return self

    def __exit__(self, ex_type, ex_value, ex_traceback):
        if ex_type or self._volatile:
            self.remove()


def get_json_files(start_folder):
    """
    Get the absolute path to all *.json files in start_folder.

    Parameters
    ----------
    start_folder : str
        Path to the folder where the json files are located.

    Returns
    -------
    """
    return [y for x in os.walk(start_folder) for y in glob(os.path.join(x[0], "*.json"))]


def create_toolkit_directory(project_fullname):
    """Create the toolkit directory if not existent and return it.

    Parameters
    ----------
    project_fullname : str
        File name and path of the AEDT project file.

    Returns
    -------
    str
        Full absolute path for the ``pyaedt`` directory for this project.
        If this directory does not exist, it is created.
    """
    project_path_and_name = os.path.normpath(os.path.splitext(project_fullname)[0])
    project_name = os.path.splitext(os.path.basename(project_fullname))[0]
    results_directory = project_path_and_name + ".aedtresults"

    toolkit_directory = project_path_and_name + ".pyaedt"
    if settings.remote_rpc_session:
        toolkit_directory = toolkit_directory.replace("\\", "/")
        try:
            settings.remote_rpc_session.filemanager.makedirs(toolkit_directory)
        except:
            toolkit_directory = settings.remote_rpc_session.filemanager.temp_dir() + "/" + project_name + ".pyaedt"
    elif settings.remote_api:
        toolkit_directory = results_directory
    elif not os.path.isdir(toolkit_directory):
        try:
            os.mkdir(toolkit_directory)
        except FileNotFoundError:
            toolkit_directory = results_directory

    return toolkit_directory
