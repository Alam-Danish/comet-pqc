import contextlib
import datetime
import json
import logging
import math
import time
import uuid
from typing import Any, Dict, List

import analysis_pqc
import comet
import numpy as np
from comet.process import ProcessMixin
from comet.resource import ResourceMixin

from .. import __version__
from ..core.formatter import PQCFormatter
from ..settings import settings

__all__ = ["Measurement"]

logger = logging.getLogger(__name__)


class NumpyEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        return super().default(obj)


class ComplianceError(ValueError):
    """Compliance tripped error."""


def format_estimate(est):
    """Format estimation message without milliseconds."""
    elapsed = datetime.timedelta(seconds=round(est.elapsed.total_seconds()))
    remaining = datetime.timedelta(seconds=round(est.remaining.total_seconds()))
    average = datetime.timedelta(seconds=round(est.average.total_seconds()))
    return "Elapsed {} | Remaining {} | Average {}".format(elapsed, remaining, average)


class ParameterType:

    def __init__(self, key, default, values, unit, type, required):
        self.key = key
        self.default = default
        self.values = values
        self.unit = unit
        self.type = type
        self.required = required


class Measurement(ResourceMixin, ProcessMixin):
    """Base measurement class."""

    type: str = ""

    required_instruments: List[str] = []

    measurement_item = None # HACK

    KEY_META = "meta"
    KEY_SERIES = "series"
    KEY_SERIES_UNITS = "series_units"
    KEY_ANALYSIS = "analysis"

    FORMAT_ISO = "%Y-%m-%dT%H:%M:%S"

    def __init__(self, process, sample_name, sample_type, sample_position,
                 sample_comment, table_position, operator, tags, timestamp=None):
        self.process = process
        self.sample_name = sample_name
        self.sample_type = sample_type
        self.sample_position = sample_position
        self.sample_comment = sample_comment
        self.table_position = table_position
        self.operator = operator
        self.tags = tags
        self.registered_parameters = {}
        self.uuid = format(uuid.uuid4())
        self._timestamp = timestamp or time.time()
        self._data = {}

    @property
    def timestamp(self):
        """Returns start timestamp in seconds."""
        return self._timestamp

    @property
    def timestamp_iso(self):
        """Returns start timestamp as ISO formatted string."""
        return datetime.datetime.fromtimestamp(self.timestamp).strftime(self.FORMAT_ISO)

    @property
    def basename(self):
        """Return standardized measurement basename."""
        return "_".join(map(format, (
            self.sample_name,
            self.sample_type,
            self.measurement_item.contact.id,
            self.measurement_item.id,
            comet.make_iso(self.timestamp)
        )))

    @property
    def data(self):
        """Measurement data property."""
        return self._data

    def register_parameter(self, key, default=None, *, values=None, unit=None, type=None,
                           required=False):
        """Register measurement parameter."""
        if key in self.registered_parameters:
            raise KeyError(f"parameter already registered: {key}")
        self.registered_parameters[key] = ParameterType(
            key, default, values, unit, type, required
        )

    def validate_parameters(self):
        for key in self.measurement_item.default_parameters.keys():
            if key not in self.registered_parameters:
                logger.warning("Unknown parameter: %s", key)
        missing_keys = []
        for key, parameter in self.registered_parameters.items():
            if parameter.required:
                if key not in self.measurement_item.parameters:
                    missing_keys.append(key)
        if missing_keys:
            ValueError(f"missing required parameter(s): {missing_keys}")

    def get_parameter(self, key):
        """Get measurement parameter."""
        if key not in self.registered_parameters:
            raise KeyError(f"no such parameter: {key}")
        parameter = self.registered_parameters[key]
        if key not in self.measurement_item.parameters:
            if parameter.required:
                raise ValueError(f"missing required parameter: {key}")
        value = self.measurement_item.parameters.get(key, parameter.default)
        if parameter.unit:
            ### TODO !!!
            ### return comet.ureg(value).to(spec.unit).m
            return value.to(parameter.unit).m
        if callable(parameter.type):
            value = parameter.type(value)
        if parameter.values:
            if not value in parameter.values:
                raise ValueError(f"invalid parameter value: {value}")
        return value

    def update_state(self, items: Dict[str, Any]) -> None:
        self.process.emit("state", items)

    def update_plots(self) -> None:
        self.process.emit("update")

    def append_reading(self, name: str, x: float, y: float) -> None:
        self.process.emit("reading", name, x, y)

    def set_message(self, message: str) -> None:
        self.process.emit("message", message)

    def set_progress(self, value: int, maximum: int) -> None:
        self.process.emit("progress", value, maximum)

    def set_meta(self, key, value):
        logger.info("Meta %s: %s", key, value)
        self.data.get(self.KEY_META)[key] = value

    def set_series_unit(self, key, value):
        self.data.get(self.KEY_SERIES_UNITS)[key] = value

    def register_series(self, key):
        series = self.data.get(self.KEY_SERIES)
        if key in series:
            raise KeyError(f"Series already exists: {key}")
        series[key] = []

    def get_series(self, key):
        return self.data.get(self.KEY_SERIES).get(key, [])

    def set_analysis(self, key, value):
        self.data.get(self.KEY_ANALYSIS)[key] = value

    def append_series(self, **kwargs):
        series = self.data.get(self.KEY_SERIES)
        if sorted(series.keys()) != sorted(kwargs.keys()):
            raise KeyError("Inconsistent series keys")
        for key, value in kwargs.items():
            series.get(key).append(value)

    def serialize_json(self, fp):
        """Serialize data dictionary to JSON."""
        json.dump(self.data, fp, indent=2, cls=NumpyEncoder)

    def serialize_txt(self, fp):
        """Serialize data dictionary to plain text."""
        meta = self.data.get("meta", {})
        series_units = self.data.get("series_units", {})
        series = self.data.get("series", {})
        fmt = PQCFormatter(fp)
        # Write meta data
        for key, value in meta.items():
            if key == "measurement_tags":
                value = ", ".join([tag for tag in value if tag])
            fmt.write_meta(key, value)
        # Create columns
        columns = list(series.keys())
        for key in columns:
            fmt.add_column(key, "E", unit=series_units.get(key))
        # Write header
        fmt.write_header()
        # Write series
        if columns:
            size = len(series.get(columns[0]))
            for i in range(size):
                row = {}
                for key in columns:
                    row[key] = series.get(key)[i]
                fmt.write_row(row)
        fmt.flush()

    def wait(self, seconds, interval=1.0):
        logger.info("Waiting %s s...", seconds)
        interval = abs(interval)
        steps = math.ceil(seconds / interval)
        remaining = seconds
        self.set_message(f"Waiting {seconds} s...")
        for step in range(steps):
            self.set_progress(step + 1, steps)
            if remaining >= interval:
                time.sleep(interval)
            else:
                time.sleep(remaining)
            remaining -= interval
            if not self.process.running:
                return
        logger.info("Waiting %s s... done.", seconds)
        self.set_message("")

    def before_initialize(self, **kwargs):
        self.validate_parameters()
        self.data.clear()
        self.data[self.KEY_META] = {}
        self.data[self.KEY_SERIES_UNITS] = {}
        self.data[self.KEY_SERIES] = {}
        self.data[self.KEY_ANALYSIS] = {}
        self.set_meta("uuid", self.uuid)
        self.set_meta("sample_name", self.sample_name)
        self.set_meta("sample_type", self.sample_type)
        self.set_meta("sample_position", self.sample_position)
        self.set_meta("sample_comment", self.sample_comment)
        self.set_meta("contact_name", self.measurement_item.contact.name)
        self.set_meta("measurement_name", self.measurement_item.name)
        self.set_meta("measurement_type", self.type)
        self.set_meta("measurement_tags", self.tags)
        self.set_meta("table_position", tuple(self.table_position))
        self.set_meta("start_timestamp", self.timestamp_iso)
        self.set_meta("operator", self.operator)
        self.set_meta("pqc_version", __version__)
        self.set_meta("analysis_pqc_version", analysis_pqc.__version__)

    def initialize(self, **kwargs):
        ...

    def after_initialize(self, **kwargs):
        ...

    def measure(self, **kwargs):
        ...

    def before_finalize(self, **kwargs):
        ...

    def finalize(self, **kwargs):
        ...

    def after_finalize(self, **kwargs):
        ...

    def analyze(self, **kwargs):
        ...


