import copy
import csv
from collections import OrderedDict

from pyaedt.generic.DataHandlers import _arg2dict
from pyaedt.generic.DataHandlers import _dict2arg
from pyaedt.generic.general_methods import PropsManager
from pyaedt.generic.general_methods import generate_unique_name
from pyaedt.generic.general_methods import pyaedt_function_handler
from pyaedt.modules.OptimetricsTemplates import defaultdoeSetup
from pyaedt.modules.OptimetricsTemplates import defaultdxSetup
from pyaedt.modules.OptimetricsTemplates import defaultoptiSetup
from pyaedt.modules.OptimetricsTemplates import defaultparametricSetup
from pyaedt.modules.OptimetricsTemplates import defaultsensitivitySetup
from pyaedt.modules.OptimetricsTemplates import defaultstatisticalSetup
from pyaedt.modules.SetupTemplates import SetupProps


class CommonOptimetrics(PropsManager, object):
    """Creates and sets up optimizations.

    Parameters
    ----------
    p_app :

    name :

    dictinputs

    optimtype : str
        Type of the optimization.

    """

    def __init__(self, p_app, name, dictinputs, optimtype):
        self.auto_update = False
        self._app = p_app
        self.omodule = self._app.ooptimetrics
        self.name = name
        self.soltype = optimtype

        inputd = copy.deepcopy(dictinputs)

        if optimtype == "OptiParametric":
            self.props = SetupProps(self, inputd or copy.deepcopy(defaultparametricSetup))
            if not inputd and self._app.design_type == "Icepak":
                self.props["ProdOptiSetupDataV2"] = OrderedDict(
                    {"SaveFields": False, "FastOptimetrics": False, "SolveWithCopiedMeshOnly": True}
                )
        if optimtype == "OptiDesignExplorer":
            self.props = SetupProps(self, inputd or copy.deepcopy(defaultdxSetup))
        if optimtype == "OptiOptimization":
            self.props = SetupProps(self, inputd or copy.deepcopy(defaultoptiSetup))
        if optimtype == "OptiSensitivity":
            self.props = SetupProps(self, inputd or copy.deepcopy(defaultsensitivitySetup))
        if optimtype == "OptiStatistical":
            self.props = SetupProps(self, inputd or copy.deepcopy(defaultstatisticalSetup))
        if optimtype == "OptiDXDOE":
            self.props = SetupProps(self, inputd or copy.deepcopy(defaultdoeSetup))
        if optimtype == "optiSLang":
            self.props = SetupProps(self, inputd or copy.deepcopy(defaultdxSetup))
        if inputd:
            self.props.pop("ID", None)
            self.props.pop("NextUniqueID", None)
            self.props.pop("MoveBackwards", None)
            self.props.pop("GoalSetupVersion", None)
            self.props.pop("Version", None)
            self.props.pop("SetupType", None)
            if inputd.get("Sim. Setups"):
                setups = inputd["Sim. Setups"]
                for el in setups:
                    if type(self._app.design_properties["SolutionManager"]["ID Map"]["Setup"]) is list:
                        for setup in self._app.design_properties["SolutionManager"]["ID Map"]["Setup"]:
                            if setup["I"] == el:
                                setups[setups.index(el)] = setup["I"]
                                break
                    else:
                        if self._app.design_properties["SolutionManager"]["ID Map"]["Setup"]["I"] == el:
                            setups[setups.index(el)] = self._app.design_properties["SolutionManager"]["ID Map"][
                                "Setup"
                            ]["N"]
                            break
            if inputd.get("Goals", None):
                if self._app._is_object_oriented_enabled():
                    oparams = self.omodule.GetChildObject(self.name).GetCalculationInfo()
                    oparam = [i for i in oparams[0]]
                    calculation = ["NAME:Goal"]
                    calculation.extend(oparam)
                    arg1 = OrderedDict()
                    _arg2dict(calculation, arg1)
                    self.props["Goals"] = arg1
        self.auto_update = True

    @pyaedt_function_handler()
    def _get_context(
        self,
        expressions,
        condition,
        goal_weight,
        goal_value,
        setup_sweep_name=None,
        domain="Sweep",
        intrinsics=None,
        report_category=None,
        context=None,
        subdesign_id=None,
        polyline_points=0,
        is_goal=False,
    ):
        did = 3
        if domain != "Sweep":
            did = 1
        sweepdefinition = OrderedDict()
        sweepdefinition["ReportType"] = report_category
        if not setup_sweep_name:
            setup_sweep_name = self._app.nominal_sweep
        sweepdefinition["Solution"] = setup_sweep_name
        ctxt = OrderedDict({})

        if self._app.solution_type in ["TR", "AC", "DC"]:
            ctxt["SimValueContext"] = [did, 0, 2, 0, False, False, -1, 1, 0, 1, 1, "", 0, 0]
            setup_sweep_name = self._app.solution_type
            sweepdefinition["Solution"] = setup_sweep_name

        elif self._app.solution_type in ["HFSS3DLayout"]:
            if context == "Differential Pairs":
                ctxt["SimValueContext"] = [
                    did,
                    0,
                    2,
                    0,
                    False,
                    False,
                    -1,
                    1,
                    0,
                    1,
                    1,
                    "",
                    0,
                    0,
                    "EnsDiffPairKey",
                    False,
                    "1",
                    "IDIID",
                    False,
                    "1",
                ]
            else:
                ctxt["SimValueContext"] = [did, 0, 2, 0, False, False, -1, 1, 0, 1, 1, "", 0, 0, "IDIID", False, "1"]

        elif self._app.solution_type in ["NexximLNA", "NexximTransient"]:
            ctxt["SimValueContext"] = [did, 0, 2, 0, False, False, -1, 1, 0, 1, 1, "", 0, 0]
            if subdesign_id:
                ctxt_temp = ["NUMLEVELS", False, "1", "SUBDESIGNID", False, str(subdesign_id)]
                ctxt["SimValueContext"].extend(ctxt_temp)
            if context == "Differential Pairs":
                ctxt_temp = ["USE_DIFF_PAIRS", False, "1"]
                ctxt["SimValueContext"].extend(ctxt_temp)
        elif context == "Differential Pairs":
            ctxt["SimValueContext"] = ["Diff:=", "Differential Pairs", "Domain:=", domain]
        elif self._app.solution_type in ["Q3D Extractor", "2D Extractor"]:
            if not context:
                ctxt["Context"] = "Original"
            else:
                ctxt["Context"] = context
        elif context:
            ctxt["Context"] = context
            if context in self._app.modeler.line_names:
                ctxt["PointCount"] = polyline_points
        else:
            ctxt = OrderedDict({"Domain": domain})
        sweepdefinition["SimValueContext"] = ctxt
        sweepdefinition["Calculation"] = expressions
        sweepdefinition["Name"] = expressions
        sweepdefinition["Ranges"] = OrderedDict({})
        if context and context in self._app.modeler.line_names and intrinsics and "Distance" not in intrinsics:
            sweepdefinition["Ranges"]["Range"] = ("Var:=", "Distance", "Type:=", "a")
        if not setup_sweep_name:
            setup_sweep_name = self._app.nominal_sweep
            if not setup_sweep_name:
                self._app.logger.error("Sweep not Available.")
                return False
        elif setup_sweep_name not in self._app.existing_analysis_sweeps:
            self._app.logger.error("Sweep not Available.")
            return False
        if intrinsics:
            for v, k in intrinsics.items():
                if not k:
                    r = ["Var:=", v, "Type:=", "a"]
                elif isinstance(k, tuple):
                    r = ["Var:=", v, "Type:=", "rd"]
                    r.append("Start:=")
                    r.append(k[0])
                    r.append("Stop:=")
                    r.append(k[1])
                    r.append("DiscreteValues:=")
                    r.append("")
                elif isinstance(k, (list, str)):
                    r = ["Var:=", v, "Type:=", "d"]
                    r.append("DiscreteValues:=")
                    if isinstance(k, list):
                        r.append(",".join(k))
                    else:
                        r.append(k)

                if not sweepdefinition["Ranges"]:
                    sweepdefinition["Ranges"]["Range"] = tuple(r)
                elif isinstance(sweepdefinition["Ranges"]["Range"], list):
                    sweepdefinition["Ranges"]["Range"].append(tuple(r))
                else:
                    sweepdefinition["Ranges"]["Range"] = [sweepdefinition["Ranges"]["Range"]]
                    sweepdefinition["Ranges"]["Range"].append(tuple(r))
        if is_goal:
            sweepdefinition["Condition"] = condition
            sweepdefinition["GoalValue"] = OrderedDict(
                {"GoalValueType": "Independent", "Format": "Real/Imag", "bG": ["v:=", "[{};]".format(goal_value)]}
            )
            sweepdefinition["Weight"] = "[{};]".format(goal_weight)
        return sweepdefinition

    @pyaedt_function_handler()
    def update(self, update_dictionary=None):
        """Update the setup based on stored properties.

        Parameters
        ----------
        update_dictionary : dict, optional
            Dictionary to use. The  default is ``None``.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        References
        ----------

        >>> oModule.EditSetup
        """
        if update_dictionary:
            for el in update_dictionary:
                self.props._setitem_without_update(el, update_dictionary[el])

        arg = ["NAME:" + self.name]
        _dict2arg(self.props, arg)

        if self.soltype == "OptiParametric" and len(arg[8]) == 2:
            arg[8] = ["NAME:Sweep Operations"]
            for variation in self.props["Sweep Operations"].get("add", []):
                arg[8].append("add:=")
                arg[8].append(variation)

        self.omodule.EditSetup(self.name, arg)
        return True

    @pyaedt_function_handler()
    def create(self):
        """Create a setup.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        References
        ----------

        >>> oModule.InsertSetup
        """
        arg = ["NAME:" + self.name]
        _dict2arg(self.props, arg)
        self.omodule.InsertSetup(self.soltype, arg)
        return True

    @pyaedt_function_handler()
    def _add_calculation(
        self,
        calculation,
        ranges=None,
        variables=None,
        solution=None,
        context=None,
        subdesign_id=None,
        polyline_points=1001,
        report_type=None,
        is_goal=False,
        condition="<=",
        goal_value=1,
        goal_weight=1,
    ):
        self.auto_update = False
        if not solution:
            solution = self._app.nominal_sweep
        setupname = solution.split(" ")[0]
        if setupname not in self.props["Sim. Setups"]:
            self.props["Sim. Setups"].append(setupname)
        domain = "Time"
        if (ranges and ("Freq" in ranges or "Phase" in ranges or "Theta" in ranges)) or self._app.solution_type in [
            "Magnetostatic",
            "Electrostatic",
            "EddyCurrent",
            "DCConduction",
            "Eigenmode",
        ]:
            domain = "Sweep"
        if not report_type:
            report_type = self._app.design_solutions.report_type
            if context and context in self._app.modeler.sheet_names:
                report_type = "Fields"
            elif self._app.solution_type in ["Q3D Extractor", "2D Extractor"]:
                report_type = "Matrix"
            elif context:
                try:
                    for f in self._app.field_setups:
                        if context == f.name:
                            report_type = "Far Fields"
                except:
                    pass
        sweepdefinition = self._get_context(
            calculation,
            condition,
            goal_weight,
            goal_value,
            solution,
            domain,
            ranges,
            report_type,
            context,
            subdesign_id,
            polyline_points,
            is_goal,
        )
        dx_variables = {}
        if variables:
            for el in list(variables):
                try:
                    dx_variables[el] = self._app[el]
                except:
                    pass
        for v in list(dx_variables.keys()):
            self._activate_variable(v)
        if self.soltype in ["OptiDesignExplorer", "OptiDXDOE"] and is_goal:
            optigoalname = "CostFunctionGoals"
        else:
            optigoalname = "Goals"
        if "Goal" in self.props[optigoalname]:
            if type(self.props[optigoalname]["Goal"]) is not list:
                self.props[optigoalname]["Goal"] = [self.props[optigoalname]["Goal"], sweepdefinition]
            else:
                self.props[optigoalname]["Goal"].append(sweepdefinition)
        else:
            self.props[optigoalname] = OrderedDict({})
            self.props[optigoalname]["Goal"] = sweepdefinition
        self.auto_update = True
        return self.update()

    @pyaedt_function_handler()
    def _add_goal(
        self,
        optigoalname,
        reporttype,
        solution=None,
        domain="Sweep",
        calculation="",
        calculation_type="discrete",
        calc_val1="",
        calc_val2="",
        condition="==",
        goal_value=1,
        goal_weight=1,
        goal_name=None,
    ):
        """Add an optimization goal to the setup.

        Parameters
        ----------
        optigoalname : str
            Name of the optimization goal.
        reporttype : str, optional
            Type of the report.
        solution : str, optional
            Type of the solution. The default is ``None``.
        domain : str, optional
            Type of the domain. The default is ``"Sweep"''.
        calculation : str, optional
            Name of the calculation. The default is ``""``.
        calculation_type : str, optional
            Type of the calculation. The default is ``"discrete"``.
        calc_val1 : str, optional
            First value for the calculation. The default is ``""``.
        calc_val2 : str, optional
            Second value for the calculation. The default is ``""``.
        condition : str, optional
            The condition for the calculation. The default is ``"=="``.
        goal_value : optional
            Value for the optimization goal. The default is ``1``.
        goal_weight : optional
            Weight for the optimzation goal. The default is ``1``.
        goal_name : str, optional
            Name of the goal. The default is ``None``.

        Returns
        -------

        """
        self.auto_update = False
        sweepdefinition = OrderedDict()
        sweepdefinition["ReportType"] = reporttype
        if not solution:
            solution = self._app.nominal_sweep
        setupname = solution.split(" ")[0]
        if setupname not in self.props["Sim. Setups"]:
            self.props["Sim. Setups"].append(setupname)
        sweepdefinition["Solution"] = solution
        sweepdefinition["SimValueContext"] = OrderedDict({"Domain": domain})
        sweepdefinition["Calculation"] = calculation
        if goal_name:
            sweepdefinition["Name"] = goal_name
        else:
            sweepdefinition["Name"] = generate_unique_name(calculation)
        if domain == "Sweep":
            var = "Freq"
        else:
            var = "Time"
        if calculation_type == "discrete":
            if type(calc_val1) is list:
                dr = ",".join(calc_val1)
            else:
                dr = calc_val1
            sweepdefinition["Ranges"] = OrderedDict({"Range": ["Var:=", var, "Type:=", "d", "DiscreteValues:=", dr]})
        elif calculation_type == "all":
            sweepdefinition["Ranges"] = OrderedDict(
                {
                    "Range": [
                        "Var:=",
                        var,
                        "Type:=",
                        "a",
                    ]
                }
            )
        else:
            sweepdefinition["Ranges"] = OrderedDict(
                {
                    "Range": [
                        "Var:=",
                        var,
                        "Type:=",
                        calculation_type,
                        "Start:=",
                        calc_val1,
                        "Stop:=",
                        calc_val2,
                        "DiscreteValues:=",
                        "",
                    ]
                }
            )
        sweepdefinition["Condition"] = condition
        sweepdefinition["GoalValue"] = OrderedDict(
            {"GoalValueType": "Independent", "Format": "Real/Imag", "bG": ["v:=", "[{};]".format(goal_value)]}
        )
        sweepdefinition["Weight"] = "[{};]".format(goal_weight)
        if "Goal" in self.props[optigoalname]:
            if type(self.props[optigoalname]["Goal"]) is not list:
                self.props[optigoalname]["Goal"] = [self.props[optigoalname]["Goal"], sweepdefinition]
            else:
                self.props[optigoalname]["Goal"].append(sweepdefinition)
        else:
            self.props[optigoalname] = OrderedDict({})
            self.props[optigoalname]["Goal"] = sweepdefinition
        self.auto_update = True
        return self.update()

    @pyaedt_function_handler()
    def _activate_variable(self, variable_name):
        if self.soltype in ["OptiDesignExplorer", "OptiDXDOE", "OptiOptimization", "OptiSLang"]:
            self._app.activate_variable_optimization(variable_name)
        elif self.soltype == "OptiParametric":
            self._app.activate_variable_tuning(variable_name)
        elif self.soltype == "OptiSensitivity":
            self._app.activate_variable_sensitivity(variable_name)
        elif self.soltype == "OptiStatistical":
            self._app.activate_variable_statistical(variable_name)


