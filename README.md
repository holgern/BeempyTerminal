# BeempyTerminal
[![Build status](https://ci.appveyor.com/api/projects/status/7r0gp79faarapbgd?svg=true)](https://ci.appveyor.com/project/holger80/beempyterminal)
[![Build Status](https://travis-ci.org/holgern/BeempyTerminal.svg?branch=master)](https://travis-ci.org/holgern/BeempyTerminal)
A pyqt5 based desktop app for the beempy

## Setup 
Install python 3.6
Upgrade pip and install virtualenv (replace python by python3 or python.exe, depending on the installation and the system)
```
python -m pip install pip --upgrade
python -m pip install virtualenv
```

Create a virtual environment:
```
python -m virtualenv env
```

Activate the virtual environment
```
<path>\env\Scripts\activate
```

Install the packages:
```
pip install fbs PyQt5==5.12.3 PyInstaller==3.4 beem cryptography  python-dateutil
```

For windows
```
pip install pywin32
```
is necessary

## Create files

```
pyuic5 ui\mainwindow.ui -o src\main\python\ui_mainwindow.py
pyrcc5 src\main\beempyterminal.rc -o src\main\python\beempyterminal_rc.py
```

## Run the app
```
fbs run
```

## Freezing the app
```
fbs freeze
```
## Build an installer
```
fbs installer
```