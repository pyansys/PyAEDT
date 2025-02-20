Filter design
==========================
The ``FilterSolutions`` module contains all classes needed to create and edit an object including. 


* ``Attributes`` to defines attributes and parameters of filters.
* ``DllInterface`` to interface with the FilterSolutions DLL.
* ``GraphSetup`` to define the frequency and time limits of the exported responses.
* ``IdealResponse`` to return the data for available ideal filter responses.
* ``MultipleBandsTable`` to manipulate access to the entries of multiple bands table.
* ``TransmissionZeros`` to manipulates access to ratio and bandwidth entries in the transmission zeros table.
* ``LumpedTopology`` to define attributes and parameters of filters implemented with lumped topology.
* ``LumpedParasitics`` to define attributes of the lumped element parasitic values.
* ``LumpedNodesandLeads`` to define attributes of the lumped node capacitors and lead inductors.
* ``LumpedTerminationImpedance`` to manipulate access to the entries of source and load complex impedance table.
* ``ExportToAedt`` to define attributes and parameters of the export page for exporting to AEDT.
* ``OptimizationGoalsTable`` to manipulate access to the entries of the optimization goals table.



They are accessible through:


.. currentmodule:: ansys.aedt.core.filtersolutions_core

.. autosummary::
   :toctree: _autosummary
   :nosignatures:

   attributes.Attributes
   dll_interface.DllInterface
   graph_setup.GraphSetup
   ideal_response.IdealResponse
   multiple_bands_table.MultipleBandsTable
   transmission_zeros.TransmissionZeros
   lumped_topology.LumpedTopology
   lumped_parasitics.LumpedParasitics
   lumped_nodes_and_leads.LumpedNodesandLeads
   lumped_termination_impedance_table.LumpedTerminationImpedance
   export_to_aedt.ExportToAedt
   optimization_goals_table.OptimizationGoalsTable
