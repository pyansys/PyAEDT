# Copyright (C) 2019 ANSYS, Inc - All Rights Reserved
# Unauthorized copying of this file, via any medium is strictly prohibited
# Proprietary and confidential
# flake8: noqa

import sys


class WBMultiphysics(object):
    """description of class"""

    def __init__(
        self,
        path,
        name,
        pyaedt_path,
        AEDTproject_name=None,
        AEDTMatproject_name=None,
        GEOMproject_name=None,
        TempMap_name=None,
        PCB_name=None,
    ):
        self.path = path.replace("\\", "/")
        self.name = name
        self.AEDTproject_name = AEDTproject_name
        self.AEDTMatproject_name = AEDTMatproject_name
        self.GEOMproject_name = GEOMproject_name
        self.TempMap_name = TempMap_name
        self.PCB_name = PCB_name
        self.hfss_design_name = "HFSSDesign"
        self.hfssmaterial_design_name = "HFSSDesign 1"
        sys.path.append(pyaedt_path.replace("\\", "/"))

    def import_hfss(self, design_name):

        name = self.AEDTproject_name

        self.fileType1 = GetFileType(Name="Ansys Electronics Desktop Project")
        ImportFile(FilePath=name, FileType=self.fileType1)
        self.hfss_design_name = design_name
        self.hfsssys = GetSystem(Name=self.hfss_design_name)

    def import_material_hfss(self, design_name):

        name = self.AEDTMatproject_name

        self.fileType1 = GetFileType(Name="Ansys Electronics Desktop Project")
        ImportFile(FilePath=name, FileType=self.fileType1)
        self.hfssmaterial_design_name = design_name
        self.materialhfsssys = GetSystem(Name=self.hfssmaterial_design_name)

    def import_scdm(self):

        name = self.GEOMproject_name

        self.geometrytemplate = GetTemplate(TemplateName="Geometry")
        # If system1 Design exists it will create the component Below
        try:
            self.spaceclaim = self.geometrytemplate.CreateSystem(Position="Below", RelativeTo=self.hfsssys)
        except:
            self.spaceclaim = self.geometrytemplate.CreateSystem()

        self.geometry1 = self.spaceclaim.GetContainer(ComponentName="Geometry")
        self.geometry1.SetFile(FilePath=GetAbsoluteUserPathName(name))

    def import_dm(self):

        name = self.GEOMproject_name

        # Import Design Modeler
        self.geometrytemplate = GetTemplate(TemplateName="Geometry")
        # If system1 Design exists it will create the component Below
        try:
            self.designmodeler = self.geometrytemplate.CreateSystem(Position="Below", RelativeTo=self.hfsssys)
        except:
            self.designmodeler = self.geometrytemplate.CreateSystem()

        self.geometrydm = self.designmodeler.GetContainer(ComponentName="Geometry")
        self.geometrydm.SetFile(FilePath=GetAbsoluteUserPathName(name))

    def import_externaldata_fld(self):

        name = self.TempMap_name

        self.externaldatatemplate = GetTemplate(TemplateName="External Data")
        self.externaldata_fld = self.externaldatatemplate.CreateSystem()
        self.externaldatasetup_fld = self.externaldata_fld.GetContainer(ComponentName="Setup")
        self.externalLoadFileData_fld = self.externaldatasetup_fld.AddDataFile(FilePath=GetAbsoluteUserPathName(name))

    def import_externaldata_pcb(self):

        name = self.PCB_name

        self.externaldatatemplate = GetTemplate(TemplateName="External Data")
        self.externaldata_pcb = self.externaldatatemplate.CreateSystem()
        self.externaldatasetup_pcb = self.externaldata_pcb.GetContainer(ComponentName="Setup")
        # Refactor this to Select PCB Format
        try:
            if name.find("aedb") > 0:
                name = name + "/edb.def"
            elif name.find("anf") > 0:
                print("Obsolote format since 2020R2")

            self.externalLoadFileData_pcb = self.externaldatasetup_pcb.AddDataFile(
                FilePath=GetAbsoluteUserPathName(name)
            )
        except:
            print("Format not found")

    def create_thermal_with_hfss(self):
        self.thermaltemplate = GetTemplate(TemplateName="Steady-State Thermal", Solver="ANSYS")
        try:
            self.thermal = self.thermaltemplate.CreateSystem(Position="Right", RelativeTo=self.hfsssys)
        except:
            print("No HFSS Model Imported")

    def transfer_hfss2thermal_ed(self):
        self.hFSSGeometryComponent_hfss = self.hfsssys.GetComponent(Name="HFSSGeometry")
        # Refresh()
        self.engineeringDataThermal = self.thermal.GetComponent(Name="Engineering Data")
        self.hFSSGeometryComponent_hfss.TransferData(TargetComponent=self.engineeringDataThermal)
        try:
            Refresh()
        except:
            print("refresh failed")

    def modify_thermal_ed(self):
        self.engineeringDataThermal = self.thermal.GetContainer(ComponentName="Engineering Data")
        materials = self.engineeringDataThermal.GetMaterials()
        for mat in materials:
            a = str(mat).split(":")
            if a[1] == "vacuum" or a[1] == "pec" or a[1] == "Structural Steel]":
                mat.SetSuppression(Suppressed=True)
        Refresh()

    def link_geometry_hfss2thermal(self):
        self.geometryComponent_thermal = self.thermal.GetComponent(Name="Geometry")
        self.hFSSGeometryComponent_hfss.TransferData(TargetComponent=self.geometryComponent_thermal)
        try:
            Refresh()
        except:
            print("refresh failed")

    def link_setup_hfss2thermal(self):
        self.hFSSSolutionComponent1 = self.hfsssys.GetComponent(Name="HFSSSolution")
        self.setupThermal = self.thermal.GetComponent(Name="Setup")
        self.hFSSSolutionComponent1.TransferData(TargetComponent=self.setupThermal)

    def link_setup_thermal2structural(self):
        self.solutionComponentThermal = self.thermal.GetComponent(Name="Solution")
        self.setupStructural = self.structuralthermal.GetComponent(Name="Setup")
        self.solutionComponentThermal.TransferData(TargetComponent=self.setupStructural)

    def link_geometry_scdm2thermal(self):
        self.geometryComponent_thermal = self.thermal.GetComponent(Name="Geometry")
        self.geometryComponent_scdm = self.spaceclaim.GetComponent(Name="Geometry")
        self.geometryComponent_thermal.ReplaceWithShare(
            TargetSystem=self.thermal, ComponentToShare=self.geometryComponent_scdm, SourceSystem=self.spaceclaim
        )
        try:
            Refresh()
        except:
            print("refresh failed")

    def create_structural_with_thermal(self):
        self.structuraltemplate = GetTemplate(TemplateName="Static Structural", Solver="ANSYS")
        self.engineeringDataThermal = self.thermal.GetComponent(Name="Engineering Data")
        self.geometryComponent_thermal = self.thermal.GetComponent(Name="Geometry")
        self.modelComponentThermal = self.thermal.GetComponent(Name="Model")
        self.solutionComponentThermal = self.thermal.GetComponent(Name="Solution")
        try:
            self.structuralthermal = self.structuraltemplate.CreateSystem(
                ComponentsToShare=[
                    self.engineeringDataThermal,
                    self.geometryComponent_thermal,
                    self.modelComponentThermal,
                ],
                Position="Right",
                RelativeTo=self.thermal,
            )
        except:
            print("No Thermal Model")

    def create_structural_with_hfss(self):
        self.structuraltemplate = GetTemplate(TemplateName="Static Structural", Solver="ANSYS")
        try:
            self.structural = self.structuraltemplate.CreateSystem(Position="Right", RelativeTo=self.hfsssys)
        except:
            print("No HFSS Model Imported")

    def transfer_hfss2structural_ed(self):
        self.hFSSGeometryComponent_hfss = self.hfsssys.GetComponent(Name="HFSSGeometry")
        Refresh()
        self.engineeringDataStructural = self.structural.GetComponent(Name="Engineering Data")
        self.hFSSGeometryComponent_hfss.TransferData(TargetComponent=self.engineeringDataStructural)
        try:
            Refresh()
        except:
            print("refresh failed")

    def transfer_material_hfss2structural_ed(self):
        self.hFSSGeometryComponent_materialhfss = self.materialhfsssys.GetComponent(Name="HFSSGeometry")
        Refresh()
        self.engineeringDataStructural = self.structural.GetComponent(Name="Engineering Data")
        self.hFSSGeometryComponent_materialhfss.TransferData(TargetComponent=self.engineeringDataStructural)
        try:
            Refresh()
        except:
            print("refresh failed")

    def modify_structural_ed(self):
        self.engineeringDataStructural = self.structural.GetContainer(ComponentName="Engineering Data")
        materials = self.engineeringDataStructural.GetMaterials()
        for mat in materials:
            a = str(mat).split(":")
            if a[1] == "vacuum" or a[1] == "pec":
                mat.SetSuppression(Suppressed=True)
        # self.library1 = EngData.OpenLibrary(Name="General Materials", Source="General_Materials.xml")
        # self.matl1 = self.engineeringDataStructural.ImportMaterial(Name="FR-4", Source="General_Materials.xml")
        # self.matl2 = self.engineeringDataStructural.ImportMaterial(Name="Aluminum Alloy", Source="General_Materials.xml")
        # self.matl3 = self.engineeringDataStructural.ImportMaterial(Name="Copper Alloy", Source="General_Materials.xml")
        Refresh()

    def modify_structural_mesh(self):
        self.modelStructural = self.structural.GetComponent(Name="Model")
        self.modelStructural.Update(AllDependencies=True)

    def modify_structural_setup(self):
        self.setupStructural = self.structural.GetComponent(Name="Setup")
        self.setupStructural.Update(AllDependencies=True)

    def modify_thermal_setup(self):
        self.setupThermal = self.thermal.GetComponent(Name="Setup")
        self.setupThermal.Update(AllDependencies=True)

    def modify_thermal_solution(self):
        self.solutionThermal = self.thermal.GetComponent(Name="Solution")
        self.solutionThermal.Update(AllDependencies=True)

    def modify_structuralthermal_setup(self):
        self.setupstructuralthermal = self.structuralthermal.GetComponent(Name="Setup")
        self.setupstructuralthermal.Update(AllDependencies=True)

    def modify_structuralthermal_solution(self):
        self.solutionstructuralthermal = self.structuralthermal.GetComponent(Name="Solution")
        self.solutionstructuralthermal.Update(AllDependencies=True)

    def link_geometry_hfss2structural(self):
        self.geometryComponent_structural = self.structural.GetComponent(Name="Geometry")
        self.hFSSGeometryComponent_hfss.TransferData(TargetComponent=self.geometryComponent_structural)
        try:
            Refresh()
        except:
            print("refresh failed")

    def link_setup_hfss2thermalstructural(self):
        self.hFSSSolutionComponent1 = self.hfsssys.GetComponent(Name="HFSSSolution")
        self.setupStructuralThermal = self.structuralthermal.GetComponent(Name="Setup")
        self.hFSSSolutionComponent1.TransferData(TargetComponent=self.setupStructuralThermal)

    def link_setup_hfss2structural(self):
        self.hFSSSolutionComponent1 = self.hfsssys.GetComponent(Name="HFSSSolution")
        self.setupStructural = self.structural.GetComponent(Name="Setup")
        self.hFSSSolutionComponent1.TransferData(TargetComponent=self.setupStructural)

    def update_hfss(self):
        self.hFSSSolutionComponent1 = self.hfsssys.GetComponent(Name="HFSSSolution")
        self.hFSSSolutionComponent1.Update(AllDependencies=True)

    def update_iterations(self, numIterations, deltaT, deltaD):
        self.feedbackIteratorEntity1 = GetDataEntity(
            "/FeedbackIterator/FeedbackIteratorEntity:FeedbackIteratorEntityInstance"
        )
        if int(numIterations) != self.feedbackIteratorEntity1.TotalSolveIterations:
            self.feedbackIteratorEntity1.MaxSolveIterations = int(numIterations)
            self.feedbackIteratorEntity1.TargetDeltaTPercentage = float(deltaT)
            self.feedbackIteratorEntity1.TargetDeltaDPercentage = float(deltaD)

    def link_setup_temperaturemap2structural(self):
        self.setupexternaldata_fld = self.externaldata_fld.GetComponent(Name="Setup")
        self.setupStructural = self.structural.GetComponent(Name="Setup")
        self.setupexternaldata_fld.TransferData(TargetComponent=self.setupStructural)

        # Modify Table
        self.setupexternaldata_fld1 = self.externaldata_fld.GetContainer(ComponentName="Setup")
        self.externalLoadData_fld = self.setupexternaldata_fld1.GetExternalLoadData()
        self.seexternalLoadFileData_fld = self.externalLoadData_fld.GetExternalLoadFileData(Name="ExternalLoadFileData")
        self.externalLoadFileDataProperty_fld = self.externalLoadFileData_fld.GetDataProperty()
        self.externalLoadFileData_fld.SetDelimiterType(
            FileDataProperty=self.externalLoadFileDataProperty_fld, Delimiter="Space", DelimiterString=" "
        )
        self.externalLoadFileData_fld.SetStartImportAtLine(
            FileDataProperty=self.externalLoadFileDataProperty_fld, LineNumber=3
        )
        self.externalLoadColumnData_fldx = self.externalLoadFileDataProperty_fld.GetColumnData(
            Name="ExternalLoadColumnData"
        )
        self.externalLoadFileDataProperty_fld.SetColumnDataType(
            ColumnData=self.externalLoadColumnData_fldx, DataType="X Coordinate"
        )
        self.externalLoadColumnData_fldy = self.externalLoadFileDataProperty_fld.GetColumnData(
            Name="ExternalLoadColumnData 1"
        )
        self.externalLoadFileDataProperty_fld.SetColumnDataType(
            ColumnData=self.externalLoadColumnData_fldy, DataType="Y Coordinate"
        )
        self.externalLoadColumnData_fldz = self.externalLoadFileDataProperty_fld.GetColumnData(
            Name="ExternalLoadColumnData 2"
        )
        self.externalLoadFileDataProperty_fld.SetColumnDataType(
            ColumnData=self.externalLoadColumnData_fldz, DataType="Z Coordinate"
        )
        self.externalLoadColumnData_fldt = self.externalLoadFileDataProperty_fld.GetColumnData(
            Name="ExternalLoadColumnData 3"
        )
        self.externalLoadFileDataProperty_fld.SetColumnDataType(
            ColumnData=self.externalLoadColumnData_fldt, DataType="Temperature"
        )
        self.externalLoadColumnData_fldt.Unit = "C"
        self.setupexternaldata_fld.Update(AllDependencies=True)

    def link_setup_pcb2structural(self):
        self.setupexternaldata_PCB = self.externaldata_pcb.GetComponent(Name="Setup")
        self.modelStructural = self.structural.GetComponent(Name="Model")
        self.setupexternaldata_PCB.TransferData(TargetComponent=self.modelStructural)
        self.setupexternaldata_PCB.Update(AllDependencies=True)

    def link_geometry_scdm2structural(self):
        self.geometryComponent_structural = self.structural.GetComponent(Name="Geometry")
        self.geometryComponent_scdm = self.spaceclaim.GetComponent(Name="Geometry")
        self.geometryComponent_structural.ReplaceWithShare(
            TargetSystem=self.structural, ComponentToShare=self.geometryComponent_scdm, SourceSystem=self.spaceclaim
        )
        try:
            Refresh()
        except:
            print("refresh failed")

    def link_geometry_dm2structural(self):
        self.geometryComponent_structural = self.structural.GetComponent(Name="Geometry")
        self.geometryComponent_dm = self.designmodeler.GetComponent(Name="Geometry")
        self.geometryComponent_structural.ReplaceWithShare(
            TargetSystem=self.structural, ComponentToShare=self.geometryComponent_dm, SourceSystem=self.designmodeler
        )
        try:
            Refresh()
        except:
            print("refresh failed")

    def model_command(
        self,
    ):
        self.template2 = GetTemplate(TemplateName="Static Structural", Solver="ANSYS")
        self.modelComponent1 = self.system2.GetComponent(Name="Model")
        self.solutionComponent1 = self.system2.GetComponent(Name="Solution")
        self.componentTemplate1 = GetComponentTemplate(Name="SimulationSetupCellTemplate_StructuralStaticANSYS")
        self.system3 = self.template2.CreateSystem(
            ComponentsToShare=[self.engineeringDataComponent1, self.geometryComponent1, self.modelComponent1],
            Position="Right",
            RelativeTo=self.system2,
        )
        self.setupComponent3 = self.system3.GetComponent(Name="Setup")
        self.hFSSSolutionComponent1.TransferData(TargetComponent=self.setupComponent3)
        Refresh()

    def run_hfss_script(self, ScriptFileName, design_name):
        """
        Open HFSS Design and execute a python script in it
        """
        # open HFSS
        self.hfss_design_name = design_name
        # system1 = GetSystem(Name="HFSSDesign1")
        self.hfsssys = GetSystem(Name=self.hfss_design_name)
        Ansoft.EditSystem(System=self.hfsssys)
        string1 = Ansoft.ExecuteGenericDesktopCommand(
            System=self.hfsssys,
            CommandClass="WB_ACTIVATE_GIVEN_SYSTEMID",
            Argument="HFSS",
            ExecuteOnlyIfSystemIsAlreadyOpenInDesktop=True,
        )
        # prepare the RunScript command string to be executed in HFSS
        CommandStr = r'oDesktop.RunScript(r"%s")' % ScriptFileName
        # send the command in HFSS
        self.hfsssys.SendAnsoftCommand(PyCommand=CommandStr)
        # close the application
        self.hfsssys.CloseAnsoftApplication()

    def run_report_script(self, MechGui):
        self.structural = GetSystem(Name="SYS")
        self.structural_model = self.structural.GetContainer(ComponentName="Model")
        if MechGui:
            self.structural_model.Edit()
        pyFilename = self.path + "//" + self.name + "_Report.py"
        pyFilename = pyFilename.replace("\\", "//")
        print("Created file :" + pyFilename)
        sCommand = 'WB.AppletList.Applet("DSApplet").App.Script.doToolsRunMacro("' + pyFilename + '")'
        self.structural_model.SendCommand(Command=sCommand)
        if MechGui:
            self.structural_model.Exit()

    def run_setup_script(self, MechGui):
        self.structural = GetSystem(Name="SYS")
        self.hfsssys = GetSystem(Name=self.hfss_design_name)
        self.hFSSSolutionComponent1 = self.hfsssys.GetComponent(Name="HFSSSolution")
        if MechGui:
            self.structural_model = self.structural.GetContainer(ComponentName="Model")
            self.structural_model.Edit()
        self.structural_model = self.structural.GetContainer(ComponentName="Model")
        self.structural_setup = self.structural.GetContainer(ComponentName="Setup")
        self.hFSSSolutionComponent1.Update(AllDependencies=True)
        Refresh()
        Save(Overwrite=True)
        pyFilename = self.path + "//" + self.name + "_Setup.py"
        pyFilename = pyFilename.replace("\\", "//")
        # pyFilename = pyFilename.replace("\\", "/")
        print("Created Python File: " + pyFilename)
        sCommand = 'WB.AppletList.Applet("DSApplet").App.Script.doToolsRunMacro("' + pyFilename + '")'
        self.structural_setup.SendCommand(Command=sCommand)
        if MechGui:
            self.structural_model.Exit()

    def setup_iterations(self, numIterations, deltaT, deltaD, design_name):
        self.feedbackiteratortemplate = GetTemplate(TemplateName="FeedbackIteratorComponentSystemTemplate")
        # self.system2 = GetSystem(Name="SYS")
        self.structural = GetSystem(Name="SYS")
        self.feedbackiterator = self.feedbackiteratortemplate.CreateSystem(Position="Below", RelativeTo=self.structural)
        # self.system1 = GetSystem(Name="HFSSDesign1")
        # system1 = GetSystem(Name="HFSSDesign1")
        self.hfss_design_name = design_name
        self.hfsssys = GetSystem(Name=self.hfss_design_name)
        self.hFSSSetupComponent1 = self.hfsssys.GetComponent(Name="HFSSSetup")
        self.feedbackIteratorComponent1 = self.feedbackiterator.GetComponent(Name="FeedbackIterator")
        self.hFSSSetupComponent1.TransferData(TargetComponent=self.feedbackIteratorComponent1)
        self.feedbackIteratorEntity1 = GetDataEntity(
            "/FeedbackIterator/FeedbackIteratorEntity:FeedbackIteratorEntityInstance"
        )
        self.feedbackIteratorEntity1.MaxSolveIterations = str(numIterations)
        self.feedbackIteratorEntity1.TargetDeltaTPercentage = str(deltaT)
        self.feedbackIteratorEntity1.TargetDeltaDPercentage = str(deltaD)
        Save(Overwrite=True)

    def analyze_hfss(self, design_name):
        self.hfss_design_name = design_name
        system1 = GetSystem(Name=self.hfss_design_name)
        Ansoft.ForceSolutionIntoUpdateRequiredState(System=system1)
        hfssSolutionComponent1 = system1.GetComponent(Name="HFSSSolution")
        hfssSolutionComponent1.Update(AllDependencies=True)

    def remove_iterations(self):
        system1 = GetSystem(Name="Feedback Iterator")
        system1.Delete()

    # OLD
    def createStruct(self):
        self.template2 = GetTemplate(TemplateName="Static Structural", Solver="ANSYS")
        self.modelComponent1 = self.system2.GetComponent(Name="Model")
        self.solutionComponent1 = self.system2.GetComponent(Name="Solution")
        self.componentTemplate1 = GetComponentTemplate(Name="SimulationSetupCellTemplate_StructuralStaticANSYS")
        self.system3 = self.template2.CreateSystem(
            ComponentsToShare=[
                self.engineeringDataComponentThermal,
                self.geometryComponent_thermal,
                self.modelComponent1,
            ],
            Position="Right",
            RelativeTo=self.system2,
        )
        self.setupComponent3 = self.system3.GetComponent(Name="Setup")
        self.hFSSSolutionComponent1.TransferData(TargetComponent=self.setupComponent3)
        Refresh()

    def cleanintersectionsinSpaceClaim(self):
        self.geometryCell = self.system2.GetContainer(ComponentName="Geometry")
        self.geometryCell.Edit(Interactive=False, IsSpaceClaimGeometry=True)
        SCDMCommand = "\n# Fix Interference\nresult = FixInterference.FindAndFix()\n# EndBlock"
        self.geometryCell.SendCommand(Language="Python", Command=SCDMCommand)
        self.geometryCell.Exit()

    def createSetupandLoads(self, MechGui):
        if MechGui:
            self.model2 = self.system2.GetContainer(ComponentName="Model")
            self.model2.Edit()
        self.model2 = self.system2.GetContainer(ComponentName="Model")
        self.setup2 = self.system2.GetContainer(ComponentName="Setup")
        self.hFSSSolutionComponent1.Update(AllDependencies=True)
        Refresh()
        Save(Overwrite=True)
        pyFilename = self.path + "//" + self.name + "New.py"
        pyFilename = pyFilename.replace("\\", "//")
        print("Created Python File: " + pyFilename)
        sCommand = 'WB.AppletList.Applet("DSApplet").App.Script.doToolsRunMacro("' + pyFilename + '")'
        self.setup2.SendCommand(Command=sCommand)
        self.setupComponent3 = self.system3.GetComponent(Name="Setup")
        self.solutionComponent2 = self.system2.GetComponent(Name="Solution")
        self.solutionComponent2.TransferData(TargetComponent=self.setupComponent3)
        if MechGui:
            self.model2.Exit()

    def ExportSParameterReportfromHFSS_WB(self, FileName, PortsList, PortExct, VariationsArray, YMarkerDB=None):
        # After DesignXploration variation, set the paramentes to "all"
        # and export the S Paramenter plot from HFSS
        #
        system1 = GetSystem(Name=self.hfss_design_name)
        Ansoft.EditSystem(System=system1)
        string1 = Ansoft.ExecuteGenericDesktopCommand(
            System=system1,
            CommandClass="WB_ACTIVATE_GIVEN_SYSTEMID",
            Argument="HFSS",
            ExecuteOnlyIfSystemIsAlreadyOpenInDesktop=True,
        )

        # prepare the arguments with the Parameter Variables defined in designXplorerInput
        arg = "\n[ \n"
        arg = arg + '"Freq:=" , ["All"]'
        for p in VariationsArray:
            arg = arg + ",\n" + '"' + p + ':=" , ["All"]'
        arg = arg + "\n],"

        # prepare the Command string. Note the %s in place of port pairs definition (e.g. %s="Port2,Port1")
        CommandStr = """oDesktop.GetActiveProject().GetActiveDesign().GetModule(\"ReportSetup\").UpdateTraces(\"S Parameter Plot 1\", 
                    [\"dB(S(%s))\"], 
                    \"AFS : Sweep\", 
	                [
		                \"Domain:=\"		, \"Sweep\"
	                ], """
        CommandStr = (
            CommandStr
            + arg
            + """
	                [
		                \"X Component:=\"		, \"Freq\",
		                \"Y Component:=\"		, [\"dB(S(%s))\"]
	                ], [])"""
        )

        # cycle through the port pairs combinations, substitute the %s in CommandStr
        # and run the report update command
        for p in PortsList:
            PortPair = str(PortExct) + "," + str(p)
            CommandStrP = CommandStr % (PortPair, PortPair)
            system1.SendAnsoftCommand(PyCommand=CommandStrP)

        if YMarkerDB:
            # Create an Y marker at YMarkerDB
            MarkerCommandStr = (
                'oDesktop.GetActiveProject().GetActiveDesign().GetModule("ReportSetup").AddCartesianYMarker("S Parameter Plot 1", "MY1", "Y1", %s, "")'
                % str(YMarkerDB)
            )
            system1.SendAnsoftCommand(PyCommand=MarkerCommandStr)
            # Set the properties of Y marker
            system1.SendAnsoftCommand(
                PyCommand="""oDesktop.GetActiveProject().GetActiveDesign().GetModule(\"ReportSetup\").ChangeProperty(
	            [
		            \"NAME:AllTabs\",
		            [
			            \"NAME:Y Marker\",
			            [
				            \"NAME:PropServers\", 
				            \"S Parameter Plot 1:MY1\"
			            ],
			            [
				            \"NAME:ChangedProps\",
				            [
					            \"NAME:Box Background\",
					            \"R:=\"			, 166,
					            \"G:=\"			, 226,
					            \"B:=\"			, 255
				            ],
				            [
					            \"NAME:Line Color\",
					            \"R:=\"			, 0,
					            \"G:=\"			, 128,
					            \"B:=\"			, 192
				            ],
				            [
					            \"NAME:Line Width\",
					            \"Value:=\"		, \"2\"
				            ],
				            [
					            \"NAME:Line Style\",
					            \"Value:=\"		, \"Dash\"
				            ]
			            ]
		            ]
	            ])"""
            )

        # save the report
        system1.SendAnsoftCommand(
            PyCommand='oDesktop.GetActiveProject().GetActiveDesign().GetModule("ReportSetup").ExportImageToFile("S Parameter Plot 1", "'
            + str(FileName)
            + '", 1920, 1080)'
        )
        # close the application
        system1.CloseAnsoftApplication()
