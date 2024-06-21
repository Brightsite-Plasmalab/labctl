# labctl
A simple experiment automation library for devices with serial communication. 

# Graphical User Interface (GUI)

This package includes a GUI with the following features:
- Connect to serial devices
- Write serial commands
- Read serial output
- Execute scripts that read & write serial communication

# Syntax

This module generates scripts (`.labctl` files). They consists of:
- Serial commands. These are submitted to serial devices as you would normally.
- Meta commands. These are commands to the LabCTL interpreter and will not be transmitted over serial communication:
  - `#SELSER 0`: Selects serial device 0.
  - `#WAIT 123`: Waits for 123 milliseconds before continuing execution of the script.
  - `# Some comment`: Displays some comment to the GUI. <br/>
  NB: There should be a space after the `#`.