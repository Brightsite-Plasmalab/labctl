# TODO: Is there a way to stop the BNC pulsing for the camera when stopping file execution?

import sys
import time
import threading
import queue
from typing import List, Optional

import serial
from serial.tools.list_ports import comports
from PyQt5.QtWidgets import QMessageBox, QApplication
from PyQt5.QtCore import pyqtSignal, QObject
from PyQt5 import QtWidgets

try:
    import winsound
except ImportError:
    pass

import labctl_ui

SERIAL_NEWLINE_CHARS = "\n"

# Colors (Hexadecimal strings)
COLORS_DEVICES = ["cccc00", "0000ff", "00cccc"]  # Yellow, Blue, Cyan
COLOR_META = "ff00ff"  # Magenta
COLOR_TEST_SUCCESS = "00ff00"  # Green
COLOR_TEST_FAILURE = "ff0000"  # Red
COLOR_LOG = "000000"  # Black


class SerialHandler(QObject):
    """Manages a single serial connection and its retrieval thread."""

    data_received = pyqtSignal(str)  # message
    newline_chars: bytes = SERIAL_NEWLINE_CHARS
    default_color: str = "000000"

    def __init__(
        self, index: int, color: str, newline_chars: bytes = SERIAL_NEWLINE_CHARS
    ):
        super().__init__()
        self.index = index
        self.default_color = color
        self.conn: Optional[serial.Serial] = None
        self.thread: Optional[threading.Thread] = None
        self.listening = False
        self.newline_chars = newline_chars
        self.stop_event = threading.Event()
        self._rx_queue: queue.Queue[str] = queue.Queue()

    def connect(self, port: str, baudrate: int):
        self.disconnect()
        self.conn = serial.Serial(port, baudrate=baudrate, timeout=0.1)
        self.listening = True
        self.stop_event.clear()
        # Clear any stale data from a previous connection
        with self._rx_queue.mutex:
            self._rx_queue.queue.clear()
        self.thread = threading.Thread(target=self._retrieve_data_loop, daemon=True)
        self.thread.start()

    def disconnect(self):
        self.listening = False
        self.stop_event.set()
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=1.0)
        if self.conn and self.conn.is_open:
            self.conn.close()
        self.conn = None
        self.thread = None

    def send(self, message: str):
        if self.conn and self.conn.is_open:
            self.conn.write(f"{message}{self.newline_chars}".encode("ascii"))

    def query(self, command: str, timeout: float = 1.0) -> Optional[str]:
        """Send a command and wait for the response within a given timeout.

        Reads from the shared receive queue so it is safe to call while
        _retrieve_data_loop is running in its background thread.
        """
        if not self.conn or not self.conn.is_open:
            return None

        # Discard any stale messages that arrived before this command was sent.
        with self._rx_queue.mutex:
            self._rx_queue.queue.clear()

        self.send(command)
        try:
            return self._rx_queue.get(timeout=timeout)
        except queue.Empty:
            return None

    def _retrieve_data_loop(self):
        while self.listening and not self.stop_event.is_set():
            if self.conn and self.conn.is_open:
                try:
                    message = self.conn.readline()
                    if message and message.decode().strip():
                        clean_msg = message.decode().strip()
                        # Put into queue first so query() can consume it,
                        # then also emit for live UI display.
                        self._rx_queue.put(clean_msg)
                        self.data_received.emit(clean_msg)
                except Exception as e:
                    print(f"Error reading from serial {self.index}: {e}")
                    break
            time.sleep(0.01)


