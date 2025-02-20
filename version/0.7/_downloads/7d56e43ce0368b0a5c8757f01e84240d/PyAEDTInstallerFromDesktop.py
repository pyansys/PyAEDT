import argparse
import os
import sys
import platform
import shutil

is_iron_python = platform.python_implementation().lower() == "ironpython"
is_linux = os.name == "posix"
is_windows = not is_linux


def run_pyinstaller_from_c_python(oDesktop):
    # This is called when run from IronPython
    version = oDesktop.GetVersion()[2:6].replace(".", "")
    python_version = "3.10"
    if version <= "231":
        python_version = "3.7"
    edt_root = os.path.normpath(oDesktop.GetExeDir())
    if is_windows:
        python_exe = os.path.normpath(os.path.join(edt_root, "commonfiles", "CPython", python_version.replace(".", "_"),
                                                   "winx64", "Release", "python", "python.exe"))
    else:
        python_exe = os.path.normpath(os.path.join(edt_root, "commonfiles", "CPython", python_version.replace(".", "_"),
                                                   "linx64", "Release", "python", "runpython"))
    command = ['"{}"'.format(python_exe), '"{}"'.format(os.path.normpath(__file__)), "--version=" + version]
    if is_student_version(oDesktop):
        command.append("--student")
    if is_linux:
        command.extend(['--edt_root="{}"'.format(edt_root), '--python_version="{}"'.format(python_version)])

    if wheelpyaedt:
        command.extend(['--wheel="{}"'.format(wheelpyaedt)])

    oDesktop.AddMessage("", "", 0, "Installing PyAEDT.")
    if is_windows:
        import subprocess
        process = subprocess.Popen(" ".join(command))
        process.wait()
        return_code = process.returncode
        err_msg = "There was an error while installing PyAEDT."
    else:
        return_code = run_command(" ".join(command))
        err_msg = "There was an error while installing PyAEDT. Refer to the Terminal window where AEDT was launched " \
                  "from."
    if is_windows:
        venv_dir = os.path.join(os.environ["APPDATA"], "pyaedt_env_ide", "v" + version)
        python_exe = os.path.join(venv_dir, "Scripts", "python.exe")
    else:
        venv_dir = os.path.join(os.environ["HOME"], "pyaedt_env_ide", "v" + version)
        python_exe = os.path.join(venv_dir, "bin", "python")
    if str(return_code) != "0":
        oDesktop.AddMessage("", "", 2, err_msg)
        return
    else:
        oDesktop.AddMessage("", "", 0, "PyAEDT setup complete.")


    import tempfile
    python_script = os.path.join(tempfile.gettempdir(), "configure_pyaedt.py")
    with open(python_script, "w") as f:
        # enable in debu mode
        #f.write("import sys\n")
        #f.write('sys.path.insert(0, r"c:\\ansysdev\\git\\repos\\pyaedt")\n')
        f.write("from pyaedt.misc.aedtlib_personalib_install import add_pyaedt_to_aedt\n")
        f.write('add_pyaedt_to_aedt(aedt_version="{}", is_student_version={}, use_sys_lib=False, new_desktop_session=False, pers_dir=r"{}")\n'.format(oDesktop.GetVersion()[:6], is_student_version(oDesktop), oDesktop.GetPersonalLibDirectory()))

    command = r'"{}" "{}"'.format(python_exe, python_script)
    oDesktop.AddMessage("", "", 0, command)
    ret_code = os.system(command)
    if ret_code != 0:
        oDesktop.AddMessage("", "", 2, "Error configuring the configuration Tab.")
        return
    if version >= "232":
        oDesktop.RefreshToolkitUI()
    msg = "PyAEDT configuration complete."
    if is_linux:
        msg += " Please ensure Ansys Electronics Desktop is launched in gRPC mode (i.e. launch ansysedt with -grpcsrv" \
               " argument) to take advantage of the new toolkits."
    from System.Windows.Forms import MessageBox, MessageBoxButtons, MessageBoxIcon
    oDesktop.AddMessage("", "", 0, msg)
    MessageBox.Show(msg, 'Info', MessageBoxButtons.OK, MessageBoxIcon.Information)


def parse_arguments_for_pyaedt_installer(args=None):
    parser = argparse.ArgumentParser(description="Install PyAEDT")
    if is_linux:
        parser.add_argument("--edt_root", help="AEDT's path (required for Linux)", required=True)
        parser.add_argument("--python_version", help="Python version (required for Linux)", required=True)

    parser.add_argument("--version", "-v", help="AEDT's 3 digit version", required=True)
    parser.add_argument("--student", "--student_version", "-sv", help="Is Student version", action="store_true")
    parser.add_argument("--wheel", "--wheel_house", "-whl", type=str, help="Wheel house path")
    args = parser.parse_args(args)
    if len(sys.argv[1:]) == 0 and args is None:
        parser.print_help()
        parser.error("No arguments given!")
    return args


