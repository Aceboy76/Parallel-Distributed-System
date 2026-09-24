from cma_flow_gui import CMAFlowApp
from PyQt6.QtWidgets import QApplication
import sys
if __name__=='__main__':
    app=QApplication(sys.argv); w=CMAFlowApp(); w.show(); sys.exit(app.exec())
