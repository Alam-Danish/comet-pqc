from .cv_ramp import *
from .cv_ramp_alt import *
from .cv_ramp_vsrc import *
from .frequency_scan import *
from .iv_ramp import *
from .iv_ramp_4_wire import *
from .iv_ramp_4_wire_bias import *
from .iv_ramp_bias import *
from .iv_ramp_bias_elm import *
from .iv_ramp_bias_elm_multi_step import *
from .iv_ramp_elm import *


def measurement_factory(key: str) -> type:
    """Factory function to retrun measurement class by type name.

    >>> meas = measurement_factory("iv_ramp")()
    >>> meas.run()
    """
    for cls in globals().values():
        if hasattr(cls, "type"):
            if cls.type == key:
                return cls
    raise KeyError(f"no such measurement type: {key}")
