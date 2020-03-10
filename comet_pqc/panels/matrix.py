import comet
from .panel import Panel

__all__ = ["MatrixPanel"]

def encode_matrix(values):
    return ", ".join(map(format, values))

def decode_matrix(value):
    return list(map(str.strip, value.split(",")))

class MatrixChannelsText(comet.Text):
    """Overloaded text input to handle matrix channel list."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    @property
    def value(self):
        return decode_matrix(self.qt.text())

    @value.setter
    def value(self, value):
        self.qt.setText(encode_matrix(value or []))

class MatrixPanel(Panel):
    """Base class for matrix switching panels."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.matrix_enabled = comet.CheckBox(text="Enable Switching")
        self.matrix_channels = MatrixChannelsText(
            tooltip="Matrix card switching channels, comma separated list."
        )

        self.controls.append(comet.FieldSet(
            title="Matrix",
            layout=comet.Column(
                self.matrix_enabled,
                comet.Label(text="Channels"),
                comet.Row(
                    self.matrix_channels,
                    comet.Button(text="Load from Matrix", enabled=False)
                )
            )
        ))

        self.bind("matrix_enabled", self.matrix_enabled, False)
        self.bind("matrix_channels", self.matrix_channels, [])
