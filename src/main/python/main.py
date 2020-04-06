from fbs_runtime.application_context.PyQt5 import ApplicationContext, cached_property
import sys
from builtins import print
import os
import getpass
import socket
from pathlib import Path
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QPushButton, QPlainTextEdit, QDesktopWidget, QMainWindow, QDialog, QGridLayout, QLabel
from PyQt5.QtGui import QSyntaxHighlighter, QTextCharFormat, QColor, QFont, QTextCursor
from PyQt5.QtCore import Qt, pyqtSignal, QRegExp, QProcess, QThread, QCoreApplication, QSettings, QPoint, QSize
from ui_mainwindow import Ui_MainWindow
import logging
import fix_qt_import_error
from beem.cli import cli
from click.testing import CliRunner
log = logging.getLogger(__name__)
logging.basicConfig(level=logging.ERROR)

ORGANIZATION_NAME = 'holger80'
ORGANIZATION_DOMAIN = 'beempy.com'
APPLICATION_NAME = 'BeempyTerminal'
SETTINGS_TRAY = 'settings/tray'


class AppContext(ApplicationContext):
    def run(self):
        stylesheet = self.get_resource('styles.qss')
        self.app.setStyleSheet(open(stylesheet).read())
        self.window.show()
        return self.app.exec_()
    @cached_property
    def window(self):
        return MainWindow()


class MainWindow(QMainWindow, Ui_MainWindow):
    def __init__(self):
        super(QMainWindow, self).__init__()
        # Set up the user interface from Designer.
        self.setupUi(self)
        self.widget.add()
        self.actionAbout.triggered.connect(self.about)
        self.settings = QSettings(ORGANIZATION_NAME, APPLICATION_NAME)
        self.readSettings()

    def readSettings(self):
        if self.settings.contains("commands"):
            self.widget.commandslist = self.settings.value("commands")
        if self.settings.contains("pos"):
            pos = self.settings.value("pos", QPoint(200, 200))
            self.move(pos)
        if self.settings.contains("size"):
            size = self.settings.value("size", QSize(400, 400))
            self.resize(size)

    def writeSettings(self):
        self.settings.setValue("commands", self.widget.commandslist)
        self.settings.setValue("pos", self.pos())
        self.settings.setValue("size", self.size())

    def closeEvent(self, e):
        self.writeSettings()

    def about(self):
        self.dialog = QDialog()
        self.dialog.setWindowTitle("About Dialog")
        gridlayout = QGridLayout()
        
        text = QLabel()
        text.setWordWrap(True)
        text.setText("Welcome to Beempy Terminal! This is the first release for testing qt5. Please vote for holger80 as witness, if you like this :).")
        layout = QVBoxLayout()
        layout.addWidget(text)

        gridlayout.addLayout(layout, 0, 0)
        self.dialog.setLayout(gridlayout)    
        self.dialog.show()


class PlainTextEdit(QPlainTextEdit):
    commandSignal = pyqtSignal(str)
    commandZPressed = pyqtSignal(str)

    def __init__(self, parent=None, movable=False):
        super().__init__(parent)

        self.name = ">$ beempy "
        self.appendPlainText(self.name)
        self.movable = movable
        self.parent = parent
        self.text = None
        self.document_file = self.document()
        self.previousCommandLength = 0
        self.document_file.setDocumentMargin(-1)

    def center(self):
        qr = self.frameGeometry()
        cp = QDesktopWidget().availableGeometry().center()
        qr.moveCenter(cp)
        self.move(qr.topLeft())

    def mousePressEvent(self, event):
        if self.movable is True:
            self.parent.mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self.movable is True:
            self.parent.mouseMoveEvent(event)

    def textUnderCursor(self):
        textCursor = self.textCursor()
        textCursor.select(QTextCursor.WordUnderCursor)

        return textCursor.selectedText()

    def keyPressEvent(self, e):
        cursor = self.textCursor()

        if self.parent:

            if e.modifiers() == Qt.ControlModifier and e.key() == Qt.Key_A:
                return

            if e.modifiers() == Qt.ControlModifier and e.key() == Qt.Key_Z:
                self.commandZPressed.emit("True")
                return

            if e.key() == 16777220:  # This is the ENTER key
                text = self.textCursor().block().text()
                # text = "beempy " + text.replace(self.name, "")
                if text == self.name + text.replace(self.name, "") and text.replace(self.name, "") != "":  # This is to prevent adding in commands that were not meant to be added in
                    self.parent.commandslist.append(text.replace(self.name, ""))
                self.commandSignal.emit(text)
                # self.appendPlainText(self.name)

                return

            if e.key() == Qt.Key_Up:
                try:
                    if self.parent.tracker != 0:
                        cursor.select(QTextCursor.BlockUnderCursor)
                        cursor.removeSelectedText()
                        self.appendPlainText(self.name)

                    self.insertPlainText(self.parent.commandslist[self.parent.tracker])
                    self.parent.tracker += 1

                except IndexError:
                    self.parent.tracker = 0

                return

            if e.key() == Qt.Key_Down:
                try:
                    cursor.select(QTextCursor.BlockUnderCursor)
                    cursor.removeSelectedText()
                    self.appendPlainText(self.name)

                    self.insertPlainText(self.parent.commandslist[self.parent.tracker])
                    self.parent.tracker -= 1

                except IndexError:
                    self.parent.tracker = 0

            if e.key() == 16777219:
                if cursor.positionInBlock() <= len(self.name):
                    return

                else:
                    cursor.deleteChar()

            super().keyPressEvent(e)

        e.accept()


