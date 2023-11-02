import os.path

from pyaedt import is_ironpython, is_linux
from pyaedt.generic.general_methods import env_path

if is_linux and is_ironpython:
    import subprocessdotnet as subprocess
else:
    import subprocess


class SiwaveSolve(object):
    def __init__(self, aedb_path="", aedt_version="2021.2", aedt_installer_path=None):
        self._project_path = aedb_path
        self._exec_path = ""
        self._nbcores = 4
        self._ng = True
        if aedt_installer_path:
            self.installer_path = aedt_installer_path
        else:
            try:
                self.installer_path = env_path(aedt_version)
            except:
                raise Exception("Either a valid aedt version or full path has to be provided")
        if self._ng:
            executable = "siwave_ng"
        else:
            executable = "siwave"
        if is_linux:
            self._exe = os.path.join(self.installer_path, executable)
        else:
            self._exe = os.path.join(self.installer_path, executable + ".exe")

    @property
    def siwave_exe(self):
        return self._exe

    @siwave_exe.setter
    def siwave_exe(self, value):
        self._exe = value

    @property
    def projectpath(self):
        return self._project_path

    @projectpath.setter
    def projectpath(self, value):
        self._project_path = value

    @property
    def execfile(self):
        return self._exec_path

    @execfile.setter
    def execfile(self, value):
        self._exec_path = value

    @property
    def nbcores(self):
        return self._nbcores

    @nbcores.setter
    def nbcores(self, value):
        self._nbcores = value

    @property
    def nongraphical(self):
        return self._ng

    @nongraphical.setter
    def nongraphical(self, value):
        self._ng = value

    def solve(self):
        # supporting non graphical solve only
        if self.nongraphical:
            if is_linux:
                exe_path = os.path.join(self.installer_path, "siwave_ng")
            else:
                exe_path = os.path.join(self.installer_path, "siwave_ng.exe")
            exec_file = os.path.splitext(self._project_path)[0] + ".exec"
            if os.path.exists(exec_file):
                with open(exec_file, "r+") as f:
                    content = f.readlines()
                    if "SetNumCpus" not in content:
                        f.writelines(str.format("SetNumCpus {}", str(self.nbcores)) + "\n")
                        f.writelines("SaveSiw")
                    else:
                        fstarts = [i for i in range(len(content)) if content[i].startswith("SetNumCpus")]
                        content[fstarts[0]] = str.format("SetNumCpus {}", str(self.nbcores))
                        f.close()
                        os.remove(exec_file)
                        f = open(exec_file, "w")
                        f.writelines(content)
            command = [exe_path]
            command.append(self._project_path)
            command.append(exec_file)
            command.append("-formatOutput -useSubdir")
            p = subprocess.Popen(" ".join(command))
            p.wait()

    def export_3d_cad(
        self, format_3d="Q3D", output_folder=None, net_list=None, num_cores=None, aedt_file_name=None, hidden=False
    ):
        """Export edb to Q3D or HFSS

        Parameters
        ----------
        format_3d : str, default ``Q3D``
        output_folder : str
            Output file folder. If `` then the aedb parent folder is used
        net_list : list, default ``None``
            Define Nets to Export. if None, all nets will be exported
        num_cores : int, optional
            Define number of cores to use during export
        aedt_file_name : str, optional
            Output  aedt file name (without .aedt extension). If `` then default naming is used

        Returns
        -------
        str
            path to aedt file
        """
        if not output_folder:
            output_folder = os.path.dirname(self.projectpath)
        scriptname = os.path.join(output_folder, "export_cad.py")
        with open(scriptname, "w") as f:
            f.write("import os\n")
            f.write("edbpath = r'{}'\n".format(self.projectpath))
            f.write("exportOptions = os.path.join(r'{}', 'options.config')\n".format(output_folder))
            f.write("oDoc.ScrImportEDB(edbpath)\n")
            f.write("oDoc.ScrSaveProjectAs(os.path.join(r'{}','{}'))\n".format(output_folder, "test.siw"))
            if net_list:
                f.write("allnets = []\n")
                for el in net_list:
                    f.write("allnets.append('{}')\n".format(el))
                f.write("for i in range(0, len(allnets)):\n")
                f.write("    if allnets[i] != 'DUMMY':\n")
                f.write("        oDoc.ScrSelectNet(allnets[i], 1)\n")
            f.write("oDoc.ScrSetOptionsFor3DModelExport(exportOptions)\n")
            if not aedt_file_name:
                aedt_file_name = format_3d + "_siwave.aedt"
            f.write("q3d_filename = os.path.join(r'{}', '{}')\n".format(output_folder, aedt_file_name))
            if num_cores:
                f.write("oDoc.ScrSetNumCpusToUse('{}')\n".format(num_cores))
                self.nbcores = num_cores
            f.write("oDoc.ScrExport3DModel('{}', q3d_filename)\n".format(format_3d))
            f.write("oDoc.ScrCloseProject()\n")
            f.write("oApp.Quit()\n")
        if is_linux:
            _exe = '"' + os.path.join(self.installer_path, "siwave") + '"'
        else:
            _exe = '"' + os.path.join(self.installer_path, "siwave.exe") + '"'
        command = [_exe]
        if hidden:
            command.append("-embedding")
        command.append("-RunScriptAndExit")
        command.append(scriptname)
        print(command)
        os.system(" ".join(command))
        # p1 = subprocess.call(" ".join(command))
        # p1.wait()
        return os.path.join(output_folder, aedt_file_name)

    def export_dc_report(
        self,
        siwave_project,
        solution_name,
        output_folder=None,
        html_report=True,
        vias=True,
        voltage_probes=True,
        current_sources=True,
        voltage_sources=True,
        power_tree=True,
        loop_res=True,
        hidden=True,
    ):
        """Close EDB and solve it with Siwave.

        Parameters
        ----------
        siwave_project : str
            Siwave full project name.
        solution_name : str
            Siwave DC Analysis name.
        output_folder : str, optional
            Ouptu folder where files will be downloaded.
        html_report : bool, optional
            Either if generate or not html report. Default is `True`.
        vias : bool, optional
            Either if generate or not vias report. Default is `True`.
        voltage_probes : bool, optional
            Either if generate or not voltage probe report. Default is `True`.
        current_sources : bool, optional
            Either if generate or not current source report. Default is `True`.
        voltage_sources : bool, optional
            Either if generate or not voltage source report. Default is `True`.
        power_tree : bool, optional
            Either if generate or not power tree image. Default is `True`.
        loop_res : bool, optional
            Either if generate or not loop resistance report. Default is `True`.

        Returns
        -------
        list
            list of files generated.
        """
        if not output_folder:
            output_folder = os.path.dirname(self.projectpath)
        output_list = []
        scriptname = os.path.normpath(os.path.join(os.path.normpath(output_folder), "export_results.py"))
        with open(scriptname, "w") as f:
            f.write("oApp.OpenProject(r'{}')\n".format(siwave_project))
            if html_report:
                f.write("proj = oApp.GetActiveProject()\n")

                f.write("proj.ScrExportDcSimReportColorBarProperties(14,2,False,True)\n")

                f.write("proj.ScrExportDcSimReportScaling('All','All',-1,-1,False)\n")
                report_name = os.path.join(output_folder, solution_name + ".htm")
                f.write("proj.ScrExportDcSimReport('{}','White',r'{}')\n".format(solution_name, report_name))
                output_list.append(report_name)
            if vias:
                via_name = os.path.join(output_folder, "vias.txt")
                f.write("proj.ScrExportElementData('{}',r'{}','Vias')\n".format(solution_name, via_name))
                output_list.append(via_name)

            if voltage_probes:
                probes_names = os.path.join(output_folder, "voltage_probes.txt")
                f.write("proj.ScrExportElementData('{}',r'{}','Voltage Probes')\n".format(solution_name, probes_names))
                output_list.append(probes_names)

            if current_sources:
                source_name = os.path.join(output_folder, "current_sources.txt")

                f.write("proj.ScrExportElementData('{}',r'{}','Current Sources')\n".format(solution_name, source_name))
                output_list.append(source_name)

            if voltage_sources:
                sources = os.path.join(output_folder, "v_sources.txt")

                f.write("proj.ScrExportElementData('{}',r'{}','Voltage Sources')\n".format(solution_name, sources))
                output_list.append(sources)

            if power_tree:
                csv_file = os.path.join(output_folder, "powertree.csv")
                c = open(csv_file, "w")
                c.close()
                png_file = os.path.join(output_folder, "powertree.png")
                f.write("proj.ScrExportDcPowerTree('{}',r'{}', r'{}' )\n".format(solution_name, csv_file, png_file))
                output_list.append(png_file)

            if loop_res:
                f.write("sourceNames=[]\n")
                f.write("sourceData=[]\n")
                f.write("proj.ScrReadDCLoopResInfo('{}', sourceNames, sourceData)\n".format(solution_name))
                loop_res = os.path.join(output_folder, "loop_res.txt")
                f.write("with open(r'{}','w') as f:\n".format(loop_res))

                f.write("  f.writelines('Sources\tValue\\n')\n")

                f.write("  for a, b in zip(sourceNames, sourceData):\n")

                f.write("      f.writelines(a + '\t' + b + '\\n')\n")
                output_list.append(loop_res)

            f.write("proj.ScrCloseProject()\n")

            f.write("oApp.Quit()\n")
        if is_linux:
            _exe = '"' + os.path.join(self.installer_path, "siwave") + '"'
        else:
            _exe = '"' + os.path.join(self.installer_path, "siwave.exe") + '"'
        command = [_exe]
        if hidden:
            command.append("-embedding")
        command.append("-RunScriptAndExit")
        command.append('"' + scriptname + '"')
        print(command)
        if os.name == "posix":
            p = subprocess.Popen(command)

        else:
            p = subprocess.Popen(" ".join(command))
        p.wait()
        return output_list