class SetupOpti(CommonOptimetrics, object):
    """Sets up an optimization in Opimetrics."""

    def __init__(self, app, name, dictinputs=None, optim_type="OptiDesignExplorer"):
        CommonOptimetrics.__init__(self, app, name, dictinputs=dictinputs, optimtype=optim_type)

    @pyaedt_function_handler()
    def delete(self):
        """Delete a defined Optimetrics Setup.

        Parameters
        ----------
        setup_name : str
            Name of optimetrics setup to delete.

        Returns
        -------
        bool
            `True` if setup is deleted. `False` if it failed.
        """

        self.omodule.DeleteSetups([self.name])
        self._app.optimizations.setups.remove(self)
        return True

    @pyaedt_function_handler()
    def add_calculation(
        self,
        calculation,
        ranges=None,
        variables=None,
        solution=None,
        context=None,
        subdesign_id=None,
        polyline_points=1001,
        report_type=None,
    ):
        """Add a calculation to the setup.

        Parameters
        ----------
        calculation : str, optional
            Name of the calculation.
        ranges : dict, optional
            Dictionary of ranges with respective values.
            Values can be: `None` for all values, a List of Discrete Values, a tuple of start and stop range.
            It includes intrinsics like "Freq", "Time", "Theta", "Distance".
            The default is ``None``, to be used e.g. in "Eigenmode" design type.
        solution : str, optional
            Type of the solution. The default is ``None``, in which case the default
            solution is used.
        context : str, optional
            Calculation contexts. It can be a sphere, a matrix or a polyline.
        subdesign_id : int, optional
            Subdesign id for Circuit and HFSS 3D Layout objects.
        polyline_points : int, optional
            Number of points for Polyline context.
        report_type : str, optional
            Override the auto computation of Calculation Type.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        References
        ----------

        >>> oModule.EditSetup
        """
        return self._add_calculation(
            calculation,
            ranges,
            variables,
            solution,
            context,
            subdesign_id,
            polyline_points,
            report_type,
            is_goal=False,
        )

    @pyaedt_function_handler()
    def add_goal(
        self,
        calculation,
        ranges,
        variables=None,
        solution=None,
        context=None,
        subdesign_id=None,
        polyline_points=1001,
        report_type=None,
        condition="<=",
        goal_value=1,
        goal_weight=1,
    ):
        """Add a goal to the setup.

        Parameters
        ----------
        calculation : str, optional
            Name of the calculation.
        ranges : dict
            Dictionary of ranges with respective values.
            Values can be: `None` for all values, a List of Discrete Values, a tuple of start and stop range.
            It includes intrinsics like "Freq", "Time", "Theta", "Distance".
        variables : list, optional
            List of variables to include in the optimization.
        condition : string, optional
            The default is ``"<="``.
        goal_value : optional
            Value for the goal. The default is ``1``.
        goal_weight : optional
            Value for the goal weight. The default is ``1``.
        solution : str, optional
            Type of the solution. The default is ``None``, in which case the default
            solution is used.
        context : str, optional
            Calculation contexts. It can be a sphere, a matrix or a polyline.
        subdesign_id : int, optional
            Subdesign id for Circuit and HFSS 3D Layout objects.
        polyline_points : int, optional
            Number of points for Polyline context.
        report_type : str, optional
            Override the auto computation of Calculation Type.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        References
        ----------

        >>> oModule.EditSetup
        """

        return self._add_calculation(
            calculation,
            ranges,
            variables,
            solution,
            context,
            subdesign_id,
            polyline_points,
            report_type,
            True,
            condition,
            goal_value,
            goal_weight,
        )

    @pyaedt_function_handler()
    def add_variation(
        self,
        variable_name,
        min_value,
        max_value,
        starting_point=None,
        min_step=None,
        max_step=None,
        use_manufacturable=False,
    ):
        """Add a new variable as input for the optimization and defines its ranges.

        Parameters
        ----------
        variable_name : str
            Name of the variable.
        min_value : float
            Minimum Optimization Value for variable_name.
        max_value : float
            Maximum Optimization Value for variable_name.
        starting_point : float, optional
            Starting point for optimization. If None, default will be used.
        min_step : float
            Minimum Step Size for optimization. If None, 1/100 of the range will be used.

        max_step : float
            Maximum Step Size for optimization. If None, 1/10 of the range will be used.
        use_manufacturable : bool
            Either if to use or not the Manufacturable values. Default is False.


        Returns
        -------
        bool
        """
        if variable_name not in self._app.variable_manager.variables:
            self._app.logger.error("Variable {} does not exists.".format(variable_name))
            return False
        self.auto_update = False
        self._activate_variable(variable_name)

        if not min_step:
            min_step = (max_value - min_value) / 100
        min_step = self._app.value_with_units(min_step, self._app.variable_manager[variable_name].units)

        if not max_step:
            max_step = (max_value - min_value) / 10
        max_step = self._app.value_with_units(max_step, self._app.variable_manager[variable_name].units)
        min_value = self._app.value_with_units(min_value, self._app.variable_manager[variable_name].units)
        max_value = self._app.value_with_units(max_value, self._app.variable_manager[variable_name].units)
        arg = [
            "i:=",
            True,
            "int:=",
            False,
            "Min:=",
            min_value,
            "Max:=",
            max_value,
            "MinStep:=",
            min_step,
            "MaxStep:=",
            max_step,
            "MinFocus:=",
            min_value,
            "MaxFocus:=",
            max_value,
            "UseManufacturableValues:=",
            use_manufacturable,
        ]
        if not self.props.get("Variables", None):
            self.props["Variables"] = OrderedDict({})
        self.props["Variables"][variable_name] = arg
        if not self.props.get("StartingPoint", None):
            self.props["StartingPoint"] = OrderedDict({})
        if not starting_point:
            starting_point = self._app[variable_name]

        self.props["StartingPoint"][variable_name] = self._app.value_with_units(
            starting_point, self._app.variable_manager[variable_name].units
        )
        self.auto_update = True
        self.update()
        return True


