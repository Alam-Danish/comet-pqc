import logging
import datetime
import random
import time
import os
import re

import comet

from ..formatter import PQCFormatter
from .matrix import MatrixMeasurement

__all__ = ["CVRampMeasurement"]

class CVRampMeasurement(MatrixMeasurement):
    """CV ramp measurement."""

    type = "cv_ramp"

    def initialize(self, smu, lcr):
        self.process.events.message("Initialize...")
        self.process.events.progress(0, 2)

        smu_idn = smu.resource.query("*IDN?")
        logging.info("Detected SMU: %s", smu_idn)
        result = re.search(r'model\s+([\d\w]+)', smu_idn, re.IGNORECASE).groups()
        smu_model = ''.join(result) or None

        self.process.events.progress(1, 2)

        lcr_idn = lcr.resource.query("*IDN?")
        logging.info("Detected LCR Meter: %s", lcr_idn)
        lcr_model = lcr_idn.split(",")[1:][0]


        self.process.events.state(dict(
            smu_model=smu_model,
            smu_voltage=smu.source.voltage.level,
            smu_current=None,
            smu_output=smu.output,
            lcr_model=lcr_model
        ))

        self.process.events.progress(2, 2)

    def measure(self, smu, lcr):
        sample_name = self.sample_name
        sample_type = self.sample_type
        output_dir = self.output_dir
        contact_name =  self.measurement_item.contact.name
        measurement_name =  self.measurement_item.name
        parameters = self.measurement_item.parameters
        current_compliance = parameters.get("current_compliance").to("A").m
        bias_voltage_start = parameters.get("bias_voltage_start").to("V").m
        bias_voltage_step = parameters.get("bias_voltage_step").to("V").m
        bias_voltage_stop = parameters.get("bias_voltage_stop").to("V").m
        waiting_time = parameters.get("waiting_time").to("s").m

        iso_timestamp = comet.make_iso()
        filename = comet.safe_filename(f"{iso_timestamp}-{sample_name}-{sample_type}-{contact_name}-{measurement_name}.txt")
        with open(os.path.join(output_dir, filename), "w", newline="") as f:
            # Create formatter
            fmt = PQCFormatter(f)
            fmt.add_column("timestamp", ".3f")
            fmt.add_column("voltage", "E")
            fmt.add_column("current", "E")
            fmt.add_column("temperature", "E")
            fmt.add_column("humidity", "E")

            # Write meta data
            fmt.write_meta("measurement_name", measurement_name)
            fmt.write_meta("measurement_type", self.type)
            fmt.write_meta("contact_name", contact_name)
            fmt.write_meta("sample_name", sample_name)
            fmt.write_meta("sample_type", sample_type)
            fmt.write_meta("start_timestamp", datetime.datetime.now(), "%Y-%m-%d %H:%M:%S")
            fmt.write_meta("bias_voltage_start", f"{bias_voltage_start:E} V")
            fmt.write_meta("bias_voltage_stop", f"{bias_voltage_stop:E} V")
            fmt.write_meta("bias_voltage_step", f"{bias_voltage_step:E} V")
            fmt.write_meta("current_compliance", f"{current_compliance:E} A")
            fmt.flush()

            # Write header
            fmt.write_header()
            fmt.flush()

    def finalize(self, smu, lcr):
        self.process.events.progress(0, 0)

        smu.output = False

        self.process.events.progress(1, 1)

    def code(self, *args, **kwargs):
        with self.devices.get("k2410") as smu:
            with self.devices.get("lcr") as lcr:
                try:
                    self.initialize(smu, lcr)
                    self.measure(smu, lcr)
                finally:
                    self.finalize(smu, lcr)
