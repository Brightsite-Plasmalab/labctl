"""
The most important part of this module is the function: :func:`regenerate_file<labctl.compatibility.regenerate_file>`.
This function is used to import a pickle file from an older version of LabCTL and convert it to a newer version, sometimes
some extra information has be provided by the user to construct the new file.

.. autofunction:: labctl.compatibility.regenerate_file
.. autoclass:: labctl.compatibility.ValueMap
"""


from labctl.compatibility._regenerate_labctl_file import regenerate_file, ValueMap