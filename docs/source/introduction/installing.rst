Installing
===========
For a regular local install from a checked-out repository:

.. code-block:: bash

   uv add "git+https://github.com"
   uv sync


For most of the functionality in the :mod:`labctl.analysis` submodule, you need to add the ``analysis`` group:

.. code-block:: bash

   uv add "git+https://github.com" --group analysis
   uv sync