class ScriptExecutor(QObject):
    """Handles parsing and execution of .labctl files."""

    add_log = pyqtSignal(str, str)  # message, color
    script_finished = pyqtSignal()
    status_message = pyqtSignal(str, bool)

    def __init__(self, serial_handlers: List[SerialHandler]):
        super().__init__()
        self.serial_handlers = serial_handlers
        self.is_running = False
        self.stop_event = threading.Event()
        self.current_selser = 0
        self.delay_submission = 0.05
        self.cmd_list: List[str] = []
        self.line_number = 0
        self.filename = ""

    def start(self, filename: str):
        self.filename = filename
        self.is_running = True
        self.stop_event.clear()
        self.line_number = 0
        self.current_selser = 0

        try:
            with open(filename, "r") as f:
                self.cmd_list = [line.strip() for line in f]
            threading.Thread(target=self._run_loop, daemon=True).start()
        except Exception as e:
            self.status_message.emit(f"Failed to open script: {e}", True)
            self.script_finished.emit()

    def stop(self):
        self.is_running = False
        self.stop_event.set()

    def _run_loop(self):
        timestamp = time.strftime("%H_%M_%S", time.localtime())
        log_filename = self.filename.replace(".labctl", f"_log_{timestamp}.txt")
        full_log = []

        while self.cmd_list and self.is_running and not self.stop_event.is_set():
            self.line_number += 1
            raw_command = self.cmd_list.pop(0)
            if not raw_command:
                continue

            # Handle comments and meta-commands
            command = raw_command
            if raw_command:
                cmd_part, _, comment = raw_command.partition("#")
                if comment.strip():
                    self._log(comment.strip(), COLOR_LOG)
                if raw_command.strip().startswith("#"):
                    # Only a comment or a Meta Command
                    if self._handle_meta_command(raw_command):
                        continue
                    continue
                command = cmd_part.strip()

            if not command:
                continue

            # Execute serial command
            handler = self.serial_handlers[self.current_selser]
            handler.send(command)
            self._log(command.strip(), handler.default_color)

            time.sleep(self.delay_submission)

        self.is_running = False
        self._log("LOG: Script execution finished.", COLOR_LOG)
        self.script_finished.emit()

        # Save log file at the end
        try:
            with open(log_filename, "w") as f:
                f.write("\n".join(full_log))
        except Exception:
            pass

    def _handle_meta_command(self, cmd: str) -> bool:
        if cmd.startswith("#WAIT"):
            try:
                ms = int(cmd[5:].strip())
                self._log(f"Waiting for {ms} ms", COLOR_META)
                time.sleep(ms / 1000.0)
                return True
            except ValueError:
                pass
        elif cmd.startswith("#SELSER"):
            try:
                idx = int(cmd[7:].strip())
                if 0 <= idx < len(self.serial_handlers):
                    self.current_selser = idx
                    self._log(f"Selected serial port {idx}", COLOR_META)
                else:
                    self.status_message.emit(f"Invalid serial port index: {idx}", True)
                return True
            except ValueError:
                pass
        elif cmd.strip() == "#BEEP":
            self._log("Beep!", COLOR_META)
            try:
                winsound.MessageBeep()
            except:
                pass
            return True
        elif cmd.startswith("#TEST"):
            try:
                # Format: #TEST command == expected_result # comment
                # or:     #TESTn command == expected_result # comment
                # where n limits comparison to the first n characters of the response
                prefix = cmd.split()[0]  # e.g. "#TEST" or "#TEST3"
                char_limit_str = prefix[5:]  # everything after "#TEST"
                char_limit = int(char_limit_str) if char_limit_str else None

                body = cmd[len(prefix) :].strip()
                comment = ""
                # Extract trailing comment after the result part
                # Split on == first, then check for # in the expected part
                parts = body.split("==")
                if len(parts) == 2:
                    command = parts[0].strip()
                    expected_part = parts[1]
                    if "#" in expected_part:
                        expected_str, _, comment = expected_part.partition("#")
                        expected = expected_str.strip()
                        comment = comment.strip()
                    else:
                        expected = expected_part.strip()

                    handler = self.serial_handlers[self.current_selser]

                    self._log(f"Checking: {command}", handler.default_color)
                    response = handler.query(command, timeout=1.0)

                    label = f" ({comment})" if comment else ""
                    if response is not None:
                        compared = response[:char_limit] if char_limit else response
                        if compared == expected:
                            self._log(
                                f"Success{label}: {compared} == {expected}",
                                COLOR_TEST_SUCCESS,
                            )
                        else:
                            self._log(
                                f"Failure{label}: {compared} != {expected}",
                                COLOR_TEST_FAILURE,
                            )
                            self.status_message.emit(
                                f"Verification failed{label}: {compared} != {expected}",
                                True,
                            )
                    else:
                        self._log(
                            f"Failure{label}: No response received", COLOR_TEST_FAILURE
                        )
                        self.status_message.emit(
                            f"Verification failed{label}: No response", True
                        )
                    return True
            except Exception as e:
                self._log(f"Error in #RESULT: {e}", COLOR_TEST_FAILURE)
        return False

    def _log(self, message: str, color: str):
        timestamp = time.strftime("%H:%M:%S", time.localtime())
        formatted = f"{timestamp} | Line {self.line_number}: {message}"
        self.add_log.emit(formatted, color)


