Syntax
-------
The syntax for the LabCTL interpreter is very simple:

* If a line does not start with ``#``, it is sent to the currently active serial channel.
* If a line starts with ``#``, it is interpreted by LabCTL:
    * ``#SELSER 0`` selects channel 0 as the currently active serial channel
    * ``#WAIT 500`` pauses for 500ms.
    * ``# Some brief explanation`` prints *"Some brief explanation"* to the command window.