class MeasurementRunner:

    def __init__(self, measurement) -> None:
        self.measurement = measurement

    def handle_state(self, name, methods):
        def handle_state(kwargs):
            logger.info("%s %s...", name, self.measurement.type)
            try:
                for method in methods:
                    getattr(self.measurement, method)(**kwargs)
            except Exception as exc:
                logger.exception(exc)
                logger.error("%s %s... failed.", name, self.measurement.type)
                raise
            else:
                logger.info("%s %s... done.", name, self.measurement.type)
        return handle_state

    def initialize(self, kwargs):
        self.handle_state("Initialize", [
            "before_initialize",
            "initialize",
            "after_initialize",
        ])(kwargs)

    def measure(self, kwargs):
        self.handle_state("Measure", [
            "measure",
        ])(kwargs)

    def finalize(self, kwargs):
        self.handle_state("Finalize", [
            "before_finalize",
            "finalize",
            "after_finalize",  # is not executed on error
        ])(kwargs)

    def analyze(self, kwargs):
        self.handle_state("Analyze", [
            "analyze",
        ])(kwargs)

    def __call__(self):
        """Run measurement.

        If initialize, measure or analyze fails, finalize is executed before
        raising any exception.
        """
        measurement = self.measurement
        with contextlib.ExitStack() as es:
            kwargs = {}
            for key in type(measurement).required_instruments:
                create = settings.getInstrumentType(key)
                resource = measurement.resources.get(key)
                kwargs.update({key: create(es.enter_context(resource))})
            try:
                self.initialize(kwargs)
                self.measure(kwargs)
            finally:
                try:
                    self.finalize(kwargs)
                finally:
                    self.analyze(kwargs)
