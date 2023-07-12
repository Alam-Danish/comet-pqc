from typing import Optional

from PyQt5 import QtCore, QtWidgets

from .processes import WebAPIProcess

__all__ = ["WebAPIPlugin"]


class WebAPIPlugin:

    def __init__(self, window) -> None:
        self.window = window
        self.process = WebAPIProcess(
            failed=self.window.show_exception
        )
        self.window.processes.add("webapi", self.process)

    def install(self) -> None:
        self.preferencesWidget = WebAPIPreferencesWidget()
        self.window.preferences_dialog.tab_widget.qt.addTab(self.preferencesWidget, "WebAPI")
        self.process.start()

    def uninstall(self) -> None:
        self.process.stop()
        index = self.window.preferences_dialog.tab_widget.qt.indexOf(self.preferencesWidget)
        self.window.preferences_dialog.tab_widget.qt.removeTab(index)
        self.preferencesWidget.deleteLater()


class WebAPIPreferencesWidget(QtWidgets.QWidget):

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)

        self.isServerEnabledCheckBox = QtWidgets.QCheckBox(self)
        self.isServerEnabledCheckBox.setText("Enabled")

        self.hostLineEdit = QtWidgets.QLineEdit(self)

        self.portSpinBox = QtWidgets.QSpinBox(self)
        self.portSpinBox.setRange(0, 99999)

        self.groupBox = QtWidgets.QGroupBox(self)
        self.groupBox.setTitle("Server")

        groupBoxLayout = QtWidgets.QFormLayout(self.groupBox)
        groupBoxLayout.addWidget(self.isServerEnabledCheckBox)
        groupBoxLayout.addRow("Host", self.hostLineEdit)
        groupBoxLayout.addRow("port", self.portSpinBox)

        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(self.groupBox)
        layout.addStretch(1)

    def reflection(self):  # TODO
        return self

    def isServerEnabled(self) -> bool:
        return self.isServerEnabledCheckBox.isChecked()

    def setServerEnabled(self, enabled: bool) -> None:
        self.isServerEnabledCheckBox.setChecked(enabled)

    def hostname(self) -> str:
        return self.hostLineEdit.text().strip()

    def setHostname(self, hostname: str) -> None:
        self.hostLineEdit.setText(hostname)

    def port(self) -> int:
        return self.portSpinBox.value()

    def setPort(self, port: int) -> None:
        self.portSpinBox.setValue(port)

    def load(self) -> None:
        settings = QtCore.QSettings()
        settings.beginGroup("plugin.webapi")
        enabled = settings.value("enabled", False, bool)
        hostname = settings.value("hostname", "0.0.0.0", str)
        port = settings.value("port", 9000, int)
        settings.endGroup()
        self.setServerEnabled(enabled)
        self.setHostname(hostname)
        self.setPort(port)

    def store(self) -> None:
        settings = QtCore.QSettings()
        settings.beginGroup("plugin.webapi")
        settings.setValue("enabled", self.isServerEnabled())
        settings.setValue("hostname", self.hostname())
        settings.setValue("port", self.port())
        settings.endGroup()
