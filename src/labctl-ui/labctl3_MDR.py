# TODO: Is there a way to stop the BNC pulsing for the camera when stopping file execution?

import sys
import time
import threading

import serial
from serial.tools.list_ports import comports
from PyQt5.QtWidgets import QMessageBox, QApplication
from PyQt5.QtCore import pyqtSignal
from PyQt5 import QtWidgets

import minimale_widget_st_multi


class ExampleApp(QtWidgets.QMainWindow, minimale_widget_st_multi.Ui_MainWindow):
    counter = pyqtSignal(str)
    addline = pyqtSignal(str)
    execLabctlScript_btn_changeText = pyqtSignal(str)
    update_statusbar = pyqtSignal(str)
    timeToEnd = threading.Event()
    ESEGUI = pyqtSignal(str)
    scriptmode_active = False
    filename = ""
    selser = 0
    linenumber = 0
    delayCmdSubmission = 0.05  # s - delay between instructions
    cmdlist = list()
    datarec = list()
    timerec = list()
    bookmarks = dict()

    def __init__(self):
        super(self.__class__, self).__init__()
        self.setupUi(self)  # This is defined in design.py file automatically

        self.actionExit.triggered.connect(self.close)
        self.actionAbout.triggered.connect(self.about)

        self.add_ports()

        self.execLabctlScript_btn.clicked.connect(self.execLabctlScript)
        self.cmdPath_lE.returnPressed.connect(self.execLabctlScript)

        self.update_list_btn.clicked.connect(self.add_ports)
        self.init_btn.clicked.connect(self.serial_connect_0)
        self.init_btn_1.clicked.connect(self.serial_connect_1)
        self.init_btn_2.clicked.connect(self.serial_connect_2)
        self.move_btn.clicked.connect(self.send_move_request)
        self.stop_btn.clicked.connect(self.send_stop_request)
        self.send_btn_0.clicked.connect(self.write_data)
        self.cmd_0.returnPressed.connect(self.write_data)

        self.send_btn_1.clicked.connect(self.write_data_1)
        self.cmd_1.returnPressed.connect(self.write_data_1)

        self.send_btn_2.clicked.connect(self.write_data_2)
        self.cmd_2.returnPressed.connect(self.write_data_2)

        self.addline.connect(self.log_TE.append)
        self.execLabctlScript_btn_changeText.connect(self.execLabctlScript_btn.setText)
        self.update_statusbar.connect(self._statusbar_message)

        self.counter.connect(self.send_btn.setText)

        self._listening: list[bool] = [
            False,
            False,
            False,
        ]  # TODO: implement some correct shared state between threads
        self._threads: list[threading.Thread | None] = [None, None, None]
        self._serial_conns: list[serial.Serial | None] = [None, None, None]

    def close_connection(self):
        self._listening = [False, False, False]
        for thread in self._threads:
            if thread is not None:
                thread.join()
        for conn in self._serial_conns:
            if conn is not None:
                conn.close()
        self._serial_conns = [None, None, None]

    def color(self, text, color):
        return '<span style=" font-size:8pt; font-weight:600; color:#{};" >{}</span>'.format(
            color, text
        )

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

    def _serial_connect(self, index, port, baudrate, run_func):
        self._listening[index] = False
        if self._threads[index] is not None:
            self._threads[index].join()
        if self._serial_conns[index] is not None:
            self._serial_conns[index].close()

        used_coms = [
            conn.port
            for i, conn in enumerate(self._serial_conns)
            if conn is not None and conn.is_open
        ]

        if port in used_coms:
            self._statusbar_message(
                f'"{port}" already in use. Please select another port.', True
            )
            return

        self._serial_conns[index] = serial.Serial(
            port,
            baudrate=baudrate,
            timeout=0.1,
        )
        print(self._serial_conns[index])
        self._statusbar_message("Just connected to {}...".format(port))
        self._listening[index] = True
        self._threads[index] = threading.Thread(target=run_func)
        self._threads[index].start()

    def serial_connect_0(self):
        self._serial_connect(
            0,
            self.port_cB.currentText(),
            int(self.baudrate_cB.currentText()),
            self.retrieve_data_0,
        )
        # enable few other pushbuttons
        self.move_btn.setEnabled(True)
        self.stop_btn.setEnabled(True)
        self.send_btn_0.setEnabled(True)
        self.execLabctlScript_btn.setEnabled(True)

    def serial_connect_1(self):
        self._serial_connect(
            1,
            self.port_cB_1.currentText(),
            int(self.baudrate_cB_1.currentText()),
            self.retrieve_data_1,
        )
        # enable few other pushbuttons
        self.send_btn_1.setEnabled(True)

    def serial_connect_2(self):
        self._serial_connect(
            2,
            self.port_cB_2.currentText(),
            int(self.baudrate_cB_2.currentText()),
            self.retrieve_data_2,
        )
        # enable few other pushbuttons
        self.send_btn_2.setEnabled(True)

    def add_ports(self):
        for n in range(8):
            self.port_cB.removeItem(0)
            self.port_cB_1.removeItem(0)
            self.port_cB_2.removeItem(0)
        for n, (port, desc, hwid) in enumerate(sorted(comports()), 1):
            self.port_cB.addItem(port)
            self.port_cB_1.addItem(port)
            self.port_cB_2.addItem(port)

    def _write_data(self, commands, serial_conn, color, name):
        for line in commands.text().split("#")[0].split("|"):
            if len(line) == 0:
                continue
            message = "{}\n".format(line)
            serial_conn.write(message.encode("ascii"))
            self.addline.emit(self.color("{}".format(message.rstrip("\n")), color))
            self._statusbar_message(
                f'Sent "{message}" to {name} {self.port_cB.currentText()}...'
            )

    def write_data(self):
        self._write_data(self.cmd_0, self._serial_conns[0], "ff0000", "0")

    def write_data_1(self):
        self._write_data(self.cmd_1, self._serial_conns[1], "cccc00", "1")

    def write_data_2(self):
        self._write_data(self.cmd_2, self._serial_conns[2], "0000ff", "2")

    def execLabctlScript(self):
        self.selser = 0  # Select serial port 0 by default. If scripts need other serial ports, they should use metacommands to select them.
        self.filename = self.cmdPath_lE.text()
        self.filename = str(self.filename).replace("file:///", "")

        if not self.scriptmode_active:
            self.scriptmode_active = True
            self.execLabctlScript_btn.setText("Stop executing commands from file")
            thread2 = threading.Thread(target=self.start_execution_list)
            thread2.start()
        else:
            self.scriptmode_active = False
            self.execLabctlScript_btn.setText("Start executing commands from file")

    def start_execution_list(self):
        # open file
        if self.timeToEnd.is_set():
            return
        if not self.scriptmode_active:
            return
        with open(self.filename, "r") as f:
            self.cmdlist = [line.rstrip("\n") for line in f]
        self.dispach_instr(sendAll=True)

    def dispach_instr(self, sendAll=False):
        timestamp = time.strftime("%H_%M_%S", time.localtime())
        name_out = self.filename.replace(".labctl", f"log_{timestamp}.txt")
        linenumber = 0

        def log_format_line(command, color):
            nonlocal linenumber
            timestamp = time.strftime("%H:%M:%S", time.localtime())
            self.addline.emit(
                self.color(f"{timestamp} | Line {linenumber}: {command}", color)
            )

        while len(self.cmdlist) != 0:
            if self.timeToEnd.is_set():
                return
            if not self.scriptmode_active:
                return
            linenumber += 1
            command = self.cmdlist.pop(0).strip()
            if command == "":
                continue

            if command.startswith("# ") or "#" in command[1:]:
                cmd, _, comment = command.partition("#")
                # Meta command: print comment
                if len(comment) > 0:
                    log_format_line(comment.strip("\n"), "000000")

                # If it is only a comment continue, otherwise execute the command
                if command.startswith("# "):
                    continue
                command = cmd

            # Meta command: wait a specified amount of milliseconds
            if command.startswith("#WAIT"):
                wtime = int(command[5:].strip())
                log_format_line("Waiting for {} ms".format(wtime), "ff00ff")
                time.sleep(1e-3 * wtime)
                continue

            # Meta command: select a specified serial port
            if command.startswith("#SELSER"):
                self.selser = int(command[7:].strip())
                if self.selser not in (0, 1, 2):
                    self._statusbar_message(
                        f"Tried to select invalid serial port! COM {self.selser}", True
                    )
                    return

                log_format_line("Selected serial port {}".format(self.selser), "ff00ff")
                continue

            # Everything else is real serial commands
            # here there should be the check on which serial port to send the information
            if self.selser == 0:
                color = "ff0000"
            elif self.selser == 1:
                color = "cccc00"
            else:
                color = "0000ff"
            message = "{}\r\n".format(command)
            self._serial_conns[self.selser].write(message.encode("ascii"))
            log_format_line(
                message,
                color,
            )
            time.sleep(self.delayCmdSubmission)

            if len(self.cmdlist) == 0:
                self.scriptmode_active = False
                self.execLabctlScript_btn_changeText.emit(
                    "Start executing commands form file"
                )
                log_format_line("LOG: Completed command list! Stopping now", "000000")

            if not sendAll:
                break

        with open(name_out, "w") as f:
            f.write(str(self.log_TE.toPlainText()))

    def send_move_request(self):
        self._serial_conns[0].write(":INST:STATE ON\n".encode("ascii"))
        self._statusbar_message("Sent BNC delay generator start command")

    def send_stop_request(self):
        self._serial_conns[0].write(":INST:STATE OFF\n".encode("ascii"))
        self._statusbar_message("Sent BNC delay generator Stop command")

    def _retrieve_data(self, ser_conn, color):
        message = ser_conn.readline()
        if message != b"" and message != b"\n" and message != b"\r\n":
            if message[-2:] == b"\r\n":
                message = message[:-2]
            self.addline.emit(self.color(message.decode(), color))

    def retrieve_data_0(self):
        while self._listening[0]:
            self._retrieve_data(self._serial_conns[0], "00ff00")
            if self.timeToEnd.is_set():
                break

    def retrieve_data_1(self):
        while self._listening[1]:
            self._retrieve_data(self._serial_conns[1], "00cccc")
            if self.timeToEnd.is_set():
                break

    def retrieve_data_2(self):
        while self._listening[2]:
            self._retrieve_data(self._serial_conns[2], "0000ff")
            if self.timeToEnd.is_set():
                break

    def closeEvent(self, *args, **kwargs):
        super(QtWidgets.QMainWindow, self).closeEvent(*args, **kwargs)
        self.scriptmode_active = False
        self.timeToEnd.set()
        self.close_connection()
        print("Wait few seconds.. trying to kill few surviving threads..")


def main():
    app = QApplication(sys.argv)
    form = ExampleApp()  # We set the form to be our ExampleApp (design)
    form.show()  # Show the form
    app.exec_()  # and execute the app


if __name__ == "__main__":  # if we're running file directly and not importing it
    main()  # run the main function