class SetupParam(CommonOptimetrics, object):
    """Sets up a parametric analysis in Optimetrics."""

    def __init__(self, p_app, name, dictinputs=None, optim_type="OptiParametric"):
        CommonOptimetrics.__init__(self, p_app, name, dictinputs=dictinputs, optimtype=optim_type)
        pass

    @pyaedt_function_handler()
    def delete(self):
        """Delete a defined Optimetrics Setup.

        Parameters
        ----------
        setup_name : str
            Name of optimetrics setup to delete.

        Returns
        -------
        bool
            ``True`` if setup is deleted. ``False`` if it failed.
        """

        self.omodule.DeleteSetups([self.name])
        self._app.parametrics.setups.remove(self)
        return True

    @pyaedt_function_handler()
    def add_variation(self, sweep_var, start_point, end_point=None, step=100, unit=None, variation_type="LinearCount"):
        """Add a variation to an existing parametric setup.

        Parameters
        ----------
        sweep_var : str
            Name of the variable.
        start_point : float or int
            Variation Start Point.
        end_point : float or int, optional
            Variation End Point. This parameter is optional if a Single Value is defined.
        step : float or int, optional
            Variation Step or Count depending on variation_type. Default is `100`.
        unit : str, optional
            Variation units. Default is `None`.
        variation_type : float or int
            Variation Type. Admitted values are `"LinearCount"`, `"LinearStep"`, `"LogScale"`, `"SingleValue"`.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        References
        ----------

        >>> oModule.EditSetup
        """
        if sweep_var not in self._app.variable_manager.variables:
            self._app.logger.error("Variable {} does not exists.".format(sweep_var))
            return False
        sweep_range = ""
        if not unit:
            unit = self._app.variable_manager[sweep_var].units
        start_point = self._app.value_with_units(start_point, unit)
        end_point = self._app.value_with_units(end_point, unit)
        if variation_type == "LinearCount":
            sweep_range = "LINC {} {} {}".format(start_point, end_point, step)
        elif variation_type == "LinearStep":
            sweep_range = "LIN {} {} {}".format(start_point, end_point, self._app.value_with_units(step, unit))
        elif variation_type == "LogScale":
            sweep_range = "DEC {} {} {}".format(start_point, end_point, self._app.value_with_units(step, unit))
        elif variation_type == "SingleValue":
            sweep_range = "{}".format(self._app.value_with_units(start_point, unit))
        if not sweep_range:
            return False
        self._activate_variable(sweep_var)
        sweepdefinition = OrderedDict()
        sweepdefinition["Variable"] = sweep_var
        sweepdefinition["Data"] = sweep_range
        sweepdefinition["OffsetF1"] = False
        sweepdefinition["Synchronize"] = 0
        if self.props["Sweeps"]["SweepDefinition"] is None:
            self.props["Sweeps"]["SweepDefinition"] = sweepdefinition
        elif type(self.props["Sweeps"]["SweepDefinition"]) is not list:
            self.props["Sweeps"]["SweepDefinition"] = [self.props["Sweeps"]["SweepDefinition"]]
            self._append_sweepdefinition(sweepdefinition)
        else:
            self._append_sweepdefinition(sweepdefinition)

        return self.update()

    @pyaedt_function_handler()
    def _append_sweepdefinition(self, sweepdefinition):
        for sweep_def in self.props["Sweeps"]["SweepDefinition"]:
            if sweepdefinition["Variable"] == sweep_def["Variable"]:
                sweep_def["Data"] += " " + sweepdefinition["Data"]
                return True
        self.props["Sweeps"]["SweepDefinition"].append(sweepdefinition)
        return True

    @pyaedt_function_handler()
    def sync_variables(self, variables, sync_n=1):
        """Sync variable variations in an existing parametric setup.
        Setting the sync number to `0` will effectively unsync the variables.

        Parameters
        ----------
        variables : list
            List of variables to sync.
        sync_n : int, optional
            Sync number. Sweep variables with the same Sync number will be synchronizad.
            Default is `1`.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        References
        ----------

        >>> oModule.EditSetup
        """
        if type(self.props["Sweeps"]["SweepDefinition"]) is not list:
            self._app.logger.error("Not enough variables are defined in the Parametric setup")
            return False
        existing_variables = [s["Variable"] for s in self.props["Sweeps"]["SweepDefinition"]]
        undo_vals = {}
        for v in variables:
            if v not in existing_variables:
                self._app.logger.error("Variable {} is not defined in the Parametric setup".format(v))
                return False
        for v in variables:
            for sweep_def in self.props["Sweeps"]["SweepDefinition"]:
                if v == sweep_def["Variable"]:
                    undo_vals[v] = sweep_def["Synchronize"]
                    sweep_def["Synchronize"] = sync_n
        try:
            return self.update()
        except Exception:  # pragma: no cover
            # If it fails to sync (due to e.g. different number of variations), reverts to original values.
            for v in variables:
                for sweep_def in self.props["Sweeps"]["SweepDefinition"]:
                    if v == sweep_def["Variable"]:
                        sweep_def["Synchronize"] = undo_vals[v]
            self._app.logger.error("Failed to sync the Parametric setup.")
            return False

    @pyaedt_function_handler()
    def add_calculation(
        self,
        calculation,
        ranges,
        solution=None,
        context=None,
        subdesign_id=None,
        polyline_points=1001,
        report_type=None,
    ):
        """Add a calculation to the parametric setup.

        Parameters
        ----------
        calculation : str, optional
            Name of the calculation.
        ranges : dict
            Dictionary of ranges with respective values.
            Values can be: `None` for all values, a List of Discrete Values, a tuple of start and stop range.
            It includes intrinsics like "Freq", "Time", "Theta", "Distance".
        solution : str, optional
            Type of the solution. The default is ``None``, in which case the default
            solution is used.
        context : str, optional
            Calculation contexts. It can be a sphere, a matrix or a polyline.
        subdesign_id : int, optional
            Subdesign id for Circuit and HFSS 3D Layout objects.
        polyline_points : int, optional
            Number of points for Polyline context.
        report_type : str, optional
            Override the auto computation of Calculation Type.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        References
        ----------

        >>> oModule.EditSetup
        """
        return self._add_calculation(
            calculation, ranges, None, solution, context, subdesign_id, polyline_points, report_type, is_goal=False
        )

    @pyaedt_function_handler()
    def export_to_csv(self, filename):
        """Export the current Parametric Setup to csv.

        Parameters
        ----------
        filename : str
            Full Path to the csv file.

        Returns
        -------
        bool
            `True` if the export is correctly executed.
        """
        self.omodule.ExportParametricSetupTable(self.name, filename)
        return True


