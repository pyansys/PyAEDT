Filter design
====================
This section describes the classes used for creating and modifying parameters in the ``filtersolutions`` module.
The module provides tools for designing and customizing filter configurations. 

The module includes two classes, ``LumpedDesign`` and ``DistributedDesign``, both inherited from the ``FilterDesignBase`` class as described in the :ref:`BaseFilterDesign` section.

Each class implements methods specific to its design approach while leveraging common functionality from the base class.


Lumped design
~~~~~~~~~~~~~~~~~~~
The ``LumpedDesign`` module includes all the necessary classes for creating and modifying parameters used in lumped filter designs.
Lumped filters use discrete components such as capacitors, inductors, and resistors.

* ``LumpedTopology`` to define attributes and parameters of filters implemented using a lumped topology.
* ``LumpedParasitics`` to define attributes of parasitic values associated with lumped elements.
* ``LumpedNodesandLeads`` to define attributes of the lumped node capacitors and lead inductors.
* ``LumpedTerminationImpedance`` to manage access to the entries in the source and load complex impedance table.

They are accessible through:


.. currentmodule:: ansys.aedt.core.filtersolutions_core

.. autosummary::
   :toctree: _autosummary
   :nosignatures:


   lumped_topology.LumpedTopology
   lumped_parasitics.LumpedParasitics
   lumped_nodes_and_leads.LumpedNodesandLeads
   lumped_termination_impedance_table.LumpedTerminationImpedance

``Lumped Filter`` example:

.. code:: python

    import ansys.aedt.core
    import ansys.aedt.core.filtersolutions
    # This call returns an instance of the LumpedDesign class
    design = ansys.aedt.core.FilterSolutions.LumpedDesign(version= "2025.1")
    # This property in the Attributes class specifies the filter class as band pass
    design.attributes.filter_class = FilterClass.BAND_PASS
    # This property in the Attributes class specifies the filter type as Elliptic
    design.attributes.filter_type = FilterType.ELLIPTIC   
    # This property in the LumpedTopology class enables the trap topology by setting it to true
    design.topology.trap_topology = True
    ...



Distributed design
~~~~~~~~~~~~~~~~~~~
The ``DistributedDesign`` module includes all the necessary classes for creating and modifying parameters used in distributed filter designs.
Distributed filters rely on transmission lines and resonators.

* ``DistributedTopology`` to define attributes and parameters of filters implemented using a distributed topology.
* ``DistributedSubstrate`` to define attributes and  parameters of the substrate used in distributed filters.
* ``DistributedGeometry`` to define attributes and parameters of the substrate geometry used in distributed filters.
* ``DistributedRadial`` to define attributes and parameters of the substrate radial used in distributed filters.


They are accessible through:


.. currentmodule:: ansys.aedt.core.filtersolutions_core

.. autosummary::
   :toctree: _autosummary
   :nosignatures:


   distributed_topology.DistributedTopology
   distributed_substrate.DistributedSubstrate
   distributed_geometry.DistributedGeometry
   distributed_radial.DistributedRadial

``Distributed Filter`` example:

.. code:: python

    import ansys.aedt.core
    import ansys.aedt.core.filtersolutions
    # This call returns an instance of the DistributedDesign class
    design = ansys.aedt.core.FilterSolutions.DistributedDesign(version= "2025.2")
    # This property in the Attributes class specifies the filter class as band pass
    design.attributes.filter_class = FilterClass.BAND_PASS
    # This property in the Attributes class specifies the filter type as Elliptic
    design.attributes.filter_type = FilterType.ELLIPTIC   
    # This property in the DistributedTopology class sets the load resistance to 50 ohms.
    design.topology.load_resistance = "50"
    ...




.. _BaseFilterDesign:

Base filter design
~~~~~~~~~~~~~~~~~~~
The ``FilterDesignBase`` module provides all the essential classes for creating and modifying the primary parameters applicable to all design types.

* ``Attributes`` to define attributes and parameters of filters.
* ``GraphSetup`` to define the frequency and time graph parameters of the exported responses.
* ``IdealResponse`` to return the data for the available ideal filter responses.
* ``MultipleBandsTable`` to manage access to the entries in the multiple bands table.
* ``TransmissionZeros`` to manage access to ratio and bandwidth entries in the transmission zeros table.
* ``ExportToAedt`` to define attributes and parameters for the export page when exporting to AEDT.
* ``OptimizationGoalsTable`` to manage access to the entries in the optimization goals table.

They are accessible through:


.. currentmodule:: ansys.aedt.core.filtersolutions_core

.. autosummary::
   :toctree: _autosummary
   :nosignatures:


   attributes.Attributes
   graph_setup.GraphSetup
   ideal_response.IdealResponse
   multiple_bands_table.MultipleBandsTable
   transmission_zeros.TransmissionZeros
   export_to_aedt.ExportToAedt
   optimization_goals_table.OptimizationGoalsTable