class Terminal(QWidget):
    errorSignal = pyqtSignal(str)
    outputSignal = pyqtSignal(str)

    def __init__(self, parent, movable=False):
        super().__init__()

        self.setWindowFlags(
            Qt.Widget |
            Qt.WindowCloseButtonHint |
            Qt.WindowStaysOnTopHint |
            Qt.FramelessWindowHint
        )
        self.movable = movable
        self.layout = QVBoxLayout()
        self.pressed = False
        self.parent = parent
        self.name = ">$ beempy "
        self.commandslist = []  # This is a list to track what commands the user has used so we could display them when
        # up arrow key is pressed
        self.tracker = 0
        self.runner = CliRunner()
        self.setLayout(self.layout)
        self.setStyleSheet("QWidget {background-color:invisible;}")

        # self.showMaximized() # comment this if you want to embed this widget

    def ispressed(self):
        return self.pressed

    def center(self):
        qr = self.frameGeometry()
        cp = QDesktopWidget().availableGeometry().center()
        qr.moveCenter(cp)
        self.move(qr.topLeft())

    def add(self):
        self.added()
        self.commandfield = PlainTextEdit(self, self.movable)
        self.highlighter = name_highlighter(self.commandfield.document(), str(getpass.getuser()), str(socket.gethostname()),
                                            str(os.getcwd()))
        self.layout.addWidget(self.commandfield)
        self.commandfield.commandSignal.connect(self.handle)
        self.commandfield.commandZPressed.connect(self.handle)

    def added(self):
        self.pressed = True

    def remove(self):
        self.commandfield.deleteLater()
        self.parent.hideConsole()
        self.pressed = False

    def run(self, command):
        """Executes a system command."""
        #if self.process.state() != 2:
        #    self.process.start("beempy " + command)
        commandlist = command.split(' ')
        if commandlist == ['']:
            commandlist = ['--help']
        result = self.runner.invoke(cli, commandlist)
        out = result.output
        self.commandfield.appendPlainText(out)
        self.name = ">$ beempy "
        self.commandfield.appendPlainText(self.name) 

    def isFinished(self):
        print("finished")
        self.name = ">$ beempy "
        self.commandfield.appendPlainText(self.name)
        # self.commandfield.setPlainText(self.name)
        # self.cursorEnd()

    def cursorEnd(self):
        self.name = ">$ beempy "
        self.commandfield.setPlainText(self.name)
        cursor = self.commandfield.textCursor()
        cursor.movePosition(11, 0)
        self.commandfield.setTextCursor(cursor)
        self.commandfield.setFocus()

    def handle(self, command):

        """Split a command into list so command echo hi would appear as ['echo', 'hi']"""
        real_command = command.replace(self.commandfield.name, "")

        if real_command.startswith("python"):
            pass

        if real_command != "":
            command_list = real_command.split()
        else:
            command_list = None
        """Now we start implementing some commands"""
        if real_command == "clear":
            self.commandfield.clear()

        elif command_list is not None and command_list[0] == "echo":
            self.commandfield.appendPlainText(" ".join(command_list[1:]))

        elif real_command == "exit":
            self.remove()

        elif command == self.commandfield.name + real_command:
            self.run(real_command)

        else:
            pass
    # When the user does a command like ls and then presses enter then it wont read the line where the cursor is on as a command


