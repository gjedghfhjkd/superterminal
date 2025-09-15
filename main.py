import sys
from PyQt5.QtWidgets import QApplication
from mobaxterm.ui.main_window import MobaXtermClone

def main():
    app = QApplication(sys.argv)
    
    # Set dark theme
    app.setStyle('Fusion')
    
    window = MobaXtermClone()
    window.show()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()