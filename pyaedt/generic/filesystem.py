import os
import random
import shutil
import string


def search_files(dirname, pattern="*"):
    """Search for files inside a directory given a specific pattern.

    Parameters
    ----------
    dirname : str
    pattern :str, optional

    Returns
    -------
    list
    """
    from pyaedt.generic.general_methods import is_ironpython

    if is_ironpython:
        import glob

        return list(glob.glob(os.path.join(dirname, pattern)))
    else:
        import pathlib

        return [os.path.abspath(i) for i in pathlib.Path(dirname).glob(pattern)]


def my_location():
    """ """
    return os.path.normpath(os.path.dirname(__file__))


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
            except FileNotFoundError as fnf_error:  # Raise error if folder doesn't exist.
                print(fnf_error)

    def remove(self):
        """ """
        try:
            # TODO check why on Anaconda 3.7 get errors with os.path.exists
            shutil.rmtree(self._scratch_path, ignore_errors=True)
        except:
            pass

    def copyfile(self, src_file, dst_filename=None):
        """Copy a file to the scratch directory. The target filename is optional.
        If omitted, the target file name is identical to the source file name.

        Parameters
        ----------
        src_file : str
            Source file with fullpath.
        dst_filename : str, optional
            Destination filename with the extension. The default is ``None``,
            in which case the destination file is given the same name as the
            source file.


        Returns
        -------
        dst_file : str
            Full path and file name of the copied file.

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
        except FileNotFoundError as fnf_error:
            print(fnf_error)

        return dst_file

    def copyfolder(self, src_folder, destfolder):
        """Parameters
        ----------
        src_folder :

        destfolder :


        Returns
        -------

        """
        from distutils.dir_util import copy_tree

        copy_tree(src_folder, destfolder)
        return True

    def __enter__(self):
        return self

    def __exit__(self, ex_type, ex_value, ex_traceback):
        if ex_type or self._volatile:
            self.remove()


def get_json_files(start_folder):
    """Get the absolute path to all *.json files in start_folder.

    Parameters
    ----------
    start_folder, str
        Path to the folder where the json files are located.

    Returns
    -------
    """
    return [y for x in os.walk(start_folder) for y in search_files(x[0], "*.json")]