def install_pyaedt():

    # This is called when run from CPython
    args = parse_arguments_for_pyaedt_installer()
    if is_windows:
        venv_dir = os.path.join(os.environ["APPDATA"], "pyaedt_env_ide", "v" + args.version)
        python_exe = os.path.join(venv_dir, "Scripts", "python.exe")
        pip_exe = os.path.join(venv_dir, "Scripts", "pip.exe")
    else:
        venv_dir = os.path.join(os.environ["HOME"], "pyaedt_env_ide", "v" + args.version)
        python_exe = os.path.join(venv_dir, "bin", "python")
        pip_exe = os.path.join(venv_dir, "bin", "pip")
        os.environ["ANSYSEM_ROOT{}".format(args.version)] = args.edt_root
        ld_library_path_dirs_to_add = [
            "{}/commonfiles/CPython/{}/linx64/Release/python/lib".format(args.edt_root,
                                                                         args.python_version.replace(".", "_")),
            "{}/common/mono/Linux64/lib64".format(args.edt_root),
            "{}".format(args.edt_root),
        ]
        if args.version<"232":
            ld_library_path_dirs_to_add.append("{}/Delcross".format(args.edt_root))
        os.environ["LD_LIBRARY_PATH"] = ":".join(ld_library_path_dirs_to_add) + ":" + os.getenv("LD_LIBRARY_PATH", "")

    if not os.path.exists(venv_dir):

        if args.version == "231":
            run_command('"{}" -m venv "{}" --system-site-packages'.format(sys.executable, venv_dir))
        else:
            run_command('"{}" -m venv "{}"'.format(sys.executable, venv_dir))

        if args.wheel and os.path.exists(args.wheel):
            wheelpyaedt = args.wheel
            import zipfile
            unzipped_path = os.path.join(os.path.dirname(wheelpyaedt),
                                         os.path.splitext(os.path.basename(wheelpyaedt))[0])
            if os.path.exists(unzipped_path):
                shutil.rmtree(unzipped_path, ignore_errors=True)
            with zipfile.ZipFile(wheelpyaedt, 'r') as zip_ref:
                # Extract all contents to a directory (you can specify a different extraction path if needed)
                zip_ref.extractall(unzipped_path)

            run_command('"{}" install --no-cache-dir --no-index --find-links={} pyaedt[all]'.format(pip_exe, unzipped_path))
            run_command('"{}" install --no-cache-dir --no-index --find-links={} jupyterlab'.format(pip_exe, unzipped_path))

        else:
            run_command('"{}" -m pip install --upgrade pip'.format(python_exe))
            run_command('"{}" --default-timeout=1000 install wheel'.format(pip_exe))
            run_command('"{}" --default-timeout=1000 install pyaedt[full]'.format(pip_exe))
            # run_command('"{}" --default-timeout=1000 install git+https://github.com/ansys/pyaedt.git@main'.format(pip_exe))
            run_command('"{}" --default-timeout=1000 install jupyterlab'.format(pip_exe))
            run_command('"{}" --default-timeout=1000 install ipython -U'.format(pip_exe))
            run_command('"{}" --default-timeout=1000 install ipyvtklink'.format(pip_exe))
            # User can uncomment these lines to install Pyside6 modules
            # run_command('"{}" --default-timeout=1000 install pyside6==6.4.0'.format(pip_exe))
            # run_command('"{}" --default-timeout=1000 install pyqtgraph'.format(pip_exe))
            # run_command('"{}" --default-timeout=1000 install qdarkstyle'.format(pip_exe))

        if args.version == "231":
            run_command('"{}" uninstall -y pywin32'.format(pip_exe))

    else:
        run_command('"{}" uninstall --yes pyaedt'.format(pip_exe))

        if args.wheel and os.path.exists(args.wheel):
            wheelpyaedt = args.wheel
            import zipfile
            unzipped_path = os.path.join(os.path.dirname(wheelpyaedt),
                                         os.path.splitext(os.path.basename(wheelpyaedt))[0])
            if os.path.exists(unzipped_path):
                shutil.rmtree(unzipped_path, ignore_errors=True)
            with zipfile.ZipFile(wheelpyaedt, 'r') as zip_ref:
                # Extract all contents to a directory (you can specify a different extraction path if needed)
                zip_ref.extractall(unzipped_path)

            run_command('"{}" install --no-cache-dir --no-index --find-links={} pyaedt'.format(pip_exe, unzipped_path))
        else:
            run_command('"{}" --default-timeout=1000 install pyaedt[full]'.format(pip_exe))

    # if is_windows:
    #     pyaedt_setup_script = "{}/Lib/site-packages/pyaedt/misc/aedtlib_personalib_install.py".format(venv_dir)
    # else:
    #     pyaedt_setup_script = "{}/lib/python{}/site-packages/pyaedt/misc/aedtlib_personalib_install.py".format(
    #         venv_dir, args.python_version)
    #
    # if not os.path.isfile(pyaedt_setup_script):
    #     sys.exit("[ERROR] PyAEDT was not setup properly since {} file does not exist.".format(pyaedt_setup_script))
    #
    # command = '"{}" "{}" --version={}'.format(python_exe, pyaedt_setup_script, args.version)
    # if args.student:
    #     command += " --student"
    # run_command(command)
    sys.exit(0)


def is_student_version(oDesktop):
    edt_root = os.path.normpath(oDesktop.GetExeDir())
    if is_windows and os.path.isdir(edt_root):
        if any("ansysedtsv" in fn.lower() for fn in os.listdir(edt_root)):
            return True
    return False


def run_command(command):
    if is_windows:
        command = '"{}"'.format(command)
    ret_code = os.system(command)
    return ret_code


if __name__ == "__main__":

    # When launched from Toolkit (i.e. IronPython) call this same file using CPython
    if is_iron_python:
        # Check if wheelhouse defined, wheelhouse is created for Windows only
        wheelpyaedt = []
        # Retrieve the script arguments
        script_args = ScriptArgument.split()
        if len(script_args) == 1:
            wheelpyaedt = script_args[0]
            if not os.path.exists(wheelpyaedt):
                wheelpyaedt = []
        run_pyinstaller_from_c_python(oDesktop)
    else:
        install_pyaedt()
