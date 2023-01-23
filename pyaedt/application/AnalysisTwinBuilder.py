from pyaedt.application.Analysis import Analysis
from pyaedt.generic.general_methods import pyaedt_function_handler
from pyaedt.modeler.schematic import ModelerTwinBuilder
from pyaedt.modules.PostProcessor import CircuitPostProcessor
from pyaedt.modules.SolveSetup import SetupCircuit


class AnalysisTwinBuilder(Analysis):
    """Provides the Twin Builder Analysis Setup (TwinBuilder).
    It is automatically initialized by Application call (Twin Builder).
    Refer to Application function for inputs definition

    Parameters
    ----------

    Returns
    -------

    """

    @property
    def existing_analysis_setups(self):
        """Get all analysis solution setups.

        References
        ----------

        >>> oModule.GetAllSolutionSetups"""
        setups = list(self.oanalysis.GetAllSolutionSetups())
        return setups

    @property
    def setup_names(self):
        """Setup names.

        References
        ----------

        >>> oModule.GetAllSolutionSetups"""
        return list(self.oanalysis.GetAllSolutionSetups())

    def __init__(
        self,
        application,
        projectname,
        designname,
        solution_type,
        setup_name=None,
        specified_version=None,
        non_graphical=False,
        new_desktop_session=False,
        close_on_exit=False,
        student_version=False,
        machine="",
        port=0,
        aedt_process_id=None,
    ):

        Analysis.__init__(
            self,
            application,
            projectname,
            designname,
            solution_type,
            setup_name,
            specified_version,
            non_graphical,
            new_desktop_session,
            close_on_exit,
            student_version,
            machine,
            port,
            aedt_process_id,
        )
        self._modeler = ModelerTwinBuilder(self)
        self._post = CircuitPostProcessor(self)

    @property
    def existing_analysis_sweeps(self):
        """Get all existing analysis setups.

        Returns
        -------
        list of str
            List of all analysis setups in the design.

        """
        return self.existing_analysis_setups

    @property
    def modeler(self):
        """Design oModeler."""
        return self._modeler

    @pyaedt_function_handler()
    def create_setup(self, setupname="MySetupAuto", setuptype=None, props={}):
        """Create a new setup.

        Parameters
        ----------
        setupname : str, optional
            Name of the setup. The default is ``"MySetupAuto"``.
        setuptype : str
            Type of the setup. The default is ``None``, in which case the default
            type is applied.
        props : dict
            Dictionary of properties with values.

        Returns
        -------
        pyaedt.modules.SolveSetup.SetupCircuit
            Setup object.
        """
        if setuptype is None:
            setuptype = self.solution_type
        name = self.generate_unique_setup_name(setupname)
        setup = SetupCircuit(self, setuptype, name)
        setup.name = name
        setup.create()
        if props:
            for el in props:
                setup.props[el] = props[el]
            setup.update()
        self.analysis_setup = name
        self.setups.append(setup)
        return setup
