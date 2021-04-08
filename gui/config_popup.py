from config import Ui_config_pu
from PyQt5.Qt import *


class ConfigPopup(Ui_config_pu, QWidget):
    def __init__(self):
        QWidget.__init__(self)
        self.setupUi(self)
        self.add_connects()

    def add_connects(self):
        self.comboBox.activated[str].connect(self.onChanged_m2)
        self.comboBox_2.activated[str].connect(self.onChanged_n2)
        self.comboBox_3.activated[str].connect(self.onChanged_r2)

    def update_input_fields(self, source, text):
        if source == "m2":
            if text == "Fix":
                self.lineEdit_3.setEnabled(True)
            elif text == "Auto Find":
                self.lineEdit_3.setEnabled(False)
        elif source == "n2":
            if text == "Fix":
                self.lineEdit.setEnabled(True)
            elif text == "Auto Find":
                self.lineEdit.setEnabled(False)
        elif source == "r2":
            if text == "Fix":
                self.lineEdit_2.setEnabled(True)
            elif text == "Auto Find":
                self.lineEdit_2.setEnabled(False)

    def onChanged_m2(self, text):
        self.update_input_fields("m2", text)

    def onChanged_n2(self, text):
        self.update_input_fields("n2", text)

    def onChanged_r2(self, text):
        self.update_input_fields("r2", text)
