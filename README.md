# labctl
A simple experiment automation library for devices with serial communication. 

## Installation
1. 
   (a) Download this repository to your computer

   OR

   (b) Clone this repo using your Git Client of choice (e.g. Sourcetree or Git Kraken), or by running the following command:<br/>
`git clone git@github.com:Brightsite-Plasmalab/labctl.git`
1. (Optional) open the folder in your code editor of choice (VS Code, Spyder, PyCharm, ...)
2. For Anaconda users:
   - Open an Anaconda Prompt
   - Optional: if you use an environment other than `base`, open it using `conda activate [my environment]`
   - Install pip using `conda install pip`
3. (Optional) to install this module in a virtual environment, [activate it](https://docs.python.org/3/library/venv.html#how-venvs-work).
4. Install the module using `pip install -e [path_to_labctl]`, replacing `[path_to_labctl]` with the directory of this repository.

## Graphical User Interface (GUI)

(WORK IN PROGRESS)
This package includes a GUI with the following features:
- Connect to serial devices
- Write serial commands
- Read serial output
- Execute scripts that read & write serial communication

## Scripting syntax

The GUI can execute LabCTL scripts (`.labctl` files). The scripts consist of:
- Serial commands. These are submitted to serial devices.
- Meta commands. These are commands to the LabCTL interpreter and will not be transmitted over serial communication:
  - `#SELSER 0`: Selects serial device 0.
  - `#WAIT 123`: Waits for 123 milliseconds before continuing execution of the script.
  - `# Some comment`: Displays "Some comment" to the GUI. <br/>
  NB: There should be a space after the `#`.

One can choose to create such a `.labctl` file in three ways:
- Manually writing the necessary commands.
- Using the Python `labctl.devices` classes to automate device behaviour.
- Using the Python `labctl.experiment` classes to automate a complete experiment. See below.

## Devices
To make it easier to control devices that are common in our lab, we implemented the following:

- Thorlabs translation stage [(link)](https://www.thorlabs.com/newgrouppage9.cfm?objectgroup_id=9464).
- BNC Model 577 Pulse Delay Generator [(link)](https://www.berkeleynucleonics.com/model-577).
- Physik Instrumente translation stages, using the Mercury GCS command set [(link)](https://twiki.cern.ch/twiki/pub/ILCBDSColl/Phase2Preparations/Mercury_GCS_Commands_MS163E102.pdf).

If there's any serial devices that you'd like to request, please implement them in a [pull request](https://github.com/Brightsite-Plasmalab/labctl/pulls). If it's a device specific to the Brightsite Plasma Lab, please open an [issue](https://github.com/Brightsite-Plasmalab/labctl/issues) to let us develop it.

## Experiments
Some experiments execute a structured set of commands, and are dependent on a set of parameters. We recommend to create an `Experiment` subclass in such case.