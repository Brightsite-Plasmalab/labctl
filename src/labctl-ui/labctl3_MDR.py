from threading import Thread
import sys
import os
import time
import numpy as np
import serial
import threading
from serial.tools.list_ports import comports
import warnings
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5 import QtCore, QtGui, QtWidgets

import minimale_widget_st_multi


class ExampleApp(QtWidgets.QMainWindow, minimale_widget_st_multi.Ui_MainWindow):
    counter = pyqtSignal(str)
    addline = pyqtSignal(str)
    execBNC_btn_changeText = pyqtSignal(str)
    update_statusbar = pyqtSignal(str)
    timeToEnd = threading.Event()
    ports = list()
    ESEGUI = pyqtSignal(str)
    listening = False
    listening_stage = False
    scriptmode_active = False
    acquiring = False
    filename = ""
    ser = None  # diventer per l'oggetto seriale stepper
    ser_stage = None  # diventer per l'oggetto seriale bnc
    selser = 0
    linenumber = 0
    # s - delay between instructions sent to the BNC delay generator
    delayCmdSubmission = 0.05
    cmdlist = list()
    datarec = list()
    timerec = list()
    bookmarks = dict()
    active_serial = 1

    def __init__(self):
        super(self.__class__, self).__init__()
        self.setupUi(self)  # This is defined in design.py file automatically

        self.actionExit.triggered.connect(self.close)
        self.actionAbout.triggered.connect(self.ab)

        self.add_ports()

        self.execBNC_btn.clicked.connect(self.execBNC)
        self.cmdPath_lE.returnPressed.connect(self.execBNC)

        self.update_list_btn.clicked.connect(self.add_ports)
        self.init_btn.clicked.connect(self.connette_serialmente)
        self.init_btn_stage.clicked.connect(self.connette_serialmente_stage)
        self.move_btn.clicked.connect(self.send_move_request)
        self.stop_btn.clicked.connect(self.send_stop_request)
        #        self.send_settings_btn.clicked.connect(self.send_settings)
        self.send_btn.clicked.connect(self.write_data)
        self.cmd_le.returnPressed.connect(self.write_data)

        self.send_btn_stage.clicked.connect(self.write_data_stage)
        self.cmd_le_stage.returnPressed.connect(self.write_data_stage)

        self.addline.connect(self.log_TE.append)
        self.execBNC_btn_changeText.connect(self.execBNC_btn.setText)
        self.update_statusbar.connect(self.statusBar().showMessage)

        self.counter.connect(self.send_btn.setText)

    def close_connection(self):
        self.ser.close()

    def redcolor(self, text):
        return '<span style=" font-size:8pt; font-weight:600; color:#ff0000;" >{}</span>'.format(
            text
        )

    def yllcolor(self, text):
        return '<span style=" font-size:8pt; font-weight:600; color:#ffff00;" >{}</span>'.format(
            text
        )

    def color(self, text, color):
        return '<span style=" font-size:8pt; font-weight:600; color:#{};" >{}</span>'.format(
            color, text
        )

    def ab(self):
        pippo = QMessageBox.about(
            self,
            "About",
            "Tool for simplifying the communication with BNCs delay generators\nThuwal\nDDCB 2019",
        )

    def connette_serialmente(self):
        self.ser = serial.Serial(
            self.port_cB.currentText(),
            baudrate=int(self.baudrate_cB.currentText()),
            timeout=0.1,
        )
        print(self.ser)
        self.statusBar().showMessage(
            "Just connected to {}...".format(self.port_cB.currentText())
        )
        # enable few othe pushbuttons
        self.move_btn.setEnabled(True)
        self.stop_btn.setEnabled(True)
        self.send_btn.setEnabled(True)
        self.execBNC_btn.setEnabled(True)
        if True:
            self.listening = True
            thread = threading.Thread(target=self.retrieve_data)
            thread.start()

    def connette_serialmente_stage(self):
        self.ser_stage = serial.Serial(
            self.port_cB_stage.currentText(),
            baudrate=int(self.baudrate_cB_stage.currentText()),
            timeout=0.1,
        )
        print(self.ser_stage)
        self.statusBar().showMessage(
            "Just connected to {}...".format(self.port_cB_stage.currentText())
        )
        # enable few othe pushbuttons
        self.send_btn_stage.setEnabled(True)
        if True:
            self.listening_stage = True
            thread3 = threading.Thread(target=self.retrieve_data_stage)
            thread3.start()

    def add_ports(self):
        for n in range(8):
            self.port_cB.removeItem(0)
            self.port_cB_stage.removeItem(0)
        for n, (port, desc, hwid) in enumerate(sorted(comports()), 1):
            self.ports.append(port)
            self.port_cB.addItem(port)
            self.port_cB_stage.addItem(port)

    def write_data(self):
        # TODO check if this works
        for line in self.cmd_le.text().split("#")[0].split("|"):
            if len(line) == 0:
                continue
            stringa = "{}\n".format(line)
            self.ser.write(stringa.encode("ascii"))
            self.addline.emit(self.color("{}".format(stringa.rstrip("\n")), "ff0000"))
            self.statusBar().showMessage(
                'Sent "{}" to BNC {}...'.format(stringa, self.port_cB.currentText())
            )

    def write_data_stage(self):
        # TODO check if this works
        for line in self.cmd_le_stage.text().split("#")[0].split("|"):
            if len(line) == 0:
                continue
            stringa = "{}\n".format(line)
            self.ser_stage.write(stringa.encode("ascii"))
            self.addline.emit(self.color("{}".format(stringa.rstrip("\n")), "cccc00"))
            self.statusBar().showMessage(
                'Sent "{}" to stage {}...'.format(stringa, self.port_cB.currentText())
            )

    def start_execution_list(self):
        # open file
        filename = self.cmdPath_lE.text()
        with open(filename, "r") as f:
            self.cmdlist = [line.rstrip("\n") for line in f]
        self.linenumber = 0
        self.dispach_instr()

    def execBNC(self):
        self.selser = 0  # reselects bnc as the first recipient of the script
        self.filename = self.cmdPath_lE.text()
        self.filename = str(self.filename).replace("file:///", "")
        if self.scriptmode_active == False:
            self.scriptmode_active = True
            self.execBNC_btn.setText("Stop executing commands form file")
            thread2 = threading.Thread(target=self.start_execution_list)
            thread2.start()
        else:
            self.scriptmode_active = False
            self.execBNC_btn.setText("Start executing commands form file")

    def start_execution_list(self):
        # open file
        if self.timeToEnd.is_set():
            return
        if self.scriptmode_active == False:
            return
        with open(self.filename, "r") as f:
            self.cmdlist = [line.rstrip("\n") for line in f]
        self.linenumber = 0
        self.dispach_instr(sendAll=True)
        # self.dispach_instr_fake(sendAll=True)

    def dispach_instr_fake(self, sendAll):
        self.addline.emit(self.yllcolor("now waiting.."))
        time.sleep(10)
        self.scriptmode_active = False
        self.addline.emit("LOG: Completed command list! Stopping now")

    def dispach_instr(self, sendAll=False):
        while len(self.cmdlist) != 0:
            if self.timeToEnd.is_set():
                return
            if self.scriptmode_active == False:
                return
            self.linenumber += 1
            # Meta command: wait a specified amount of milliseconds
            if "#WAIT" in self.cmdlist[0].split(" ")[0]:
                wtime = int(self.cmdlist.pop(0).split(" ")[-1])
                self.addline.emit(
                    self.color("Waiting for {} ms".format(wtime), "ff00ff")
                )
                time.sleep(1e-3 * wtime)
                continue
            # Meta command: select a specified serial port
            if "#SELSER" in self.cmdlist[0].split(" ")[0]:
                self.selser = int(self.cmdlist.pop(0).split(" ")[-1])
                self.addline.emit(
                    self.color("Selected serial port {}".format(self.selser), "ff00ff")
                )
                continue

            cmd, _, comment = self.cmdlist.pop(0).partition("#")
            # Meta command: print comment
            if len(comment) > 0:
                self.addline.emit(
                    self.color(
                        "{} - {}".format(self.linenumber, comment.rstrip("\n")), "000"
                    )
                )

            # Everything else is real serial commands
            for cmdi in cmd.split("|"):
                if len(cmd) < 3:
                    continue

                # here there should be the check on which serial port to send the information
                if self.selser == 0:
                    stringa = "{}\r\n".format(cmd)
                    self.ser.write(stringa.encode("ascii"))
                    self.addline.emit(
                        self.color(
                            "{} - {}".format(self.linenumber, stringa.rstrip("\n")),
                            "ff0000",
                        )
                    )
                else:
                    stringa = "{}\n".format(cmd)
                    self.ser_stage.write(stringa.encode("ascii"))
                    self.addline.emit(
                        self.color(
                            "{} - {}".format(self.linenumber, stringa.rstrip("\n")),
                            "cccc00",
                        )
                    )

                time.sleep(self.delayCmdSubmission)
            if len(self.cmdlist) == 0:
                self.scriptmode_active = False
                self.execBNC_btn_changeText.emit("Start executing commands form file")
                # self.update_statusbar.emit('Completed command list! stopping sending commands to BCN Delay Generator')
                self.addline.emit("LOG: Completed command list! Stopping now")
            if sendAll == False:
                break

    def send_move_request(self):
        self.ser.write(":INST:STATE ON\n".encode("ascii"))
        self.statusBar().showMessage("Sent BNC delay generator start command")

    def send_stop_request(self):
        self.ser.write(":INST:STATE OFF\n".encode("ascii"))
        self.statusBar().showMessage("Sent BNC delay generator Stop command")

    def retrieve_data(self):
        # print('retriving data (BNC)..')
        while self.listening == True:
            stringa = self.ser.readline()
            #            print('got: {}'.format(stringa))
            if stringa != b"" and stringa != b"\n" and stringa != b"\r\n":
                if stringa[-2:] == b"\r\n":
                    stringa = stringa[:-2]
                self.addline.emit(self.color(stringa.decode(), "00ff00"))
            if self.timeToEnd.is_set():
                break

    def retrieve_data_stage(self):
        # print('retriving data stage')
        while self.listening_stage == True:
            stringa = self.ser_stage.readline()
            #            print('got: {}'.format(stringa))
            if stringa != b"" and stringa != b"\n" and stringa != b"\r\n":
                if stringa[-2:] == b"\r\n":
                    stringa = stringa[:-2]
                self.addline.emit(self.color(stringa.decode(), "00cccc"))
            if self.timeToEnd.is_set():
                break

    def closeEvent(self, *args, **kwargs):
        super(QtWidgets.QMainWindow, self).closeEvent(*args, **kwargs)
        self.listening = False
        self.scriptmode_active = False
        self.listening_stage = False
        self.timeToEnd.set()
        print("Wait few seconds.. trying to kill few surviving threads..")


def main():
    app = QApplication(sys.argv)
    form = ExampleApp()  # We set the form to be our ExampleApp (design)
    form.show()  # Show the form
    app.exec_()  # and execute the app


if __name__ == "__main__":  # if we're running file directly and not importing it
    main()  # run the main function


"""
Interesting trick for coloring lines:
redText = "<span style=\" font-size:8pt; font-weight:600; color:#ff0000;\" >"
redText.append("I want this text red")
redText.append("</span>")
self.myTextEdit.write(redText)

"""
