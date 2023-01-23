Installation
============
PyAEDT consolidates and extends all existing capital around scripting for AEDT,
allowing re-use of existing code, sharing of best practices, and collaboration.

This PyAnsys library has been tested on HFSS, Icepak, and Maxwell 3D. It also provides
basic support for EDB and Circuit (Nexxim).

Requirements
~~~~~~~~~~~~
In addition to the runtime dependencies listed in the installation information, PyAEDT
requires Ansys Electronics Desktop (AEDT) 2021 R2 or later. The AEDT Student Version is also supported.



Install on CPython from PyPI
~~~~~~~~~~~~~~~~~~~~~~~~~~~~
You can install PyAEDT on CPython 3.7 through 3.10 from PyPI:

.. code:: python

    pip install pyaedt

You can also install PyAEDT from Conda-Forge:

.. code:: python

    conda install -c conda-forge pyaedt


Linux support
~~~~~~~~~~~~~

PyAEDT works with CPython 3.7 through 3.10 on Linux in AEDT 2022 R2 and later.
However, you must set up the following environment variables:

.. code::

    export ANSYSEM_ROOT222=/path/to/AedtRoot/AnsysEM/v222/Linux64
    export LD_LIBRARY_PATH=$ANSYSEM_ROOT222/common/mono/Linux64/lib64:$ANSYSEM_ROOT222/Delcross:$LD_LIBRARY_PATH


Install offline from a wheelhouse
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Using a wheelhouse can be helpful if you work for a company that restricts access to external networks.
Wheelhouses for CPython 3.7, 3.8, and 3.9 are available in the releases for PyAEDT v0.4.70
and later for both Windows and Linux.
You can install PyAEDT and all of its dependencies from one single entry point that can be shared internally,
which eases the security review of the PyAEDT package content.
`WheelHouse releases <https://github.com/pyansys/pyaedt/releases>`


For example, here is a command for installing the PyAEDT package and all its dependencies from a wheelhouse:

.. code::

    pip install --no-cache-dir --no-index --find-links=file:///<path_to_wheelhouse>/PyAEDT-v<release_version>-wheelhouse-Windows-3.7 pyaedt


Install from a batch file
~~~~~~~~~~~~~~~~~~~~~~~~~
AEDT already includes CPython 3.7, which can be used to run PyAEDT.
It is also possible to use CPython 3.7 as a virtual environment to run PyAEDT.

If you are running on Windows, you can download
:download:`PyAEDT Environment with IDE bat file <../Resources/pyaedt_with_IDE.bat>`
and run this batch file on your local machine. Using this approach
provides you with a complete integrated development environment (IDE)
for writing PyAEDT scripts in Windows with a simple batch file.

This batch file executes these steps:

1. Creates a Python virtual environment in your ``%APPDATA%`` folder. To accomplish
   this, it uses CPython in the latest installed version of AEDT on your machine.
2. Installs PyAEDT.
3. Optionally installs `Spyder <https://www.spyder-ide.org/>`_ with -s flag.
4. Installs `Jupyter Lab <https://jupyter.org/>`_.
5. Creates a symbolic link from your PyAEDT installation to AEDT ``PersonalLib`` so
   that scripts can also be run within AEDT.
6. Updates PyAEDT.
7. Runs the tool that you choose (Spyder, Jupyter Lab, or a simple console).

Steps 1 through 5 are executed only the first time that you run the batch file or when ``-f`` is used:

.. code::

    pyaedt_with_IDE.bat --force-install

    pyaedt_with_IDE.bat -f

Step 6 is executed only when running the command with the ``-update`` option:

.. code::

    pyaedt_with_IDE.bat --update

    pyaedt_with_IDE.bat -u

Optionally, you can decide to pass a Python path. This path is then used to create a virtual environment:

.. code::

    pyaedt_with_IDE.bat -f -p <path-to-python-root-folder>


In addition, it is possible to install the PyAEDT package and all its dependencies provided in the wheelhouse by
executing the batch file mentioned earlier. You must use the Wheelhouse 3.7 package if no Python path is provided.
Otherwise, you must download and use the correct wheelhouse:

.. code::

    pyaedt_with_IDE.bat-w <path_to_wheelhouse>PyAEDT-v<release_version>-wheelhouse-Windows-3.7

    pyaedt_with_IDE.bat -p <path-to-python3.8-root-folder> -w <path_to_wheelhouse>PyAEDT-v<release_version>-wheelhouse-Windows-3.8
    pyaedt_with_IDE.bat -p <path-to-python3.7-root-folder> -w <path_to_wheelhouse>PyAEDT-v<release_version>-wheelhouse-Windows-3.7
    pyaedt_with_IDE.bat -p <path-to-python3.9-root-folder> -w <path_to_wheelhouse>PyAEDT-v<release_version>-wheelhouse-Windows-3.9


Use IronPython in AEDT
~~~~~~~~~~~~~~~~~~~~~~
PyAEDT is designed to work in CPython 3.7+ and supports many advanced processing packages like
``matplotlib``, ``numpy``, and ``pyvista``. A user can still use PyAEDT in the IronPython
environment available in AEDT with some limitations.

To use IronPython in AEDT:

1. Download the PyAEDT package from ``https://pypi.org/project/pyaedt/#files``.
2. Extract the files.
3. Install PyAEDT into AEDT, specifying the full paths to ``ipy64`` and ``setup-distutils.py`` as needed:

.. code::

    ipy64 setup-distutils.py install --user