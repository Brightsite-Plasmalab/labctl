Cloning
========
Clone the repository and move into the project folder:

.. code-block:: bash

   git clone github.com/Brightsite-Plasmalab/labctl
   cd labctl

Install the needed dependencies using uv:

.. code-block:: bash

   uv sync

Optional dependency groups can be installed with ``uv`` when needed (for example,
analysis tools, GUI support, or development tooling):

.. code-block:: bash

   uv sync --group analysis
   uv sync --group dev
   uv sync --group gui

For most of the functionality in the :mod:`labctl.analysis` submodule, you need to install the ``analysis`` group.