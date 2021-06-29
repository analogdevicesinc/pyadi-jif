# import os,sys,inspect
# current_dir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
# parent_dir = os.path.dirname(current_dir)
# sys.path.insert(0, parent_dir)

from config_popup import ConfigPopup
from main import Ui_MainGUI
from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.Qt import *

# import adijif


def test_config():
    vcxo = 125000000

    sys = adijif.system("ad9680", "hmc7044", "xilinx", vcxo)

    # Get Converter clocking requirements
    sys.converter.sample_clock = 1e9
    sys.converter.datapath_decimation = 1
    sys.converter.L = 4
    sys.converter.M = 2
    sys.converter.N = 14
    sys.converter.Np = 16
    sys.converter.K = 32
    sys.converter.F = 1
    sys.Debug_Solver = False

    # Get FPGA clocking requirements
    sys.fpga.setup_by_dev_kit_name("zc706")
    sys.fpga.force_qpll = 1

    try:
        sys.solve()
    except:
        return False
    lr = sys.converter.bit_clock
    vcxo = sys.clock.vcxo
    return sys.clock.get_config(), lr, vcxo


class PyADIGUI(Ui_MainGUI):
    def add_row(self, c, lr, vcxo, row):
        _translate = QtCore.QCoreApplication.translate
        # LANE, VCXO, CNV REF, CNV SYS, FPGA REF, FPGA, SYS
        c = c["output_clocks"]

        values = [
            lr,
            vcxo,
            c["ad9680_adc_clock"]["rate"],
            c["ad9680_sysref"]["rate"],
            c["fpga_ref"]["rate"],
            c["ad9680_sysref"]["rate"],
        ]
        for i, val in enumerate(values):
            print(i)
            item = QtWidgets.QTableWidgetItem()
            self.tw_output.setItem(row, i, item)
            item = self.tw_output.item(row, i)
            item.setText(_translate("MyGUI", str(val)))

    def search(self):
        o, lr, vcxo = test_config()
        self.add_row(o, lr, vcxo, 0)
        self.tw_output.setRowCount(2)
        self.add_row(o, lr, vcxo, 1)

    def launch_config_panel(self):
        self.w = ConfigPopup()
        self.w.show()

    def add_connects(self):
        self.b_search.clicked.connect(self.search)
        self.pushButton_4.clicked.connect(self.launch_config_panel)


if __name__ == "__main__":
    import sys

    app = QtWidgets.QApplication(sys.argv)
    MyGUI = QtWidgets.QMainWindow()
    ui = PyADIGUI()
    ui.setupUi(MyGUI)
    ui.add_connects()
    MyGUI.show()
    sys.exit(app.exec_())