class ExampleApp(QtWidgets.QMainWindow, labctl_ui.Ui_MainWindow):
    addline = pyqtSignal(str)
    ports: List[str] = []
    init_btns: List[QtWidgets.QPushButton] = []
    send_btns: List[QtWidgets.QPushButton] = []
    cmd_widgets: List[QtWidgets.QLineEdit] = []
    port_widgets: List[QtWidgets.QComboBox] = []
    baud_widgets: List[QtWidgets.QComboBox] = []
    serial_handlers: List[SerialHandler] = []
    script_executor: Optional[ScriptExecutor] = None
    scriptmode_active: bool = False

    def __init__(self):
        super(self.__class__, self).__init__()
        self.setupUi(self)  # This is defined in design.py file automatically

        self.actionExit.triggered.connect(self.close)
        self.actionAbout.triggered.connect(self.about)

        self.execLabctlScript_btn.clicked.connect(self.execLabctlScript)
        self.cmdPath_lE.returnPressed.connect(self.execLabctlScript)

        self.update_list_btn.clicked.connect(self.add_ports)
        self.init_btns = [self.init_btn, self.init_btn_1, self.init_btn_2]
        self.send_btns = [self.send_btn_0, self.send_btn_1, self.send_btn_2]
        self.cmd_widgets = [self.cmd_0, self.cmd_1, self.cmd_2]
        self.port_widgets = [self.port_cB, self.port_cB_1, self.port_cB_2]
        self.baud_widgets = [self.baudrate_cB, self.baudrate_cB_1, self.baudrate_cB_2]

        for i in range(3):
            self.init_btns[i].clicked.connect(lambda _, idx=i: self.serial_connect(idx))
            self.send_btns[i].clicked.connect(lambda _, idx=i: self.write_data(idx))
            self.cmd_widgets[i].returnPressed.connect(
                lambda idx=i: self.write_data(idx)
            )
        self.add_ports()

        self.addline.connect(self.log_TE.append)

        self.serial_handlers: List[SerialHandler] = [
            SerialHandler(0, COLORS_DEVICES[0]),
            SerialHandler(1, COLORS_DEVICES[1]),
            SerialHandler(2, COLORS_DEVICES[2]),
        ]
        for i, handler in enumerate(self.serial_handlers):
            handler.data_received.connect(
                lambda msg, h=handler, idx=i: self.addline.emit(
                    self.color(msg, COLORS_DEVICES[idx])
                )
            )

        self.script_executor = ScriptExecutor(self.serial_handlers)
        self.script_executor.add_log.connect(
            lambda msg, color: self.addline.emit(self.color(msg, color))
        )
        self.script_executor.script_finished.connect(self._on_script_finished)
        self.script_executor.status_message.connect(self._statusbar_message)

    def _on_script_finished(self):
        self.scriptmode_active = False
        self.execLabctlScript_btn.setText("Start executing commands from file")

    def close_connection(self):
        for handler in self.serial_handlers:
            handler.disconnect()

    def color(self, text, color):
        return f'<span style=" font-size:8pt; font-weight:600; color:#{color};" >{text}</span>'

    def about(self):
        QMessageBox.about(
            self,
            "About",
            "Tool for simplifying the communication with BNCs delay generators\nThuwal\nDDCB 2019",
        )

    def _statusbar_message(self, message: str, error: bool = False):
        if error:
            self.statusbar.setStyleSheet(
                "QStatusBar{padding-left:8px;background:rgba(255,0,0,255);color:black;font-weight:bold;}"
            )
        else:
            self.statusbar.setStyleSheet("")
        self.statusBar().showMessage(message)

    def serial_connect(self, index: int):
        port = self.port_widgets[index].currentText()
        baudrate = int(self.baud_widgets[index].currentText())

        used_coms = [
            h.conn.port
            for i, h in enumerate(self.serial_handlers)
            if h.conn is not None and h.conn.is_open and i != index
        ]

        if port in used_coms:
            self._statusbar_message(
                f'"{port}" already in use. Please select another port.', True
            )
            return

        try:
            handler = self.serial_handlers[index]
            handler.connect(port, baudrate)
            self._statusbar_message(
                f"Just connected channel {index} to {port} with baud rate {baudrate}..."
            )

            # Enable buttons based on index
            self.send_btns[index].setEnabled(True)
        except Exception as e:
            self._statusbar_message(f"Failed to connect to {port}: {e}", True)

    def add_ports(self):
        for port_widget in self.port_widgets:
            for n in range(8):
                port_widget.removeItem(0)
            for n, (port, desc, hwid) in enumerate(sorted(comports()), 1):
                port_widget.addItem(port)

    def write_data(self, index: int):
        port = self.port_widgets[index].currentText()
        handler = self.serial_handlers[index]
        commands = self.cmd_widgets[index].text().split("#")[0].split("|")

        for line in commands:
            if not line.strip():
                continue
            message = "{}\n".format(line.strip())
            handler.send(message)
            self.addline.emit(
                self.color("{}".format(message.rstrip("\n")), handler.default_color)
            )
            self._statusbar_message(f'Sent "{message}" to {index} ({port}) ...')

    def execLabctlScript(self):
        filename = self.cmdPath_lE.text().replace("file:///", "")

        if not self.script_executor.is_running:
            self.execLabctlScript_btn.setText("Stop script")
            self.script_executor.start(filename)
        else:
            self.script_executor.stop()
            self.execLabctlScript_btn.setText("Execute script")

    def closeEvent(self, *args, **kwargs):
        super(QtWidgets.QMainWindow, self).closeEvent(*args, **kwargs)
        self.scriptmode_active = False
        # self.timeToEnd.set()
        self.close_connection()
        print("Wait few seconds.. trying to kill few surviving threads..")


def main():
    app = QApplication(sys.argv)
    form = ExampleApp()  # We set the form to be our ExampleApp (design)
    form.show()  # Show the form
    app.exec_()  # and execute the app


if __name__ == "__main__":  # if we're running file directly and not importing it
    main()  # run the main function
