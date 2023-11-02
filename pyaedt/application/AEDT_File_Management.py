import csv
import os
import re
import shutil

from pyaedt.generic.general_methods import open_file, pyaedt_function_handler


@pyaedt_function_handler()
def read_info_fromcsv(projdir, name):
    """Read information from a CSV file and return a list.

    Parameters
    ----------
    projdir : str
        Full path to the file.
    name : str
        Name of the file.

    Returns
    -------
    list

    """
    filename = projdir + "//" + name
    listmcad = []
    with open_file(filename, "rb") as csvfile:
        reader = csv.reader(csvfile, delimiter=",")
        for row in reader:
            listmcad.append(row)
    return listmcad


@pyaedt_function_handler()
def clean_proj_folder(dir, name):
    """Delete all project name-related folders.

    Parameters
    ----------
    dir : str
        Full path to the project directory.
    name : str
        Name of the project.

    Returns
    -------
    bool
        ``True`` when successful, ``False`` when failed.
    """
    if os.path.exists(dir):
        shutil.rmtree(dir, True)
    os.mkdir(dir)
    return True


@pyaedt_function_handler()
def create_output_folder(ProjectDir):
    """Create the output folders starting from the project directory.

    Parameters
    ----------
    ProjectDir : str
        Name of the project directory.

    Returns
    -------
    type
        PicturePath, ResultsPath

    """
    npath = os.path.normpath(ProjectDir)

    # set pathname for the Output
    OutputPath = os.path.join(npath, os.path.basename(npath))
    # set pathname for the images
    PicturePath = os.path.join(npath, os.path.basename(npath), "Pictures")
    # set pathname for the files
    ResultsPath = os.path.join(npath, os.path.basename(npath), "Results")

    # Add folders for outputs
    if not os.path.exists(OutputPath):
        os.mkdir(OutputPath)
    if not os.path.exists(PicturePath):
        os.mkdir(PicturePath)
    if not os.path.exists(ResultsPath):
        os.mkdir(ResultsPath)
    return PicturePath, ResultsPath


@pyaedt_function_handler()
def change_objects_visibility(origfile, solid_list):
    """Edit the project file to make only the solids that are specified visible.

    Parameters
    ----------
    origfile : str
        Full path to the project file, which has an ``.aedt``  extension.
    solid_list : list
        List of names for the solid to make visible. All other solides are hidden.

    Returns
    -------
    bool
        ``True`` when successful, ``False`` when failed.
    """
    path, filename = os.path.split(origfile)
    newfile = os.path.join(path, "aedttmp.tmp")

    if not os.path.isfile(origfile + ".lock"):  # check if the project is closed
        with open(origfile, "rb") as f, open(newfile, "wb") as n:
            # Reading file content
            content = f.read()

            # Searching file content for pattern
            pattern = re.compile(
                r"(\$begin 'EditorWindow'\n.+)(Drawings\[.+\])(.+\n\s*\$end 'EditorWindow')", re.UNICODE
            )
            # Replacing string
            # fmt: off
            view_str = u"Drawings[" + str(len(solid_list)) + u": " + str(solid_list).strip("[")
            s = pattern.sub(r"\1" + view_str + r"\3", content)
            # fmt: on
            # writing file content
            n.write(str(s))

        # renaming files and deleting temp

        os.remove(origfile)
        os.rename(newfile, origfile)

    else:  # project is locked
        print("change_objects_visibility: Project %s is still locked." % origfile)


@pyaedt_function_handler()
def change_model_orientation(origfile, bottom_dir):
    """Edit the project file to change the model orientation.

    Parameters
    ----------
    origfile : str
        Full path to the project file, which has an ``.aedt``  extension.
    bottom_dir : str
        Bottom direction as specified in the properties file.

    Returns
    -------
    bool
        ``True`` when successful, ``False`` when failed.
    """
    path, filename = os.path.split(origfile)
    newfile = os.path.join(path, "aedttmp.tmp")

    # directory of u, v vectors for view orientation
    orientation = {
        "+X": "OrientationMatrix(0, -0.816496610641479, -0.577350318431854, 0, 0.70710676908493, -0.40824830532074, "
        "0.577350318431854, 0, -0.70710676908493, -0.40824830532074, 0.577350318431854, 0, 0, 0, 0, 1, 0, -100, "
        "100, -100, 100, -100, 100)",
        "+Y": "OrientationMatrix(-0.70710688829422, -0.408248245716095, 0.577350199222565, 0, 1.04308128356934e-07, "
        "-0.816496670246124, -0.577350199222565, 0, 0.707106709480286, -0.408248245716095, 0.577350437641144, "
        "0, 0, 0, 0, 1, 0, -100, 100, -100, 100, -100, 100)",
        "+Z": "OrientationMatrix(0.70710676908493, -0.408248394727707, 0.577350199222565, 0, -0.70710676908493, "
        "-0.408248394727707, 0.577350199222565, 0, 0, -0.81649649143219, -0.577350437641144, 0, 0, 0, 0, 1, 0, "
        "-100, 100, -100, 100, -100, 100)",
        "-X": "OrientationMatrix(0, 0.816496610641479, 0.577350318431854, 0, -0.70710676908493, -0.40824830532074, "
        "0.577350318431854, 0, 0.70710676908493, -0.40824830532074, 0.577350318431854, 0, 0, 0, -0, 1, 0, -100, "
        "100, -100, 100, -100, 100)",
        "-Y": "OrientationMatrix(0.70710688829422, -0.408248245716095, 0.577350199222565, 0, 1.04308128356934e-07, "
        "0.816496670246124, 0.577350199222565, 0, -0.707106709480286, -0.408248245716095, 0.577350437641144, 0, "
        "0, 0, -0, 1, 0, -100, 100, -100, 100, -100, 100)",
        "-Z": "OrientationMatrix(-0.70710676908493, -0.408248394727707, 0.577350199222565, 0, 0.70710676908493, "
        "-0.408248394727707, 0.577350199222565, 0, 0, 0.81649649143219, 0.577350437641144, 0, 0, 0, -0, 1, 0, "
        "-100, 100, -100, 100, -100, 100) ",
    }

    if not os.path.isfile(origfile + ".lock"):  # check if the project is closed
        # Opening files
        with open(origfile, "rb") as f, open(newfile, "wb") as n:
            # Reading file content
            content = f.read()

            # Searching file content for pattern
            pattern = re.compile(
                r"(\$begin 'EditorWindow'\n.+?)(OrientationMatrix\(.+?\))(.+\n\s*\$end 'EditorWindow')", re.UNICODE
            )
            # Replacing string
            orientation_str = orientation[bottom_dir]
            s = pattern.sub(r"\1" + orientation_str + r"\3", content)

            # Writing file content
            n.write(str(s))

        # Renaming files and deleting temp
        os.remove(origfile)
        os.rename(newfile, origfile)

    else:  # Project is locked
        print("change_model_orientation: Project %s is still locked." % origfile)