class ParametricSetups(object):
    """Sets up Parametrics analyses. It includes Parametrics, Sensitivity and Statistical Analysis.

    Examples
    --------
    >>> from pyaedt import Hfss
    >>> app = Hfss()
    >>> sensitivity_setups = app.parametrics
    """

    def __init__(self, p_app):
        self._app = p_app
        self.setups = []
        if self._app.design_properties:
            try:
                setups_data = self._app.design_properties["Optimetrics"]["OptimetricsSetups"]
                for data in setups_data:
                    if (
                        isinstance(setups_data[data], (OrderedDict, dict))
                        and setups_data[data]["SetupType"] == "OptiParametric"
                    ):
                        self.setups.append(SetupParam(p_app, data, setups_data[data], setups_data[data]["SetupType"]))
            except:
                pass

    @property
    def p_app(self):
        """Parent."""
        return self._app

    @property
    def optimodule(self):
        """Optimetrics module.

        Returns
        -------
        :class:`Optimetrics`

        """
        return self._app.ooptimetrics

    @pyaedt_function_handler()
    def add(
        self,
        sweep_var,
        start_point,
        end_point=None,
        step=100,
        variation_type="LinearCount",
        solution=None,
        parametricname=None,
    ):
        """Add a basic sensitivity analysis.
        You can customize all options after the analysis is added.

        Parameters
        ----------
        sweep_var : str
            Name of the variable.
        start_point : float or int
            Variation Start Point if a variation is defined or Single Value.
        end_point : float or int, optional
            Variation End Point. This parameter is optional if a Single Value is defined.
        step : float or int
            Variation Step or Count depending on variation_type. The default is ``100``.
        variation_type : float or int
            Variation Type. Admitted values are `"LinearCount"`, `"LinearStep"`, `"LogScale"`, `"SingleValue"`.
        solution : str, optional
            Type of the solution. The default is ``None``, in which case the default
            solution is used.
        parametricname : str, optional
            Name of the sensitivity analysis. The default is ``None``, in which case
            a default name is assigned.

        Returns
        -------
        :class:`pyaedt.modules.DesignXPloration.SetupParam`
            Optimization Object.

        References
        ----------

        >>> oModule.InsertSetup
        """
        if sweep_var not in self._app.variable_manager.variables:
            self._app.logger.error("Variable {} not found.".format(sweep_var))
            return False
        if not solution:
            solution = self._app.nominal_sweep
        setupname = solution.split(" ")[0]
        if not parametricname:
            parametricname = generate_unique_name("Parametric")
        setup = SetupParam(self._app, parametricname, optim_type="OptiParametric")
        setup.auto_update = False

        setup.props["Sim. Setups"] = [setupname]
        setup.props["Sweeps"] = OrderedDict({"SweepDefinition": None})
        setup.create()
        unit = self._app.variable_manager[sweep_var].units
        setup.add_variation(sweep_var, start_point, end_point, step, unit, variation_type)
        setup.auto_update = True
        self.setups.append(setup)
        return setup

    @pyaedt_function_handler()
    def delete(self, setup_name):
        """Delete a defined Parametric Setup.

        Parameters
        ----------
        setup_name : str
            Name of parametric setup to delete.

        Returns
        -------
        bool
            ``True`` if setup is deleted. ``False`` if it failed.
        """
        for el in self.setups:
            if el.name == setup_name:
                el.delete()
                return True
        return False

    @pyaedt_function_handler()
    def add_from_file(self, filename, parametricname=None):
        """Add a Parametric Setup from a csv file.

        Parameters
        ----------
        filename : str
            Csv file path.
        parametricname : str, option
            Name of parameric setup.

        Returns
        -------
        bool
            `True` if the import is executed correctly.
        """
        if not parametricname:
            parametricname = generate_unique_name("Parametric")
        setup = SetupParam(self._app, parametricname, optim_type="OptiParametric")
        setup.auto_update = False
        setup.props["Sim. Setups"] = [setup_defined.name for setup_defined in self._app.setups]
        with open(filename, "r") as csvfile:
            csvreader = csv.DictReader(csvfile)
            first_data_line = next(csvreader)
            setup.props["Sweeps"] = {"SweepDefinition": OrderedDict()}
            sweep_definition = []
            for var_name in csvreader.fieldnames:
                if var_name != "*":
                    sweep_definition.append(
                        OrderedDict(
                            {
                                "Variable": var_name,
                                "Data": first_data_line[var_name],
                                "OffsetF1": False,
                                "Synchronize": 0,
                            }
                        )
                    )
            setup.props["Sweeps"]["SweepDefinition"] = sweep_definition

            args = ["NAME:" + parametricname]
            _dict2arg(setup.props, args)

            setup.props["Sweep Operations"] = OrderedDict({"add": []})
            table = []
            for var_name in csvreader.fieldnames:
                if var_name != "*":
                    table.append(first_data_line[var_name])
            table = [table]
            for line in csvreader:
                table_line = []
                for var_name in csvreader.fieldnames:
                    if var_name != "*":
                        table_line.append(line[var_name])
                table.append(table_line)

            for point in table:
                setup.props["Sweep Operations"]["add"].append(point)

        cont = 0
        for data in args:
            if isinstance(data, list) and "NAME:Sweep Operations" in data:
                del args[cont]
                args.append(["NAME:Sweep Operations"])
                break
            cont += 1

        for variation in setup.props["Sweep Operations"].get("add", []):
            args[-1].append("add:=")
            args[-1].append(variation)

        self.optimodule.InsertSetup("OptiParametric", args)
        self.setups.append(setup)
        return True


