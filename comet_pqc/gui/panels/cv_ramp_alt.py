from typing import Optional

from comet import ureg
from PyQt5 import QtCore, QtWidgets
from QCharted import Chart, ChartView

from .matrix import MatrixPanel
from .mixins import EnvironmentMixin, LCRMixin

__all__ = ["CVRampAltPanel"]


class CVRampAltPanel(MatrixPanel, LCRMixin, EnvironmentMixin):
    """Panel for CV ramp (alternate) measurements."""

    type_name = "cv_ramp_alt"

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)
        self.setTitle("CV Ramp (LCR)")

        self.register_lcr()
        self.register_environment()

        self.chart = Chart()
        self.chart.legend().setAlignment(QtCore.Qt.AlignRight)

        self.xAxis = self.chart.addValueAxis(QtCore.Qt.AlignBottom)
        self.xAxis.setTitleText("Voltage [V] (abs)")

        self.yAxis = self.chart.addValueAxis(QtCore.Qt.AlignRight)
        self.yAxis.setTitleText("Capacitance [pF]")

        self.lcrSeries = self.chart.addLineSeries(self.xAxis, self.yAxis)
        self.lcrSeries.setName("LCR Cp")
        self.lcrSeries.setPen(QtCore.Qt.blue)
        self.series["lcr"] = self.lcrSeries

        self.chartView = ChartView(self)
        self.chartView.setChart(self.chart)
        self.chartView.setMaximumHeight(300)

        self.dataTabWidget.insertTab(0, self.chartView, "CV Curve")

        self.chart2 = Chart()
        self.chart2.legend().setAlignment(QtCore.Qt.AlignRight)

        self.xAxis2 = self.chart2.addValueAxis(QtCore.Qt.AlignBottom)
        self.xAxis2.setTitleText("Voltage [V] (abs)")

        self.yAxis2 = self.chart2.addValueAxis(QtCore.Qt.AlignRight)
        self.yAxis2.setTitleText("1/Capacitance² [1/F²]")
        self.yAxis2.setLabelFormat("%G")

        self.lcr2Series = self.chart2.addLineSeries(self.xAxis2, self.yAxis2)
        self.lcr2Series.setName("LCR Cp")
        self.lcr2Series.setPen(QtCore.Qt.blue)
        self.series["lcr2"] = self.lcr2Series

        self.chartView2 = ChartView(self)
        self.chartView2.setChart(self.chart2)
        self.chartView2.setMaximumHeight(300)

        self.dataTabWidget.insertTab(1, self.chartView2, "1/C² Curve")

        self.voltage_start: QtWidgets.QDoubleSpinBox = QtWidgets.QDoubleSpinBox(self)
        self.voltage_start.setRange(-2.1e3, 2.1e3)
        self.voltage_start.setDecimals(3)
        self.voltage_start.setSuffix(" V")

        self.voltage_stop: QtWidgets.QDoubleSpinBox = QtWidgets.QDoubleSpinBox(self)
        self.voltage_stop.setRange(-2.1e3, 2.1e3)
        self.voltage_stop.setDecimals(3)
        self.voltage_stop.setSuffix(" V")

        self.voltage_step: QtWidgets.QDoubleSpinBox = QtWidgets.QDoubleSpinBox(self)
        self.voltage_step.setRange(0, 2.1e2)
        self.voltage_step.setDecimals(3)
        self.voltage_step.setSuffix(" V")

        self.waiting_time: QtWidgets.QDoubleSpinBox = QtWidgets.QDoubleSpinBox(self)
        self.waiting_time.setRange(0, 60)
        self.waiting_time.setDecimals(2)
        self.waiting_time.setSuffix(" s")

        self.lcr_frequency: QtWidgets.QDoubleSpinBox = QtWidgets.QDoubleSpinBox(self)
        self.lcr_frequency.setDecimals(3)
        self.lcr_frequency.setRange(0.020, 20e3)
        self.lcr_frequency.setValue(1)
        self.lcr_frequency.setSuffix(" kHz")

        self.lcr_amplitude: QtWidgets.QDoubleSpinBox = QtWidgets.QDoubleSpinBox(self)
        self.lcr_amplitude.setDecimals(3)
        self.lcr_amplitude.setRange(0, 2.1e6)
        self.lcr_amplitude.setSuffix(" mV")

        self.bind("bias_voltage_start", self.voltage_start, 0, unit="V")
        self.bind("bias_voltage_stop", self.voltage_stop, 0, unit="V")
        self.bind("bias_voltage_step", self.voltage_step, 0, unit="V")
        self.bind("waiting_time", self.waiting_time, 1, unit="s")
        self.bind("lcr_frequency", self.lcr_frequency, 1, unit="kHz")
        self.bind("lcr_amplitude", self.lcr_amplitude, 0, unit="mV")

        lcrRampGroupBox: QtWidgets.QGroupBox = QtWidgets.QGroupBox(self)
        lcrRampGroupBox.setTitle("LCR Ramp")

        lcrRampGroupBoxLayout: QtWidgets.QVBoxLayout = QtWidgets.QVBoxLayout(lcrRampGroupBox)
        lcrRampGroupBoxLayout.addWidget(QtWidgets.QLabel("Start", self))
        lcrRampGroupBoxLayout.addWidget(self.voltage_start)
        lcrRampGroupBoxLayout.addWidget(QtWidgets.QLabel("Stop", self))
        lcrRampGroupBoxLayout.addWidget(self.voltage_stop)
        lcrRampGroupBoxLayout.addWidget(QtWidgets.QLabel("Step", self))
        lcrRampGroupBoxLayout.addWidget(self.voltage_step)
        lcrRampGroupBoxLayout.addWidget(QtWidgets.QLabel("Waiting Time", self))
        lcrRampGroupBoxLayout.addWidget(self.waiting_time)
        lcrRampGroupBoxLayout.addStretch()

        frequencyGroupBox: QtWidgets.QGroupBox = QtWidgets.QGroupBox(self)
        frequencyGroupBox.setTitle("LCR")

        frequencyGroupBoxLayout: QtWidgets.QVBoxLayout = QtWidgets.QVBoxLayout(frequencyGroupBox)
        frequencyGroupBoxLayout.addWidget(QtWidgets.QLabel("AC Frequency", self))
        frequencyGroupBoxLayout.addWidget(self.lcr_frequency)
        frequencyGroupBoxLayout.addWidget(QtWidgets.QLabel("AC Amplitude", self))
        frequencyGroupBoxLayout.addWidget(self.lcr_amplitude)
        frequencyGroupBoxLayout.addStretch()

        self.generalWidgetLayout.addWidget(lcrRampGroupBox, 1)
        self.generalWidgetLayout.addWidget(frequencyGroupBox, 1)
        self.generalWidgetLayout.addStretch(1)

        fahrad = ureg("F")
        volt = ureg("V")

        self.series_transform["lcr"] = lambda x, y: ((x * volt).to("V").m, (y * fahrad).to("pF").m)

    def mount(self, measurement):
        super().mount(measurement)
        for series in self.series.values():
            series.data().clear()
        for name, points in measurement.series.items():
            series = self.series.get(name)
            if series is not None:
                tr = self.series_transform.get(name, self.series_transform_default)
                for x, y in points:
                    series.data().append(*tr(x, y))
        self.chart.fit()
        self.chart2.fit()

    def append_reading(self, name, x, y):
        if self.measurement:
            series = self.series.get(name)
            if series is not None:
                tr = self.series_transform.get(name, self.series_transform_default)
                if name not in self.measurement.series:
                    self.measurement.series[name] = []
                self.measurement.series[name].append((x, y))
                series.data().append(*tr(x, y))
                if name == "lcr":
                    if self.chart.isZoomed():
                        self.chart.updateAxis(self.xAxis, self.xAxis.min(), self.xAxis.max())
                    else:
                        self.chart2.fit()
                elif name == "lcr2":
                    if self.chart2.isZoomed():
                        self.chart2.updateAxis(self.xAxis2, self.xAxis2.min(), self.xAxis2.max())
                    else:
                        self.chart2.fit()

    def clearReadings(self):
        super().clearReadings()
        for series in self.series.values():
            series.data().clear()
        if self.measurement:
            for name, points in self.measurement.series.items():
                self.measurement.series[name] = []
        self.chart.fit()
        self.chart2.fit()
