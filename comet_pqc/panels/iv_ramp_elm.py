import logging

import comet

from ..utils import auto_unit
from .matrix import MatrixPanel

__all__ = ["IVRampElmPanel"]

class IVRampElmPanel(MatrixPanel):
    """Panel for IV ramp with electrometer measurements."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.title = "IV Ramp Elm"

        self.plot = comet.Plot(height=300, legend="right")
        self.plot.add_axis("x", align="bottom", text="Voltage [V] (abs)")
        self.plot.add_axis("y", align="right", text="Current [uA]")
        self.plot.add_series("smu", "x", "y", text="SMU", color="red")
        self.plot.add_series("elm", "x", "y", text="Electrometer", color="blue")
        self.data_tabs.insert(0, comet.Tab(title="IV Curve", layout=self.plot))

        self.voltage_start = comet.Number(decimals=3, suffix="V")
        self.voltage_stop = comet.Number(decimals=3, suffix="V")
        self.voltage_step = comet.Number(minimum=0, maximum=200, decimals=3, suffix="V")
        self.waiting_time = comet.Number(minimum=0, decimals=2, suffix="s")
        self.current_compliance = comet.Number(decimals=3, suffix="uA")
        self.sense_mode = comet.Select(values=["local", "remote"])
        self.route_termination = comet.Select(values=["front", "rear"])

        def toggle_average(enabled):
            self.average_count.enabled = enabled
            self.average_count_label.enabled = enabled
            self.average_type.enabled = enabled
            self.average_type_label.enabled = enabled

        self.average_enabled = comet.CheckBox(text="Enable", changed=toggle_average)
        self.average_count = comet.Number(minimum=0, maximum=100, decimals=0)
        self.average_count_label = comet.Label(text="Count")
        self.average_type = comet.Select(values=["repeat", "moving"])
        self.average_type_label = comet.Label(text="Type")

        self.zero_correction = comet.CheckBox(text="Zero Correction")
        self.integration_rate = comet.Number(minimum=0, maximum=100.0, decimals=2, suffix="Hz")

        self.bind("voltage_start", self.voltage_start, 0, unit="V")
        self.bind("voltage_stop", self.voltage_stop, 100, unit="V")
        self.bind("voltage_step", self.voltage_step, 1, unit="V")
        self.bind("waiting_time", self.waiting_time, 1, unit="s")
        self.bind("current_compliance", self.current_compliance, 0, unit="uA")
        self.bind("sense_mode", self.sense_mode, "local")
        self.bind("route_termination", self.route_termination, "front")
        self.bind("average_enabled", self.average_enabled, False)
        self.bind("average_count", self.average_count, 10)
        self.bind("average_type", self.average_type, "repeat")
        self.bind("zero_correction", self.zero_correction, False)
        self.bind("integration_rate", self.integration_rate, 50.0)

        # Instruments status

        self.status_smu_model = comet.Label()
        self.bind("status_smu_model", self.status_smu_model, "Model: n/a")
        self.status_smu_voltage = comet.Text(value="---", readonly=True)
        self.bind("status_smu_voltage", self.status_smu_voltage, "n/a")
        self.status_smu_current = comet.Text(value="---", readonly=True)
        self.bind("status_smu_current", self.status_smu_current, "n/a")
        self.status_smu_output = comet.Text(value="---", readonly=True)
        self.bind("status_smu_output", self.status_smu_output, "n/a")

        self.status_elm_model = comet.Label()
        self.bind("status_elm_model", self.status_elm_model, "Model: n/a")
        self.status_elm_current = comet.Text(value="---", readonly=True)
        self.bind("status_elm_current", self.status_elm_current, "n/a")

        self.status_instruments = comet.Column(
            comet.FieldSet(
                title="SMU Status",
                layout=comet.Column(
                    self.status_smu_model,
                    comet.Row(
                        comet.Column(
                            comet.Label("Voltage"),
                            self.status_smu_voltage
                        ),
                        comet.Column(
                            comet.Label("Current"),
                            self.status_smu_current
                        ),
                        comet.Column(
                            comet.Label("Output"),
                            self.status_smu_output
                        )
                    )
                )
            ),
            comet.FieldSet(
                title="Electrometer Status",
                layout=comet.Column(
                    self.status_elm_model,
                    comet.Row(
                        comet.Column(
                            comet.Label("Current"),
                            self.status_elm_current
                        ),
                        comet.Stretch(),
                        stretch=(1, 2)
                    )
                )
            ),
            comet.Stretch()
        )

        self.tabs = comet.Tabs(
            comet.Tab(
                title="General",
                layout=comet.Row(
                    comet.FieldSet(
                        title="Ramp",
                        layout=comet.Column(
                                comet.Label(text="Start"),
                                self.voltage_start,
                                comet.Label(text="Stop"),
                                self.voltage_stop,
                                comet.Label(text="Step"),
                                self.voltage_step,
                                comet.Label(text="Waiting Time"),
                                self.waiting_time,
                                comet.Stretch()
                        )
                    ),
                    comet.FieldSet(
                        title="SMU Compliance",
                        layout=comet.Column(
                            self.current_compliance,
                            comet.Stretch()
                        )
                    ),
                    comet.Stretch(),
                    stretch=(1, 1, 1)
                )
            ),
            comet.Tab(
                title="Matrix",
                layout=comet.Column(
                    self.controls.children[0],
                    comet.Stretch(),
                    stretch=(0, 1)
                )
            ),
            comet.Tab(
                title="SMU",
                layout=comet.Row(
                    comet.FieldSet(
                        title="Filter",
                        layout=comet.Column(
                            self.average_enabled,
                            self.average_count_label,
                            self.average_count,
                            self.average_type_label,
                            self.average_type,
                            comet.Stretch()
                        )
                    ),
                    comet.FieldSet(
                        title="Options",
                        layout=comet.Column(
                            comet.Label(text="Sense Mode"),
                            self.sense_mode,
                            comet.Label(text="Route Termination"),
                            self.route_termination,
                            comet.Stretch()
                        )
                    ),
                    comet.Stretch(),
                    stretch=(1, 1, 1)
                )
            ),
            comet.Tab(
                title="Electrometer",
                layout=comet.Row(
                    comet.FieldSet(
                        title="Electrometer",
                        layout=comet.Column(
                            self.zero_correction,
                            comet.Label(text="Integration Rate"),
                            self.integration_rate,
                            comet.Stretch()
                        )
                    ),
                    comet.Stretch(),
                    stretch=(1, 2)
                )
            )
        )

        self.controls.append(comet.Row(
            self.tabs,
            self.status_instruments,
            stretch=(2, 1)
        ))

    def lock(self):
        for tab in self.tabs.children:
            tab.enabled = False
        self.status_instruments.enabled = True
        self.tabs.current = 0

    def unlock(self):
        for tab in self.tabs.children:
            tab.enabled = True

    def mount(self, measurement):
        super().mount(measurement)
        for name, points in measurement.series.items():
            if name in self.plot.series:
                self.plot.series.clear()
            for x, y in points:
                voltage = x * comet.ureg('V')
                current = y * comet.ureg('A')
                self.plot.series.get(name).append(x, current.to('uA').m)
        self.update_readings()

    def state(self, state):
        if 'smu_model' in state:
            value = state.get('smu_model', "n/a")
            self.status_smu_model.text = f"Model: {value}"
        if 'smu_voltage' in state:
            value = state.get('smu_voltage')
            self.status_smu_voltage.value = auto_unit(value, "V")
        if 'smu_current' in state:
            value = state.get('smu_current')
            self.status_smu_current.value = auto_unit(value, "A")
        if 'smu_output' in state:
            labels = {False: "OFF", True: "ON", None: "---"}
            self.status_smu_output.value = labels[state.get('smu_output')]
        if 'elm_model' in state:
            value = state.get('elm_model', "n/a")
            self.status_elm_model.text = f"Model: {value}"
        if 'elm_current' in state:
            value = state.get('elm_current')
            self.status_elm_current.value = auto_unit(value, "A")
        super().state(state)

    def append_reading(self, name, x, y):
        voltage = x * comet.ureg('V')
        current = y * comet.ureg('A')
        if self.measurement:
            if name in self.plot.series:
                if name not in self.measurement.series:
                    self.measurement.series[name] = []
                self.measurement.series[name].append((x, y))
                self.plot.series.get(name).append(x, current.to('uA').m)

    def update_readings(self):
        if self.measurement:
            if self.plot.zoomed:
                self.plot.update("x")
            else:
                self.plot.fit()

    def clear_readings(self):
        super().clear_readings()
        for series in self.plot.series.values():
            series.clear()
        if self.measurement:
            for name, points in self.measurement.series.items():
                self.measurement.series[name] = []
        self.plot.fit()