class OptimizationSetups(object):
    """Sets up optimizations. It includes Optimization, DOE and DesignXplorer Analysis.

    Examples
    --------
    >>> from pyaedt import Hfss
    >>> app = Hfss()
    >>> optimization_setup = app.optimizations
    """

    def __init__(self, p_app):
        self._app = p_app
        self.setups = []
        if self._app.design_properties:
            try:
                setups_data = self._app.design_properties["Optimetrics"]["OptimetricsSetups"]
                for data in setups_data:
                    if isinstance(setups_data[data], (OrderedDict, dict)) and setups_data[data]["SetupType"] in [
                        "OptiOptimization",
                        "OptiDXDOE",
                        "OptiDesignExplorer",
                        "OptiSLang",
                        "OptiSensitivity",
                        "OptiStatistical",
                    ]:
                        self.setups.append(SetupOpti(p_app, data, setups_data[data], setups_data[data]["SetupType"]))
            except:
                pass

    @property
    def p_app(self):
        """Parent."""
        return self._app

    @property
    def optimodule(self):
        """Optimetrics module.

        Returns
        -------
        :class:`Optimetrics`

        """
        return self._app.ooptimetrics

    @pyaedt_function_handler()
    def delete(self, setup_name):
        """Delete a defined Optimetrics Setup.

        Parameters
        ----------
        setup_name : str
            Name of optimetrics setup to delete.

        Returns
        -------
        bool
            ``True`` if setup is deleted. ``False`` if it failed.
        """
        for el in self.setups:
            if el.name == setup_name:
                el.delete()
                return True
        return False

    @pyaedt_function_handler()
    def add(
        self,
        calculation=None,
        ranges=None,
        variables=None,
        optim_type="Optimization",
        condition="<=",
        goal_value=1,
        goal_weight=1,
        solution=None,
        parametricname=None,
        context=None,
        subdesign_id=None,
        polyline_points=1001,
        report_type=None,
    ):
        """Add a basic optimization analysis.
        You can customize all options after the analysis is added.

        Parameters
        ----------
        calculation : str, optional
            Name of the calculation.
        ranges : dict, optional
            Dictionary of ranges with respective values.
            Values can be: a list of discrete values, a dict with tuple args of start and stop range.
            It includes intrinsics like "Freq", "Time", "Theta", "Distance".
        variables : list, optional
            List of variables to include in the optimization.
        optim_type : strm optional
            Optimization Type.
            Possible values are `"Optimization"`, `"DXDOE"`,`"DesignExplorer"`,`"Sensitivity"`,`"Statistical"`
            and `"optiSLang"`.
        condition : string, optional
            The default is ``"<="``.
        goal_value : optional
            Value for the goal. The default is ``1``.
        goal_weight : optional
            Value for the goal weight. The default is ``1``.
        solution : str, optional
            Type of the solution. The default is ``None``, in which case the default
            solution is used.
        parametricname : str, optional
            Name of the analysis. The default is ``None``, in which case a
            default name is assigned.
        context : str, optional
            Calculation contexts. It can be a sphere, a matrix or a polyline.
        subdesign_id : int, optional
            Subdesign id for Circuit and HFSS 3D Layout objects.
        polyline_points : int, optional
            Number of points for Polyline context.
        report_type : str, optional
            Override the auto computation of Calculation Type.

        Returns
        -------
        :class:`pyaedt.modules.DesignXPloration.SetupOpti`
            Optimization object.

        References
        ----------

        >>> oModule.InsertSetup
        """
        if not solution:
            solution = self._app.nominal_sweep
        setupname = solution.split(" ")[0]
        if not parametricname:
            parametricname = generate_unique_name(optim_type)
        if optim_type != "optiSLang":
            optim_type = "Opti" + optim_type
        setup = SetupOpti(self._app, parametricname, optim_type=optim_type)
        setup.auto_update = False
        setup.props["Sim. Setups"] = [setupname]
        if calculation:
            domain = "Time"
            if not ranges:
                ranges = {}
            if "Freq" in ranges or "Phase" in ranges or "Theta" in ranges:
                domain = "Sweep"
            if not report_type:
                report_type = self._app.design_solutions.report_type
                if context and context in self._app.modeler.sheet_names:
                    report_type = "Fields"
                elif self._app.solution_type in ["Q3D Extractor", "2D Extractor"]:
                    report_type = "Matrix"
                elif context:
                    try:
                        for f in self._app.field_setups:
                            if context == f.name:
                                report_type = "Far Fields"
                    except:
                        pass
            sweepdefinition = setup._get_context(
                calculation,
                condition,
                goal_weight,
                goal_value,
                solution,
                domain,
                ranges,
                report_type,
                context,
                subdesign_id,
                polyline_points,
                is_goal=True,
            )
            setup.props["Goals"]["Goal"] = sweepdefinition

        dx_variables = {}
        if variables:
            for el in variables:
                try:
                    dx_variables[el] = self._app[el]
                except:
                    pass
        for v in list(dx_variables.keys()):
            if optim_type in ["OptiOptimization", "OptiDXDOE", "OptiDesignExplorer"]:
                self._app.activate_variable_optimization(v)
            elif optim_type == "OptiSensitivity":
                self._app.activate_variable_sensitivity(v)
            elif optim_type == "OptiStatistical":
                self._app.activate_variable_statistical(v)
        if optim_type == "OptiDXDOE" and calculation:
            setup.props["CostFunctionGoals"]["Goal"] = sweepdefinition
        if optim_type in ["OptiDesignExplorer", "optiSLang"]:
            setup.props["Sweeps"]["SweepDefinition"] = []
            for l, k in dx_variables.items():
                arg = OrderedDict({"Variable": l, "Data": k, "OffsetF1": False, "Synchronize": 0})
                setup.props["Sweeps"]["SweepDefinition"].append(arg)
        setup.create()
        setup.auto_update = True
        self.setups.append(setup)
        return setup
