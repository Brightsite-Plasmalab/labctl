Cloning
========
Clone the repository and move into the project folder:

.. code-block:: bash

   git clone github.com/Brightsite-Plasmalab/labctl
   cd labctl

Install the needed dependencies using uv:

.. code-block:: bash

   uv sync

Optional dependency groups can be installed with ``uv`` when needed:

.. code-block:: bash

   uv sync --group analysis
   uv sync --group dev
   uv sync --group gui

For most of the functionality in the :mod:`labctl.analysis` submodule, you need to install the ``analysis`` group.

Using the cloned repository
---------------------------
When cloning you can also use the standard scripts located in the folder ``experiments``. This folder contains sub-folders
for most of the experiment, each sub-folder contains one file to generate the labctl file ``labctl_*.py`` and one file with
a simple analysis script ``analysis_*.py``
