import re
import sys


# lazy imports
def Circuit(
    projectname=None,
    designname=None,
    solution_type=None,
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
    """Circuit Class.

    Parameters
    ----------
    projectname : str, optional
        Name of the project to select or the full path to the project
        or AEDTZ archive to open.  The default is ``None``, in which
        case an attempt is made to get an active project. If no
        projects are present, an empty project is created.
    designname : str, optional
        Name of the design to select. The default is ``None``, in
        which case an attempt is made to get an active design. If no
        designs are present, an empty design is created.
    solution_type : str, optional
        Solution type to apply to the design. The default is
        ``None``, in which case the default type is applied.
    setup_name : str, optional
        Name of the setup to use as the nominal. The default is
        ``None``, in which case the active setup is used or
        nothing is used.
    specified_version : str, int, float, optional
        Version of AEDT to use. The default is ``None``, in which case
        the active version or latest installed version is  used.
        This parameter is ignored when Script is launched within AEDT.
        Examples of input values are ``232``, ``23.2``,``2023.2``,``"2023.2"``.
    non_graphical : bool, optional
        Whether to run AEDT in non-graphical mode. The default
        is ``False``, in which case AEDT is launched in graphical mode.
        This parameter is ignored when a script is launched within AEDT.
    new_desktop_session : bool, optional
        Whether to launch an instance of AEDT in a new thread, even if
        another instance of the ``specified_version`` is active on the
        machine.  The default is ``True``. This parameter is ignored when
        a script is launched within AEDT.
    close_on_exit : bool, optional
        Whether to release AEDT on exit. The default is ``False``.
    student_version : bool, optional
        Whether to open the AEDT student version. The default is ``False``.
        This parameter is ignored when Script is launched within AEDT.
    machine : str, optional
        Machine name to which connect the oDesktop Session. Works only in 2022 R2
        or later. The remote server must be up and running with the command
        `"ansysedt.exe -grpcsrv portnum"`. If a machine is `"localhost"`, the
        server also starts if not present.
    port : int, optional
        Port number on which to start the oDesktop communication on an already existing server.
        This parameter is ignored when creating a new server. It works only in 2022 R2 or
        later. The remote server must be up and running with the command
        `"ansysedt.exe -grpcsrv portnum"`.
    aedt_process_id : int, optional
        Process ID for the instance of AEDT to point PyAEDT at. The default is
        ``None``. This parameter is only used when ``new_desktop_session = False``.

    Returns
    -------
    :class:`pyaedt.circuit.Circuit`

    Examples
    --------
    Create an instance of Circuit and connect to an existing HFSS
    design or create a new HFSS design if one does not exist.

    >>> from pyaedt import Circuit
    >>> aedtapp = Circuit()

    Create an instance of Circuit and link to a project named
    ``"projectname"``. If this project does not exist, create one with
    this name.

    >>> aedtapp = Circuit(projectname)

    Create an instance of Circuit and link to a design named
    ``"designname"`` in a project named ``"projectname"``.

    >>> aedtapp = Circuit(projectname,designame)

    Create an instance of Circuit and open the specified project,
    which is ``"myfie.aedt"``.

    >>> aedtapp = Circuit("myfile.aedt")

    Create an instance of Circuit using the 2023 R2 version and
    open the specified project, which is ``"myfile.aedt"``.

    >>> aedtapp = Circuit(specified_version=2023.2, projectname="myfile.aedt")

    Create an instance of Circuit using the 2023 R2 student version and open
    the specified project, which is named ``"myfile.aedt"``.

    >>> hfss = Circuit(specified_version="2023.2", projectname="myfile.aedt", student_version=True)

    """
    from pyaedt.circuit import Circuit as app

    return app(
        projectname=projectname,
        designname=designname,
        solution_type=solution_type,
        setup_name=setup_name,
        specified_version=specified_version,
        non_graphical=non_graphical,
        new_desktop_session=new_desktop_session,
        close_on_exit=close_on_exit,
        student_version=student_version,
        machine=machine,
        port=port,
        aedt_process_id=aedt_process_id,
    )


def Hfss(
    projectname=None,
    designname=None,
    solution_type=None,
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
    """Return an instance of the Hfss Class.

    Parameters
    ----------
    projectname : str, optional
        Name of the project to select or the full path to the project
        or AEDTZ archive to open. The default is ``None``, in which
        case an attempt is made to get an active project. If no
        projects are present, an empty project is created.
    designname : str, optional
        Name of the design to select. The default is ``None``, in
        which case an attempt is made to get an active design. If no
        designs are present, an empty design is created.
    solution_type : str, optional
        Solution type to apply to the design. The default is
        ``None``, in which case the default type is applied.
    setup_name : str, optional
        Name of the setup to use as the nominal. The default is
        ``None``, in which case the active setup is used or
        nothing is used.
    specified_version : str, int, float, optional
        Version of AEDT to use. The default is ``None``, in which case
        the active version or latest installed version is used.
        This parameter is ignored when a script is launched within AEDT.
        Examples of input values are ``232``, ``23.2``,``2023.2``,``"2023.2"``.
    non_graphical : bool, optional
        Whether to run AEDT in non-graphical mode. The default
        is ``False``, in which case AEDT is launched in graphical mode.
        This parameter is ignored when a script is launched within AEDT.
    new_desktop_session : bool, optional
        Whether to launch an instance of AEDT in a new thread, even if
        another instance of the ``specified_version`` is active on the
        machine. The default is ``False``. This parameter is ignored when
        a script is launched within AEDT.
    close_on_exit : bool, optional
        Whether to release AEDT on exit. The default is ``False``.
    student_version : bool, optional
        Whether to open the AEDT student version. The default is
        ``False``. This parameter is ignored when a script is launched
        within AEDT.
    machine : str, optional
        Machine name to connect the oDesktop session to. This parameter works only on
        2022 R2 or later. The remote Server must be up and running with the command
        `"ansysedt.exe -grpcsrv portnum"`. If the machine is `"localhost"`, the server
        starts if it is not present.
    port : int, optional
        Port number on which to start the oDesktop communication on an already existing server.
        This parameter is ignored when creating a new server. It works only in 2022 R2 or later.
        The remote server must be up and running with the command `"ansysedt.exe -grpcsrv portnum"`.
    aedt_process_id : int, optional
        Process ID for the instance of AEDT to point PyAEDT at. The default is
        ``None``. This parameter is only used when ``new_desktop_session = False``.

    Returns
    -------
    :class:`pyaedt.hfss.Hfss`

    Examples
    --------
    Create an instance of HFSS and connect to an existing HFSS
    design or create a new HFSS design if one does not exist.

    >>> from pyaedt import Hfss
    >>> hfss = Hfss()
    PyAEDT INFO: No project is defined...
    PyAEDT INFO: Active design is set to...


    Create an instance of HFSS and link to a project named
    ``HfssProject``. If this project does not exist, create one with
    this name.

    >>> hfss = Hfss("HfssProject")
    PyAEDT INFO: Project HfssProject has been created.
    PyAEDT INFO: No design is present. Inserting a new design.
    PyAEDT INFO: Added design ...


    Create an instance of HFSS and link to a design named
    ``HfssDesign1`` in a project named ``HfssProject``.

    >>> hfss = Hfss("HfssProject","HfssDesign1")
    PyAEDT INFO: Added design 'HfssDesign1' of type HFSS.


    Create an instance of HFSS and open the specified project,
    which is named ``"myfile.aedt"``.

    >>> hfss = Hfss("myfile.aedt")
    PyAEDT INFO: Project myfile has been created.
    PyAEDT INFO: No design is present. Inserting a new design.
    PyAEDT INFO: Added design...


    Create an instance of HFSS using the 2023 R2 release and open
    the specified project, which is named ``"myfile2.aedt"``.

    >>> hfss = Hfss(specified_version=232, projectname="myfile2.aedt")
    PyAEDT INFO: Project myfile2 has been created.
    PyAEDT INFO: No design is present. Inserting a new design.
    PyAEDT INFO: Added design...


    Create an instance of HFSS using the 2023 R2 student version and open
    the specified project, which is named ``"myfile3.aedt"``.

    >>> hfss = Hfss(specified_version="2023.2", projectname="myfile3.aedt", student_version=True)
    PyAEDT INFO: Project myfile3 has been created.
    PyAEDT INFO: No design is present. Inserting a new design.
    PyAEDT INFO: Added design...

    """
    from pyaedt.hfss import Hfss as app

    return app(
        projectname=projectname,
        designname=designname,
        solution_type=solution_type,
        setup_name=setup_name,
        specified_version=specified_version,
        non_graphical=non_graphical,
        new_desktop_session=new_desktop_session,
        close_on_exit=close_on_exit,
        student_version=student_version,
        machine=machine,
        port=port,
        aedt_process_id=aedt_process_id,
    )


def Icepak(
    projectname=None,
    designname=None,
    solution_type=None,
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
    """Icepak Class.

    Parameters
    ----------
    projectname : str, optional
        Name of the project to select or the full path to the project
        or AEDTZ archive to open.  The default is ``None``, in which
        case an attempt is made to get an active project. If no
        projects are present, an empty project is created.
    designname : str, optional
        Name of the design to select. The default is ``None``, in
        which case an attempt is made to get an active design. If no
        designs are present, an empty design is created.
    solution_type : str, optional
        Solution type to apply to the design. The default is
        ``None``, in which case the default type is applied.
    setup_name : str, optional
        Name of the setup to use as the nominal. The default is
        ``None``, in which case the active setup is used or
        nothing is used.
    specified_version : str, int, float, optional
        Version of AEDT to use. The default is ``None``, in which case
        the active version or latest installed version is  used.
        This parameter is ignored when Script is launched within AEDT.
        Examples of input values are ``232``, ``23.2``,``2023.2``,``"2023.2"``.
    non-graphical : bool, optional
        Whether to launch AEDT in non-graphical mode. The default
        is ``False``, in which case AEDT is launched in graphical mode.
        This parameter is ignored when a script is launched within AEDT.
    new_desktop_session : bool, optional
        Whether to launch an instance of AEDT in a new thread, even if
        another instance of the ``specified_version`` is active on the
        machine.  The default is ``True``.
    close_on_exit : bool, optional
        Whether to release AEDT on exit. The default is ``False``.
    student_version : bool, optional
        Whether to open the AEDT student version. The default is ``False``.
        This parameter is ignored when a script is launched within AEDT.
    machine : str, optional
        Machine name to connect the oDesktop session to. This works only in 2022 R2 or later.
        The remote server must be up and running with the command `"ansysedt.exe -grpcsrv portnum"`.
        If the machine is `"localhost"`, the server also starts if not present.
    port : int, optional
        Port number of which to start the oDesktop communication on an already existing server.
        This parameter is ignored when creating a new server. It works only in 2022 R2 or later.
        The remote server must be up and running with the command `"ansysedt.exe -grpcsrv portnum"`.
    aedt_process_id : int, optional
        Process ID for the instance of AEDT to point PyAEDT at. The default is
        ``None``. This parameter is only used when ``new_desktop_session = False``.

    Returns
    -------
    :class:`pyaedt.icepak.Icepak`

    Examples
    --------
    Create an instance of Icepak and connect to an existing Icepak
    design or create a new Icepak design if one does not exist.

    >>> from pyaedt import Icepak
    >>> icepak = Icepak()
    PyAEDT INFO: No project is defined. Project ...
    PyAEDT INFO: Active design is set to ...

    Create an instance of Icepak and link to a project named
    ``IcepakProject``. If this project does not exist, create one with
    this name.

    >>> icepak = Icepak("IcepakProject")
    PyAEDT INFO: Project ...
    PyAEDT INFO: Added design ...

    Create an instance of Icepak and link to a design named
    ``IcepakDesign1`` in a project named ``IcepakProject``.

    >>> icepak = Icepak("IcepakProject", "IcepakDesign1")
    PyAEDT INFO: Added design 'IcepakDesign1' of type Icepak.

    Create an instance of Icepak and open the specified project,
    which is ``myipk.aedt``.

    >>> icepak = Icepak("myipk.aedt")
    PyAEDT INFO: Project myipk has been created.
    PyAEDT INFO: No design is present. Inserting a new design.
    PyAEDT INFO: Added design ...

    Create an instance of Icepak using the 2023 R2 release and
    open the specified project, which is ``myipk2.aedt``.

    >>> icepak = Icepak(specified_version=2023.2, projectname="myipk2.aedt")
    PyAEDT INFO: Project...
    PyAEDT INFO: No design is present. Inserting a new design.
    PyAEDT INFO: Added design...
    """
    from pyaedt.icepak import Icepak as app

    return app(
        projectname=projectname,
        designname=designname,
        solution_type=solution_type,
        setup_name=setup_name,
        specified_version=specified_version,
        non_graphical=non_graphical,
        new_desktop_session=new_desktop_session,
        close_on_exit=close_on_exit,
        student_version=student_version,
        machine=machine,
        port=port,
        aedt_process_id=aedt_process_id,
    )


def Emit(
    projectname=None,
    designname=None,
    solution_type=None,
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
    """Emit Class.

    Parameters
    ----------
    projectname : str, optional
        Name of the project to select or the full path to the project
        or AEDTZ archive to open.  The default is ``None``, in which case
        an attempt is made to get an active project. If no projects are
        present, an empty project is created.
    designname : str, optional
        Name of the design to select. The default is ``None``, in which case
        an attempt is made to get an active design. If no designs are
        present, an empty design is created.
    solution_type : str, optional
        Solution type to apply to the design. The default is ``None``, in which
        case the default type is applied.
    setup_name : str, optional
        Name of the setup to use as the nominal. The default is
        ``None``, in which case the active setup is used or
        nothing is used.
    specified_version : str, int, float, optional
        Version of AEDT to use. The default is ``None``, in which case
        the active setup is used or the latest installed version is
        used.
        Examples of input values are ``232``, ``23.2``,``2023.2``,``"2023.2"``.
    non_graphical : bool, optional
        Whether to launch AEDT in non-graphical mode. The default
        is ``False``, in which case AEDT is launched in graphical mode.
        This parameter is ignored when a script is launched within AEDT.
    new_desktop_session : bool, optional
        Whether to launch an instance of AEDT in a new thread, even if
        another instance of the ``specified_version`` is active on the
        machine.  The default is ``True``.
    close_on_exit : bool, optional
        Whether to release AEDT on exit. The default is ``False``.
    student_version : bool, optional
        Whether to start the AEDT student version. The default is ``False``.
    port : int, optional
        Port number on which to start the oDesktop communication on an already existing server.
        This parameter is ignored when creating a server. This parameter works only in 2022 R2 or later.
        The remote server must be up and running with the command `"ansysedt.exe -grpcsrv portnum"`.
        The default is ``0``.
    machine : str, optional
        Machine name that the Desktop session is to connect to. This
        parameter works only in 2022 R2 and later. The remote server must be
        up and running with the command `"ansysedt.exe -grpcsrv portnum"`.
        If the machine is `"localhost"`, the server starts if it is not present.
    aedt_process_id : int, optional
        Process ID for the instance of AEDT to point PyAEDT at. The default is
        ``None``. This parameter is only used when ``new_desktop_session = False``.

    Returns
    -------
    :class:`pyaedt.emit.Emit`

    Examples
    --------
    Create an ``Emit`` instance. You can also choose to define parameters for this instance here.

    >>> from pyaedt import Emit
    >>> aedtapp = Emit()

    Typically, it is desirable to specify a project name, design name, and other parameters.

    >>> aedtapp = Emit(projectname, designame, specified_version=232)

    Once an ``Emit`` instance is initialized, you can edit the schematic:

    >>> rad1 = aedtapp.modeler.components.create_component("Bluetooth")
    >>> ant1 = aedtapp.modeler.components.create_component("Antenna")
    >>> if rad1 and ant1:
    >>>     ant1.move_and_connect_to(rad1)

    Once the schematic is generated, the ``Emit`` object can be analyzed to generate
    a revision. Each revision is added as an element of the ``Emit`` object member's
    revisions_list.

    >>> aedtapp.analyze()

    A revision within PyAEDT is analogous to a revision in AEDT. An interaction domain must
    be defined and then used as the input to the run command used on that revision.

    >>> domain = aedtapp.interaction_domain()
    >>> domain.rx_radio_name = "UE - HandHeld"
    >>> interaction = aedtapp.revisions_list[0].run(domain)

    The output of the run command is an ``interaction`` object. This object summarizes the interaction data
    that is defined in the interaction domain.

    >>> instance = interaction.worst_instance(ResultType.SENSITIVITY)
    >>> val = instance.value(ResultType.SENSITIVITY)
    >>> print("Worst-case sensitivity for Rx '{}' is {}dB.".format(domain.rx_radio_name, val))
    """
    from pyaedt.emit import Emit as app

    return app(
        projectname=projectname,
        designname=designname,
        solution_type=solution_type,
        setup_name=setup_name,
        specified_version=specified_version,
        non_graphical=non_graphical,
        new_desktop_session=new_desktop_session,
        close_on_exit=close_on_exit,
        student_version=student_version,
        machine=machine,
        port=port,
        aedt_process_id=aedt_process_id,
    )


def Hfss3dLayout(
    projectname=None,
    designname=None,
    solution_type=None,
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
    """Hfss3dLayout Class.

    Parameters
    ----------
    projectname : str, optional
        Name of the project to select or the full path to the project
        or AEDTZ archive to open or the path to the ``aedb`` folder or
        ``edb.def`` file. The default is ``None``, in which case an
        attempt is made to get an active project. If no projects are present,
        an empty project is created.
    designname : str, optional
        Name of the design to select. The default is ``None``, in
        which case an attempt is made to get an active design. If no
        designs are present, an empty design is created.
    solution_type : str, optional
        Solution type to apply to the design. The default is
        ``None``, in which case the default type is applied.
    setup_name : str, optional
        Name of the setup to use as the nominal. The default is
        ``None``, in which case the active setup is used or
        nothing is used.
    specified_version : str, int, float, optional
        Version of AEDT to use. The default is ``None``, in which case
        the active version or latest installed version is used.
        Examples of input values are ``232``, ``23.2``,``2023.2``,``"2023.2"``.
    non_graphical : bool, optional
        Whether to launch AEDT in non-graphical mode. The default
        is ``False```, in which case AEDT is launched in graphical mode.
        This parameter is ignored when a script is launched within AEDT.
    new_desktop_session : bool, optional
        Whether to launch an instance of AEDT in a new thread, even if
        another instance of the ``specified_version`` is active on the
        machine. The default is ``True``.
    close_on_exit : bool, optional
        Whether to release AEDT on exit. The default is ``False``.
    student_version : bool, optional
        Whether to open the AEDT student version. The default is ``False``.
    machine : str, optional
        Machine name to connect the oDesktop session to. This works only in 2022 R2 or later.
        The remote server must be up and running with the command `"ansysedt.exe -grpcsrv portnum"`.
        If the machine is `"localhost"`. the server also starts if not present.
    port : int, optional
        Port number on which to start the oDesktop communication on an already existing server.
        This parameter is ignored when creating a new server. It works only in 2022 R2 or later.
        The remote server must be up and running with the command `"ansysedt.exe -grpcsrv portnum"`.
    aedt_process_id : int, optional
        Process ID for the instance of AEDT to point PyAEDT at. The default is
        ``None``. This parameter is only used when ``new_desktop_session = False``.

    Returns
    -------
    :class:`pyaedt.hfss3dlayout.Hfss3dLayout`

    Examples
    --------
    Create an ``Hfss3dLayout`` object and connect to an existing HFSS
    design or create a new HFSS design if one does not exist.

    >>> from pyaedt import Hfss3dLayout
    >>> aedtapp = Hfss3dLayout()

    Create an ``Hfss3dLayout`` object and link to a project named
    ``projectname``. If this project does not exist, create one with
    this name.

    >>> aedtapp = Hfss3dLayout(projectname)

    Create an ``Hfss3dLayout`` object and link to a design named
    ``designname`` in a project named ``projectname``.

    >>> aedtapp = Hfss3dLayout(projectname,designame)

    Create an ``Hfss3dLayout`` object and open the specified project.

    >>> aedtapp = Hfss3dLayout("myfile.aedt")

    Create an AEDT 2023 R1 object and then create a
    ``Hfss3dLayout`` object and open the specified project.

    >>> aedtapp = Hfss3dLayout(specified_version="2023.1", projectname="myfile.aedt")

    Create an instance of ``Hfss3dLayout`` from an ``Edb``

    >>> import pyaedt
    >>> edb_path = "/path/to/edbfile.aedb"
    >>> edb = pyaedt.Edb(edb_path, edbversion=231)
    >>> edb.import_stackup("stackup.xml")  # Import stackup. Manipulate edb, ...
    >>> edb.save_edb()
    >>> edb.close_edb()
    >>> aedtapp = pyaedt.Hfss3dLayout(specified_version=231, projectname=edb_path)
    """
    from pyaedt.hfss3dlayout import Hfss3dLayout as app

    return app(
        projectname=projectname,
        designname=designname,
        solution_type=solution_type,
        setup_name=setup_name,
        specified_version=specified_version,
        non_graphical=non_graphical,
        new_desktop_session=new_desktop_session,
        close_on_exit=close_on_exit,
        student_version=student_version,
        machine=machine,
        port=port,
        aedt_process_id=aedt_process_id,
    )


def Maxwell2d(
    projectname=None,
    designname=None,
    solution_type=None,
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
    """Maxwell2d Class.

    Parameters
    ----------
    projectname : str, optional
        Name of the project to select or the full path to the project
        or AEDTZ archive to open. The default is ``None``, in which
        case an attempt is made to get an active project. If no
        projects are present, an empty project is created.
    designname : str, optional
        Name of the design to select. The default is ``None``, in
        which case an attempt is made to get an active design. If no
        designs are present, an empty design is created.
    solution_type : str, optional
        Solution type to apply to the design. The default is
        ``None``, in which case the default type is applied.
    setup_name : str, optional
        Name of the setup to use as the nominal. The default is
        ``None``, in which case the active setup is used or
        nothing is used.
    specified_version : str, int, float, optional
        Version of AEDT to use. The default is ``None``, in which case
        the active version or latest installed version is used.
        This parameter is ignored when a script is launched within AEDT.
        Examples of input values are ``232``, ``23.2``,``2023.2``,``"2023.2"``.
    non_graphical : bool, optional
        Whether to launch AEDT in non-graphical mode. The default
        is ``False``, in which case AEDT is launched in graphical mode.
        This parameter is ignored when a script is launched within AEDT.
    new_desktop_session : bool, optional
        Whether to launch an instance of AEDT in a new thread, even if
        another instance of the ``specified_version`` is active on the
        machine. The default is ``True``. This parameter is ignored when
        a script is launched within AEDT.
    close_on_exit : bool, optional
        Whether to release AEDT on exit. The default is ``False``.
    student_version : bool, optional
        Whether to open the AEDT student version. The default is ``False``.
        This parameter is ignored when a script is launched within AEDT.
    machine : str, optional
        Machine name to connect the oDesktop session to. This works only in 2022 R2
        or later. The remote server must be up and running with the command
        `"ansysedt.exe -grpcsrv portnum"`. If the machine is `"localhost"`,
        the server also starts if not present.
    port : int, optional
        Port number of which to start the oDesktop communication on an already existing
        server. This parameter is ignored when creating a new server. It works only in 2022
        R2 or later. The remote server must be up and running with the command `"ansysedt.exe -grpcsrv portnum"`.
    aedt_process_id : int, optional
        Process ID for the instance of AEDT to point PyAEDT at. The default is
        ``None``. This parameter is only used when ``new_desktop_session = False``.

    Returns
    -------
    :class:`pyaedt.maxwell.Maxwell2d`
    """
    from pyaedt.maxwell import Maxwell2d as app

    return app(
        projectname=projectname,
        designname=designname,
        solution_type=solution_type,
        setup_name=setup_name,
        specified_version=specified_version,
        non_graphical=non_graphical,
        new_desktop_session=new_desktop_session,
        close_on_exit=close_on_exit,
        student_version=student_version,
        machine=machine,
        port=port,
        aedt_process_id=aedt_process_id,
    )


def Maxwell3d(
    projectname=None,
    designname=None,
    solution_type=None,
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
    """Maxwell3d Class.

    Parameters
    ----------
    projectname : str, optional
        Name of the project to select or the full path to the project
        or AEDTZ archive to open. The default is ``None``, in which
        case an attempt is made to get an active project. If no
        projects are present, an empty project is created.
    designname : str, optional
        Name of the design to select. The default is ``None``, in
        which case an attempt is made to get an active design. If no
        designs are present, an empty design is created.
    solution_type : str, optional
        Solution type to apply to the design. The default is
        ``None``, in which case the default type is applied.
    setup_name : str, optional
        Name of the setup to use as the nominal. The default is
        ``None``, in which case the active setup is used or
        nothing is used.
    specified_version : str, int, float, optional
        Version of AEDT to use. The default is ``None``, in which case
        the active version or latest installed version is used. This
        parameter is ignored when a script is launched within AEDT.
        Examples of input values are ``232``, ``23.2``,``2023.2``,``"2023.2"``.
    non_graphical : bool, optional
        Whether to launch AEDT in non-graphical mode. The default
        is ``False``, in which case AEDT is launched in graphical
        mode. This parameter is ignored when a script is launched within
        AEDT.
    new_desktop_session : bool, optional
        Whether to launch an instance of AEDT in a new thread, even if
        another instance of the ``specified_version`` is active on the
        machine. The default is ``True``. This parameter is ignored
        when a script is launched within AEDT.
    close_on_exit : bool, optional
        Whether to release AEDT on exit. The default is ``False``.
    student_version : bool, optional
        Whether to open the AEDT student version. The default is
        ``False``. This parameter is ignored when a script is launched
        within AEDT.
    machine : str, optional
        Machine name to connect the oDesktop session to. This works only in 2022 R2
        or later. The remote server must be up and running with the command
        `"ansysedt.exe -grpcsrv portnum"`. If the machine is `"localhost"`, the
        server also starts if not present.
    port : int, optional
        Port number on which to start the oDesktop communication on an already existing server.
        This parameter is ignored when a new server is created. It works only in 2022 R2 or later.
        The remote server must be up and running with the command `"ansysedt.exe -grpcsrv portnum"`.
    aedt_process_id : int, optional
        Process ID for the instance of AEDT to point PyAEDT at. The default is
        ``None``. This parameter is only used when ``new_desktop_session = False``.

    Returns
    -------
    :class:`pyaedt.maxwell.Maxwell3d`

    Examples
    --------
    Create an instance of Maxwell 3D and open the specified
    project, which is named ``mymaxwell.aedt``.

    >>> from pyaedt import Maxwell3d
    >>> aedtapp = Maxwell3d("mymaxwell.aedt")
    PyAEDT INFO: Added design ...

    Create an instance of Maxwell 3D using the 2023 R2 release and open
    the specified project, which is named ``mymaxwell2.aedt``.

    >>> aedtapp = Maxwell3d(specified_version="2023.2", projectname="mymaxwell2.aedt")
    PyAEDT INFO: Added design ...
    """
    from pyaedt.maxwell import Maxwell3d as app

    return app(
        projectname=projectname,
        designname=designname,
        solution_type=solution_type,
        setup_name=setup_name,
        specified_version=specified_version,
        non_graphical=non_graphical,
        new_desktop_session=new_desktop_session,
        close_on_exit=close_on_exit,
        student_version=student_version,
        machine=machine,
        port=port,
        aedt_process_id=aedt_process_id,
    )


def MaxwellCircuit(
    projectname=None,
    designname=None,
    solution_type=None,
    specified_version=None,
    non_graphical=False,
    new_desktop_session=False,
    close_on_exit=False,
    student_version=False,
    machine="",
    port=0,
    aedt_process_id=None,
):
    """MaxwellCircuit Class.

    Parameters
    ----------
    projectname : str, optional
        Name of the project to select or the full path to the project
        or AEDTZ archive to open. The default is ``None``, in which
        case an attempt is made to get an active project. If no
        projects are present, an empty project is created.
    designname : str, optional
        Name of the design to select. The default is ``None``, in
        which case an attempt is made to get an active design. If no
        designs are present, an empty design is created.
    specified_version : str, int, float, optional
        Version of AEDT to use. The default is ``None``. If ``None``,
        the active setup is used or the latest installed version is
        used.
        Examples of input values are ``232``, ``23.2``,``2023.2``,``"2023.2"``.
    non-graphical : bool, optional
        Whether to launch AEDT in non-graphical mode. The default
        is ``False``, in which case AEDT is launched in graphical mode.
        This parameter is ignored when a script is launched within AEDT.
    new_desktop_session : bool, optional
        Whether to launch an instance of AEDT in a new thread, even if
        another instance of the ``specified_version`` is active on the
        machine. The default is ``True``.
    close_on_exit : bool, optional
        Whether to release AEDT on exit. The default is ``False``.
    student_version : bool, optional
        Whether to open the AEDT student version. The default is ``False``.
    machine : str, optional
        Machine name to connect the oDesktop session to. This works only in 2022 R2
        and later. The remote server must be up and running with the command
        `"ansysedt.exe -grpcsrv portnum"`. If the machine is `"localhost"`, the server
        is also started if not present.
    port : int, optional
        Port number on which to start the oDesktop communication on an already existing server.
        This parameter is ignored when creating a new server. It works only in 2022 R2 or
        later. The remote server must be up and running with the command `"ansysedt.exe -grpcsrv portnum"`.
    aedt_process_id : int, optional
        Process ID for the instance of AEDT to point PyAEDT at. The default is
        ``None``. This parameter is only used when ``new_desktop_session = False``.

    Returns
    -------
    :class:`pyaedt.maxwellcircuit.MaxwellCircuit`
    """
    from pyaedt.maxwellcircuit import MaxwellCircuit as app

    return app(
        projectname=projectname,
        designname=designname,
        solution_type=solution_type,
        specified_version=specified_version,
        non_graphical=non_graphical,
        new_desktop_session=new_desktop_session,
        close_on_exit=close_on_exit,
        student_version=student_version,
        machine=machine,
        port=port,
        aedt_process_id=aedt_process_id,
    )


def Mechanical(
    projectname=None,
    designname=None,
    solution_type=None,
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
    """Mechanical Class.

    Parameters
    ----------
    projectname : str, optional
        Name of the project to select or the full path to the project
        or AEDTZ archive to open.  The default is ``None``, in which
        case an attempt is made to get an active project. If no
        projects are present, an empty project is created.
    designname : str, optional
        Name of the design to select. The default is ``None``, in
        which case an attempt is made to get an active design. If no
        designs are present, an empty design is created.
    solution_type : str, optional
        Solution type to apply to the design. The default is
        ``None``, in which case the default type is applied.
    setup_name : str, optional
        Name of the setup to use as the nominal. The default is
        ``None``, in which case the active setup is used or
        nothing is used.
    specified_version : str, int, float, optional
        Version of AEDT to use. The default is ``None``, in which case
        the active version or latest installed version is used.
        This parameter is ignored when a script is launched within AEDT.
        Examples of input values are ``232``, ``23.2``,``2023.2``,``"2023.2"``.
    non_graphical : bool, optional
        Whether to launch AEDT in the non-graphical mode. The default
        is ``False``, in which case AEDT is launched in the graphical mode.
        This parameter is ignored when a script is launched within AEDT.
    new_desktop_session : bool, optional
        Whether to launch an instance of AEDT in a new thread, even if
        another instance of the ``specified_version`` is active on the
        machine. The default is ``True``. This parameter is ignored when
        a script is launched within AEDT.
    close_on_exit : bool, optional
        Whether to release AEDT on exit. The default is ``False``.
    student_version : bool, optional
        Whether to open the AEDT student version. The default is ``False``.
        This parameter is ignored when a script is launched within AEDT.
    machine : str, optional
        Machine name to connect the oDesktop session to. Works only in 2022R2 and
        later. The remote server must be up and running with the command
        `"ansysedt.exe -grpcsrv portnum"`. If the machine is `"localhost"`,
        the server also starts if not present.
    port : int, optional
        Port number on which to start the oDesktop communication on an already existing server.
        This parameter is ignored when creating a new server. It works only in 2022 R2 or
        later. The remote server must be up and running with the command `"ansysedt.exe -grpcsrv portnum"`.
    aedt_process_id : int, optional
        Process ID for the instance of AEDT to point PyAEDT at. The default is
        ``None``. This parameter is only used when ``new_desktop_session = False``.

    Returns
    -------
    :class:`pyaedt.mechanical.Mechanical`

    Examples
    --------
    Create an instance of Mechanical and connect to an existing
    HFSS design or create a new HFSS design if one does not exist.

    >>> from pyaedt import Mechanical
    >>> aedtapp = Mechanical()

    Create an instance of Mechanical and link to a project named
    ``"projectname"``. If this project does not exist, create one with
    this name.

    >>> aedtapp = Mechanical(projectname)

    Create an instance of Mechanical and link to a design named
    ``"designname"`` in a project named ``"projectname"``.

    >>> aedtapp = Mechanical(projectname,designame)

    Create an instance of Mechanical and open the specified
    project, which is named ``"myfile.aedt"``.

    >>> aedtapp = Mechanical("myfile.aedt")

    Create a ``Desktop on 2023 R2`` object and then create an
    ``Mechanical`` object and open the specified project, which is
    named ``"myfile.aedt"``.

    >>> aedtapp = Mechanical(specified_version=23.2, projectname="myfile.aedt")
    """
    from pyaedt.mechanical import Mechanical as app

    return app(
        projectname=projectname,
        designname=designname,
        solution_type=solution_type,
        setup_name=setup_name,
        specified_version=specified_version,
        non_graphical=non_graphical,
        new_desktop_session=new_desktop_session,
        close_on_exit=close_on_exit,
        student_version=student_version,
        machine=machine,
        port=port,
        aedt_process_id=aedt_process_id,
    )


def Q2d(
    projectname=None,
    designname=None,
    solution_type=None,
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
    """Q2D Class.

    Parameters
    ----------
    projectname : str, optional
        Name of the project to select or the full path to the project
        or AEDTZ archive to open. The default is ``None``, in which
        case an attempt is made to get an active project. If no
        projects are present, an empty project is created.
    designname : str, optional
        Name of the design to select. The default is ``None``, in
        which case an attempt is made to get an active design. If no
        designs are present, an empty design is created.
    solution_type : str, optional
        Solution type to apply to the design. The default is
        ``None``, in which case the default type is applied.
    setup_name : str, optional
        Name of the setup to use as the nominal. The default is
        ``None``, in which case the active setup is used or
        nothing is used.
    specified_version : str, int, float, optional
        Version of AEDT to use. The default is ``None``, in which case
        the active version or latest installed version is used.  This
        parameter is ignored when a script is launched within AEDT.
        Examples of input values are ``232``, ``23.2``,``2023.2``,``"2023.2"``.
    non_graphical : bool, optional
        Whether to launch AEDT in non-graphical mode. The default
        is ``False``, in which case AEDT is launched in graphical mode.
        This parameter is ignored when a script is launched within AEDT.
    new_desktop_session : bool, optional
        Whether to launch an instance of AEDT in a new thread, even if
        another instance of the ``specified_version`` is active on the
        machine. The default is ``True``. This parameter is ignored
        when a script is launched within AEDT.
    close_on_exit : bool, optional
        Whether to release AEDT on exit. The default is ``False``.
    student_version : bool, optional
        Whether to open the AEDT student version. This parameter is
        ignored when a script is launched within AEDT.
    machine : str, optional
        Machine name to connect the oDesktop session to. This works only in 2022 R2
        and later. The remote server must be up and running with the command
        `"ansysedt.exe -grpcsrv portnum"`. If the machine is `"localhost"`,
        the server also starts if not present.
    port : int, optional
        Port number on which to start the oDesktop communication on an already existing server.
        This parameter is ignored when creating a new server. It works only in 2022 R2 or later.
        The remote server must be up and running with the command `"ansysedt.exe -grpcsrv portnum"`.
    aedt_process_id : int, optional
        Process ID for the instance of AEDT to point PyAEDT at. The default is
        ``None``. This parameter is only used when ``new_desktop_session = False``.

    Returns
    -------
    :class:`pyaedt.q3d.Q2d`
    """
    from pyaedt.q3d import Q2d as app

    return app(
        projectname=projectname,
        designname=designname,
        solution_type=solution_type,
        setup_name=setup_name,
        specified_version=specified_version,
        non_graphical=non_graphical,
        new_desktop_session=new_desktop_session,
        close_on_exit=close_on_exit,
        student_version=student_version,
        machine=machine,
        port=port,
        aedt_process_id=aedt_process_id,
    )


def Q3d(
    projectname=None,
    designname=None,
    solution_type=None,
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
    """Q3D Class.

    Parameters
    ----------
    projectname : str, optional
        Name of the project to select or the full path to the project
        or AEDTZ archive to open. The default is ``None``, in which
        case an attempt is made to get an active project. If no
        projects are present, an empty project is created.
    designname : str, optional
        Name of the design to select. The default is ``None``, in
        which case an attempt is made to get an active design. If no
        designs are present, an empty design is created.
    solution_type : str, optional
        Solution type to apply to the design. The default is
        ``None``, in which case the default type is applied.
    setup_name : str, optional
        Name of the setup to use as the nominal. The default is
        ``None``, in which case the active setup is used or nothing
        is used.
    specified_version : str, int, float, optional
        Version of AEDT to use. The default is ``None``, in which case
        the active version or latest installed version is used.
        This parameter is ignored when Script is launched within AEDT.
        Examples of input values are ``232``, ``23.2``,``2023.2``,``"2023.2"``.
    non_graphical : bool, optional
        Whether to launch AEDT in non-graphical mode. The default
        is ``False``, in which case AEDT is launched in graphical mode.
        This parameter is ignored when a script is launched within AEDT.
    new_desktop_session : bool, optional
        Whether to launch an instance of AEDT in a new thread, even if
        another instance of the ``specified_version`` is active on the
        machine. The default is ``True``. This parameter is ignored when
        a script is launched within AEDT.
    close_on_exit : bool, optional
        Whether to release AEDT on exit. The default is ``False``.
    student_version : bool, optional
        Whether to open the AEDT student version. The default is ``False``.
        This parameter is ignored when a script is launched within AEDT.
    machine : str, optional
        Machine name to connect the oDesktop session to. This works only in
        2022 R2 and later. The remote server must be up and running with the
        command `"ansysedt.exe -grpcsrv portnum"`. If the machine is `"localhost"`,
        the server also starts if not present.
    port : int, optional
        Port number on which to start the oDesktop communication on an already
        existing server. This parameter is ignored when a new server is created.
        It works only in 2022 R2 and later. The remote server must be up and
        running with the command `"ansysedt.exe -grpcsrv portnum"`.
    aedt_process_id : int, optional
        Process ID for the instance of AEDT to point PyAEDT at. The default is
        ``None``. This parameter is only used when ``new_desktop_session = False``.

    Returns
    -------
    :class:`pyaedt.q3d.Q3d`
    """
    from pyaedt.q3d import Q3d as app

    return app(
        projectname=projectname,
        designname=designname,
        solution_type=solution_type,
        setup_name=setup_name,
        specified_version=specified_version,
        non_graphical=non_graphical,
        new_desktop_session=new_desktop_session,
        close_on_exit=close_on_exit,
        student_version=student_version,
        machine=machine,
        port=port,
        aedt_process_id=aedt_process_id,
    )


def Rmxprt(
    projectname=None,
    designname=None,
    solution_type=None,
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
    """Rmxprt Class.

    Parameters
    ----------
    projectname : str, optional
        Name of the project to select or the full path to the project
        or AEDTZ archive to open. The default is ``None``, in which
        case an attempt is made to get an active project. If no
        projects are present, an empty project is created.
    designname : str, optional
        Name of the design to select. The default is ``None``, in
        which case an attempt is made to get an active design. If no
        designs are present, an empty design is created.
    solution_type : str, optional
        Solution type to apply to the design. The default is
        ``None``, in which case the default type is applied.
    model_units : str, optional
        Model units.
    setup_name : str, optional
        Name of the setup to use as the nominal. The default is
        ``None``, in which case the active setup is used or
        nothing is used.
    specified_version : str, int, float, optional
        Version of AEDT to use. The default is ``None``, in which case
        the active setup is used or the latest installed version is
        used.
        Examples of input values are ``232``, ``23.2``,``2023.2``,``"2023.2"``.
    non_graphical : bool, optional
        Whether to launch AEDT in non-graphical mode. The default
        is ``False``, in which case AEDT is launched in graphical mode.
        This parameter is ignored when a script is launched within AEDT.
    new_desktop_session : bool, optional
        Whether to launch an instance of AEDT in a new thread, even if
        another instance of the ``specified_version`` is active on the
        machine.  The default is ``True``.
    close_on_exit : bool, optional
        Whether to release AEDT on exit. The default is ``False``.
    student_version : bool, optional
        Whether to open the AEDT student version. The default is ``False``.
    machine : str, optional
        Machine name to connect the oDesktop session to. This works only in 2022 R2 or
        later. The remote server must be up and running with the command
        `"ansysedt.exe -grpcsrv portnum"`. If the machine is `"localhost"`, the
        server also starts if not present.
    port : int, optional
        Port number on which to start the oDesktop communication on an already existing server.
        This parameter is ignored when creating a new server. It works only in 2022 R2 or later.
        The remote server must be up and running with the command `"ansysedt.exe -grpcsrv portnum"`.
    aedt_process_id : int, optional
        Process ID for the instance of AEDT to point PyAEDT at. The default is
        ``None``. This parameter is only used when ``new_desktop_session = False``.

    Returns
    -------
    :class:`pyaedt.rmxprt.Rmxprt`
    """
    from pyaedt.rmxprt import Rmxprt as app

    return app(
        projectname=projectname,
        designname=designname,
        solution_type=solution_type,
        setup_name=setup_name,
        specified_version=specified_version,
        non_graphical=non_graphical,
        new_desktop_session=new_desktop_session,
        close_on_exit=close_on_exit,
        student_version=student_version,
        machine=machine,
        port=port,
        aedt_process_id=aedt_process_id,
    )


def TwinBuilder(
    projectname=None,
    designname=None,
    solution_type=None,
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
    """TwinBuilder Class.

    Parameters
    ----------
    projectname : str, optional
        Name of the project to select or the full path to the project
        or AEDTZ archive to open.  The default is ``None``, in which
        case an attempt is made to get an active project. If no
        projects are present, an empty project is created.
    designname : str, optional
        Name of the design to select. The default is ``None``, in
        which case an attempt is made to get an active design. If no
        designs are present, an empty design is created.
    solution_type : str, optional
        Solution type to apply to the design. The default is
        ``None``, in which case the default type is applied.
    setup_name : str, optional
        Name of the setup to use as the nominal. The default is
        ``None``, in which case the active setup is used or
        nothing is used.
    specified_version : str, int, float, optional
        Version of AEDT to use. The default is ``None``, in which
        case the active setup or latest installed version is
        used.
        Examples of input values are ``232``, ``23.2``,``2023.2``,``"2023.2"``.
    non_graphical : bool, optional
        Whether to launch AEDT in non-graphical mode. The default
        is ``False``, in which case AEDT is launched in graphical mode.
        This parameter is ignored when a script is launched within AEDT.
    new_desktop_session : bool, optional
        Whether to launch an instance of AEDT in a new thread, even if
        another instance of the ``specified_version`` is active on the
        machine.  The default is ``True``.
    close_on_exit : bool, optional
        Whether to release AEDT on exit. The default is ``False``.
    student_version : bool, optional
        Whether to open the AEDT student version. The default is ``False``.
    machine : str, optional
        Machine name to connect the oDesktop session to. This works only in 2022 R2
        or later. The remote server must be up and running with the command
        `"ansysedt.exe -grpcsrv portnum"`. If the machine is `"localhost"`,
        the server also starts if not present.
    port : int, optional
        Port number on which to start the oDesktop communication on an already existing server.
        This parameter is ignored when creating a new server. It works only in 2022 R2 or later.
        The remote server must be up and running with command `"ansysedt.exe -grpcsrv portnum"`.
    aedt_process_id : int, optional
        Process ID for the instance of AEDT to point PyAEDT at. The default is
        ``None``. This parameter is only used when ``new_desktop_session = False``.

    Returns
    -------
    :class:`pyaedt.twinbuilder.TwinBuilder`
    """
    from pyaedt.twinbuilder import TwinBuilder as app

    return app(
        projectname=projectname,
        designname=designname,
        solution_type=solution_type,
        setup_name=setup_name,
        specified_version=specified_version,
        non_graphical=non_graphical,
        new_desktop_session=new_desktop_session,
        close_on_exit=close_on_exit,
        student_version=student_version,
        machine=machine,
        port=port,
        aedt_process_id=aedt_process_id,
    )


def Simplorer(
    projectname=None,
    designname=None,
    solution_type=None,
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
    """Simplorer Class.

    Parameters
    ----------
    projectname : str, optional
        Name of the project to select or the full path to the project
        or AEDTZ archive to open.  The default is ``None``, in which
        case an attempt is made to get an active project. If no
        projects are present, an empty project is created.
    designname : str, optional
        Name of the design to select. The default is ``None``, in
        which case an attempt is made to get an active design. If no
        designs are present, an empty design is created.
    solution_type : str, optional
        Solution type to apply to the design. The default is
        ``None``, in which case the default type is applied.
    setup_name : str, optional
        Name of the setup to use as the nominal. The default is
        ``None``, in which case the active setup is used or
        nothing is used.
    specified_version : str, int, float, optional
        Version of AEDT to use. The default is ``None``, in which
        case the active setup or latest installed version is
        used.
        Examples of input values are ``232``, ``23.2``,``2023.2``,``"2023.2"``.
    non_graphical : bool, optional
        Whether to launch AEDT in non-graphical mode. The default
        is ``False``, in which case AEDT is launched in graphical mode.
        This parameter is ignored when a script is launched within AEDT.
    new_desktop_session : bool, optional
        Whether to launch an instance of AEDT in a new thread, even if
        another instance of the ``specified_version`` is active on the
        machine.  The default is ``True``.
    close_on_exit : bool, optional
        Whether to release AEDT on exit. The default is ``False``.
    student_version : bool, optional
        Whether to open the AEDT student version. The default is ``False``.
    machine : str, optional
        Machine name to connect the oDesktop session to. This works only in 2022 R2
        or later. The remote server must be up and running with the command
        `"ansysedt.exe -grpcsrv portnum"`. If the machine is `"localhost"`,
        the server also starts if not present.
    port : int, optional
        Port number on which to start the oDesktop communication on an already existing server.
        This parameter is ignored when creating a new server. It works only in 2022 R2 or later.
        The remote server must be up and running with command `"ansysedt.exe -grpcsrv portnum"`.
    aedt_process_id : int, optional
        Process ID for the instance of AEDT to point PyAEDT at. The default is
        ``None``. This parameter is only used when ``new_desktop_session = False``.

    Returns
    -------
    :class:`pyaedt.twinbuilder.TwinBuilder`
    """
    from pyaedt.twinbuilder import TwinBuilder as app

    return app(
        projectname=projectname,
        designname=designname,
        solution_type=solution_type,
        setup_name=setup_name,
        specified_version=specified_version,
        non_graphical=non_graphical,
        new_desktop_session=new_desktop_session,
        close_on_exit=close_on_exit,
        student_version=student_version,
        machine=machine,
        port=port,
        aedt_process_id=aedt_process_id,
    )


def Desktop(
    specified_version=None,
    non_graphical=False,
    new_desktop_session=True,
    close_on_exit=True,
    student_version=False,
    machine="",
    port=0,
    aedt_process_id=None,
):
    """Desktop Class.

    Parameters
    ----------
    specified_version : str, int, float, optional
        Version of AEDT to use. The default is ``None``, in which case the
        active setup or latest installed version is used.
        Examples of input values are ``232``, ``23.2``,``2023.2``,``"2023.2"``.
    non_graphical : bool, optional
        Whether to launch AEDT in non-graphical mode. The default
        is ``False``, in which case AEDT is launched in graphical mode.
        This parameter is ignored when a script is launched within AEDT.
    new_desktop_session : bool, optional
        Whether to launch an instance of AEDT in a new thread, even if
        another instance of the ``specified_version`` is active on the machine.
        The default is ``True``.
    close_on_exit : bool, optional
        Whether to close AEDT on exit. The default is ``True``.
        This option is used only when Desktop is used in a context manager (``with`` statement).
        If Desktop is used outside a context manager, see the ``release_desktop`` arguments.
    student_version : bool, optional
        Whether to open the AEDT student version. The default is
        ``False``.
    machine : str, optional
        Machine name to connect the oDesktop session to. This parameter works only in 2022 R2
        and later. The remote server must be up and running with the command
        `"ansysedt.exe -grpcsrv portnum"`. If the machine is `"localhost"`, the server also
        starts if not present.
    port : int, optional
        Port number on which to start the oDesktop communication on the already existing server.
        This parameter is ignored when creating a new server. It works only in 2022 R2 and
        later. The remote server must be up and running with the command `"ansysedt.exe -grpcsrv portnum"`.
    aedt_process_id : int, optional
        Process ID for the instance of AEDT to point PyAEDT at. The default is
        ``None``. This parameter is only used when ``new_desktop_session = False``.

    Returns
    -------
    :class:`pyaedt.desktop.Desktop`

    Examples
    --------
    Launch AEDT 2023 R1 in non-graphical mode and initialize HFSS.

    >>> import pyaedt
    >>> desktop = pyaedt.Desktop(specified_version="2023.2", non_graphical=True)
    PyAEDT INFO: pyaedt v...
    PyAEDT INFO: Python version ...
    >>> hfss = pyaedt.Hfss(designname="HFSSDesign1")
    PyAEDT INFO: Project...
    PyAEDT INFO: Added design 'HFSSDesign1' of type HFSS.

    Launch AEDT 2023 R2 in graphical mode and initialize HFSS.

    >>> desktop = Desktop(232)
    PyAEDT INFO: pyaedt v...
    PyAEDT INFO: Python version ...
    >>> hfss = pyaedt.Hfss(designname="HFSSDesign1")
    PyAEDT INFO: No project is defined. Project...
    """
    from pyaedt.desktop import Desktop as app

    return app(
        specified_version=specified_version,
        non_graphical=non_graphical,
        new_desktop_session=new_desktop_session,
        close_on_exit=close_on_exit,
        student_version=student_version,
        machine=machine,
        port=port,
        aedt_process_id=aedt_process_id,
    )


def launch_desktop(
    specified_version=None,
    non_graphical=False,
    new_desktop_session=True,
    close_on_exit=True,
    student_version=False,
    machine="",
    port=0,
    aedt_process_id=None,
):
    """Initializes AEDT based on the inputs provided.

    Parameters
    ----------
    specified_version : str, int, float, optional
        Version of AEDT to use. The default is ``None``, in which case the
        active setup or latest installed version is used.
    non_graphical : bool, optional
        Whether to launch AEDT in non-graphical mode. The default
        is ``False``, in which case AEDT is launched in graphical mode.
        This parameter is ignored when a script is launched within AEDT.
    new_desktop_session : bool, optional
        Whether to launch an instance of AEDT in a new thread, even if
        another instance of the ``specified_version`` is active on the machine.
        The default is ``True``.
    close_on_exit : bool, optional
        Whether to close AEDT on exit. The default is ``True``.
    student_version : bool, optional
        Whether to open the AEDT student version. The default is
        ``False``.
    machine : str, optional
        Machine name to connect the oDesktop session to. This parameters works only in 2022 R2
        and later. The remote server must be up and running with the command
        `"ansysedt.exe -grpcsrv portnum"`. If the machine is `"localhost"`, the server also
        starts if not present.
    port : int, optional
        Port number on which to start the oDesktop communication on the already existing server.
        This parameter is ignored when creating a new server. It works only in 2022 R2 and
        later. The remote server must be up and running with the command `"ansysedt.exe -grpcsrv portnum"`.
    aedt_process_id : int, optional
        Process ID for the instance of AEDT to point PyAEDT at. The default is
        ``None``. This parameter is only used when ``new_desktop_session = False``.

    Returns
    -------
    :class:`pyaedt.desktop.Desktop`


    Examples
    --------
    Launch AEDT 2021 R1 in non-graphical mode and initialize HFSS.

    >>> import pyaedt
    >>> desktop = pyaedt.launch_desktop("2022.2", non_graphical=True)
    PyAEDT INFO: pyaedt v...
    PyAEDT INFO: Python version ...
    >>> hfss = pyaedt.Hfss(designname="HFSSDesign1")
    PyAEDT INFO: Project...
    PyAEDT INFO: Added design 'HFSSDesign1' of type HFSS.

    Launch AEDT 2021 R1 in graphical mode and initialize HFSS.

    >>> desktop = Desktop("2021.2")
    PyAEDT INFO: pyaedt v...
    PyAEDT INFO: Python version ...
    >>> hfss = pyaedt.Hfss(designname="HFSSDesign1")
    PyAEDT INFO: No project is defined. Project...
    """
    d = Desktop(
        specified_version=specified_version,
        non_graphical=non_graphical,
        new_desktop_session=new_desktop_session,
        close_on_exit=close_on_exit,
        student_version=student_version,
        machine=machine,
        port=port,
        aedt_process_id=aedt_process_id,
    )
    return d


def Edb(
    edbpath=None,
    cellname=None,
    isreadonly=False,
    edbversion=None,
    isaedtowned=False,
    oproject=None,
    student_version=False,
    use_ppe=False,
    technology_file=None,
):
    """Provides the EDB application interface.

    This module inherits all objects that belong to EDB.

    Parameters
    ----------
    edbpath : str, int, float optional
        Full path to the ``aedb`` folder. The variable can also contain
        the path to a layout to import. Allowed formats are BRD,
        XML (IPC2581), GDS, and DXF. The default is ``None``.
        For GDS import, the Ansys control file (also XML) should have the same
        name as the GDS file. Only the file extension differs.
    cellname : str, optional
        Name of the cell to select. The default is ``None``.
    isreadonly : bool, optional
        Whether to open EBD in read-only mode when it is
        owned by HFSS 3D Layout. The default is ``False``.
    edbversion : str, optional
        Version of EDB to use. The default is ``"2021.2"``.
    isaedtowned : bool, optional
        Whether to launch EDB from HFSS 3D Layout. The
        default is ``False``.
    oproject : optional
        Reference to the AEDT project object.
    student_version : bool, optional
        Whether to open the AEDT student version. The default is ``False.``
    technology_file : str, optional
        Full path to technology file to be converted to xml before importing or xml. Supported by GDS format only.

    Returns
    -------
    :class:`pyaedt.edb.Edb`

    Examples
    --------
    Create an ``Edb`` object and a new EDB cell.

    >>> from pyaedt import Edb
    >>> app = Edb()

    Add a new variable named "s1" to the ``Edb`` instance.

    >>> app['s1'] = "0.25 mm"
    >>> app['s1'].tofloat
    >>> 0.00025
    >>> app['s1'].tostring
    >>> "0.25mm"

    or add a new parameter with description:

    >>> app['s2'] = ["20um", "Spacing between traces"]
    >>> app['s2'].value
    >>> 1.9999999999999998e-05
    >>> app['s2'].description
    >>> 'Spacing between traces'


    Create an ``Edb`` object and open the specified project.

    >>> app = Edb("myfile.aedb")

    Create an ``Edb`` object from GDS and control files.
    The XML control file resides in the same directory as the GDS file: (myfile.xml).

    >>> app = Edb("/path/to/file/myfile.gds")

    """
    from pyaedt.edb import Edb as app

    return app(
        edbpath=edbpath,
        cellname=cellname,
        isreadonly=isreadonly,
        edbversion=edbversion,
        isaedtowned=isaedtowned,
        oproject=oproject,
        student_version=student_version,
        use_ppe=use_ppe,
        technology_file=technology_file,
    )


def Siwave(
    specified_version=None,
):
    """Siwave Class."""
    from pyaedt.siwave import Siwave as app

    return app(
        specified_version=specified_version,
    )


app_map = {
    "Maxwell 2D": Maxwell2d,
    "Maxwell 3D": Maxwell3d,
    "Maxwell Circuit": MaxwellCircuit,
    "Twin Builder": TwinBuilder,
    "Circuit Design": Circuit,
    "2D Extractor": Q2d,
    "Q3D Extractor": Q3d,
    "HFSS": Hfss,
    "Mechanical": Mechanical,
    "Icepak": Icepak,
    "Rmxprt": Rmxprt,
    "HFSS 3D Layout Design": Hfss3dLayout,
    "EMIT": Emit,
    "EDB": Edb,
    "Desktop": Desktop,
    "Siwave": Siwave,
}


def get_pyaedt_app(project_name=None, design_name=None):
    """Returns the Pyaedt Object of specific project_name and design_name.

    Parameters
    ----------
    project_name
    design_name

    Returns
    -------
    :def :`pyaedt.Hfss`
        Any of the Pyaedt App initialized.
    """
    main = sys.modules["__main__"]
    if "oDesktop" in dir(main):
        if project_name and project_name not in main.oDesktop.GetProjectList():
            raise AttributeError("Project  {} doesn't exist in current Desktop.".format(project_name))
        if not project_name:
            oProject = main.oDesktop.GetActiveProject()
        else:
            oProject = main.oDesktop.SetActiveProject(project_name)
        if not oProject:
            raise AttributeError("No Project Present.")
        design_names = []
        deslist = list(oProject.GetTopDesignList())
        for el in deslist:
            m = re.search(r"[^;]+$", el)
            design_names.append(m.group(0))
        if design_name and design_name not in design_names:
            raise AttributeError("Design  {} doesn't exists in current Project.".format(design_name))
        if not design_name:
            oDesign = oProject.GetActiveDesign()
        else:
            oDesign = oProject.SetActiveDesign(design_name)
        if not oDesign:
            raise AttributeError("No Design Present.")
        design_type = oDesign.GetDesignType()
        if design_type in list(app_map.keys()):
            version = main.oDesktop.GetVersion().split(".")
            v = ".".join([version[0], version[1]])
            return app_map[design_type](project_name, design_name, specified_version=v)
    return None