class name_highlighter(QSyntaxHighlighter):

    def __init__(self, parent=None, user_name=None, host_name=None, cwd=None):
        super().__init__(parent)
        self.highlightingRules = []
        self.name = user_name
        self.name2 = host_name
        self.cwd = cwd
        most_used = ["addkey", "addtoken", "allow", "approvewitness", "balance", "beneficiaries", "broadcast", "buy",
                     "cancel", "changerecovery", "changewalletpassphrase", "claimaccount", "claimreward",
					 "config", "convert", "createwallet", "curation", "currentnode", "customjson",
                     "delegate", "delete", "delkey", "delprofile", "deltoken", "disallow",
                     "disapprovewitness", "downvote", "featureflags", "follow", "follower", "following", "importaccount",
					 "info", "interest", "keygen", "listaccounts", "listkeys", "listtoken",
                     "mute", "muter", "muting", "newaccount", "nextnode", "notifications",
                     "openorders", "orderbook", "parsewif", "pending", "permissions", "pingnode", "exit",
                     "post", "power", "powerdown", "powerdownroute", "powerup", "pricehistory", "reply", "resteem", "rewards",
                     "sell", "set", "setprofile", "sign", "ticker", "tradehistory", "transfer", "unfollow", "updatememokey",
                     "updatenodes", "uploadimage", "upvote", "userdata", "verify", "votes", "walletinfo", "witness",
                     "witnesscreate", "witnessdisable", "witnessenable", "witnesses", "witnessfeed", "witnessupdate", "witnessproperties"
                     ]  # most used linux commands, so we will highlight them!
        self.regex = {
            "class": "\\bclass\\b",
            "function": "[A-Za-z0-9_]+(?=\\()",
            "magic": "\\__[^']*\\__",
            "decorator": "@[^\n]*",
            "singleLineComment": "#[^\n]*",
            "quotation": "\"[^\"]*\"",
            "quotation2": "'[^\']*\'",
            "multiLineComment": "[-+]?[0-9]+",
            "int": "[-+]?[0-9]+",
        }
        """compgen -c returns all commands that you can run"""

        for f in most_used:
            nameFormat = QTextCharFormat()
            nameFormat.setForeground(QColor("#00ff00"))
            # nameFormat.setFontItalic(True)
            self.highlightingRules.append((QRegExp("\\b" + f + "\\b"), nameFormat))

        hostnameFormat = QTextCharFormat()
        hostnameFormat.setForeground(QColor("#12c2e9"))
        self.highlightingRules.append((QRegExp(self.name), hostnameFormat))
        self.highlightingRules.append((QRegExp(self.name2), hostnameFormat))

        otherFormat = QTextCharFormat()
        otherFormat.setForeground(QColor("#f7797d"))
        self.highlightingRules.append((QRegExp("~\/[^\s]*"), otherFormat))

        quotation1Format = QTextCharFormat()
        quotation1Format.setForeground(QColor("#96c93d"))
        self.highlightingRules.append((QRegExp("\"[^\"]*\""), quotation1Format))

        quotation2Format = QTextCharFormat()
        quotation2Format.setForeground(QColor("#96c93d"))
        self.highlightingRules.append((QRegExp("'[^\']*\'"), quotation2Format))

        integerFormat = QTextCharFormat()
        integerFormat.setForeground(QColor("#cc5333"))
        # integerFormat.setFontItalic(True)
        self.highlightingRules.append((QRegExp("\\b[-+]?[0-9]+\\b"), integerFormat))

    def highlightBlock(self, text):

        for pattern, format in self.highlightingRules:
            expression = QRegExp(pattern)
            index = expression.indexIn(text)
            while index >= 0:
                length = expression.matchedLength()
                self.setFormat(index, length, format)
                index = expression.indexIn(text, index + length)


class PythonThread(QThread):

    def __init__(self):
        super().__init__()



if __name__ == '__main__':
    # To ensure that every time you call QSettings not enter the data of your application, 
    # which will be the settings, you can set them globally for all applications
    QCoreApplication.setApplicationName(ORGANIZATION_NAME)
    QCoreApplication.setOrganizationDomain(ORGANIZATION_DOMAIN)
    QCoreApplication.setApplicationName(APPLICATION_NAME)    
    
    appctxt = AppContext()
    exit_code = appctxt.run()
    sys.exit(exit_code)