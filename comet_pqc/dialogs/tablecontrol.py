import logging

import comet
from comet import ui
from qutie.qt import QtCore

__all__ = ['TableControlDialog']

class TableControlDialog(ui.Dialog, comet.ProcessMixin):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.title="Table Control"
        self.control = TableControl()
        self.layout=ui.Column(
            self.control,
            ui.Row(
                ui.Button("&Close", clicked=self.close),
                ui.Spacer(vertical=False)
            ),
        )
        self.process = self.processes.get('control')
        def on_failed(*args):
            ui.show_exception(*args)
            self.close()
        self.process.failed = on_failed
        def on_close():
             self.close()
        self.process.finished = on_close
        def on_move(x, y, z):
            logging.info(f"Move table: {x} {y} {z}")
            self.process.push(x, y, z)
        def on_position(x, y, z):
            self.control.position = x, y, z
            # Fetch laser sensor state
            laser_state = "n/a"
            laser_style = ""
            try:
                with self.processes.get("environment") as environ:
                    pc_data = environ.pc_data()
                    laser_sensor = pc_data.relay_states.laser_sensor
                    laser_state = {False: "OFF", True: "ON"}.get(laser_sensor, "n/a")
                    laser_style = {False: "QLabel{color:red;font-weight:bold}", True: "QLabel{color:green;font-weight:bold}"}.get(laser_sensor, "")
            except Exception as e:
                logging.error(e)
            self.control.laser_state_label.text = laser_state
            self.control.laser_state_label.stylesheet = laser_style
        def on_caldone(x, y, z):
            self.control.caldone = x, y, z
        self.process.position = on_position
        self.process.caldone = on_caldone
        self.control.move = on_move

    def run(self):
        self.process.start()
        super().run()
        self.process.stop()
        self.process.join()

class SquareSpacer(ui.Spacer):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.width = 32
        self.height = 32

class SquareButton(ui.Button):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.width = 32
        self.height = 32

class SquareLabel(ui.Label):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.width = 32
        self.height = 32
        self.qt.setAlignment(QtCore.Qt.AlignCenter)

class TableControl(ui.Column):

    movement_widths = (
        (1.0, "fine", "green"),
        (10.0, "wide", "orange"),
        (100.0, "large", "red")
    )

    def __init__(self, *args, move=None, **kwargs):
        super().__init__(*args, **kwargs)
        # Event
        self.move = move
        # Control buttons
        self.back_button = SquareButton(
            text="⊳",
            tool_tip="Move table to back.",
            clicked=self.on_back
        )
        self.front_button = SquareButton(
            text="⊲",
            tool_tip="Move table to front.",
            clicked=self.on_front
        )
        self.left_button = SquareButton(
            "∆",
            tool_tip="Move table left.",
            clicked=self.on_left
        )
        self.right_button = SquareButton(
            "∇",
            tool_tip="Move table right.",
            clicked=self.on_right
        )
        self.up_button = SquareButton(
            "∆",
            tool_tip="Move table up.",
            clicked=self.on_up
        )
        self.down_button = SquareButton(
            "∇",
            tool_tip="Move table down.",
            clicked=self.on_down
        )
        self.control_buttons = (
            self.front_button,
            self.back_button,
            self.left_button,
            self.right_button,
            self.up_button,
            self.down_button
        )
        # Create movement radio buttons
        self.movement_buttons = ui.Column()
        for width, name, color in self.movement_widths:
            button = ui.RadioButton(
                text=f"{name.title()} ({width} μm)",
                tool_tip=f"Move in {name} steps.",
                stylesheet=f"QRadioButton{{color:{color};}}",
                toggled=self.on_colorcode
            )
            button.movement_width = width
            button.movement_name = name
            button.movement_color = color
            self.movement_buttons.append(button)
        self.pos_x_label = ui.Label()
        self.pos_y_label = ui.Label()
        self.pos_z_label = ui.Label()
        self.cal_x_label = ui.Label()
        self.cal_y_label = ui.Label()
        self.cal_z_label = ui.Label()
        self.rm_x_label = ui.Label()
        self.rm_y_label = ui.Label()
        self.rm_z_label = ui.Label()
        self.laser_state_label = ui.Label("n/a")
        # Layout
        self.controls_layout = ui.Column(
            ui.Spacer(),
            ui.Row(
                ui.Spacer(),
                ui.Row(
                    ui.Column(
                        SquareSpacer(),
                        self.front_button,
                        SquareSpacer()
                    ),
                    ui.Column(
                        self.left_button,
                        SquareLabel("X/Y"),
                        self.right_button
                    ),
                    ui.Column(
                        SquareSpacer(),
                        self.back_button,
                        SquareSpacer()
                    )
                ),
                SquareSpacer(),
                ui.Column(
                    self.up_button,
                    SquareLabel("Z"),
                    self.down_button
                ),
                SquareSpacer(),
                ui.Column(
                    ui.GroupBox(
                        title="Movement",
                        layout=self.movement_buttons
                    ),
                    ui.Spacer(horizontal=False)
                ),
                ui.Spacer(),
                stretch=(1, 0, 0, 0, 0, 0, 1)
            ),
            ui.Spacer(),
            stretch=(1, 0, 1)
        )
        self.append(ui.Column(
            ui.Row(
                ui.Column(
                    ui.GroupBox(
                        title="Control",
                        layout=self.controls_layout
                    ),
                    ui.Label("All controls relative to Probe-Card camera image.", enabled=False)
                ),
                ui.Column(
                    ui.GroupBox(
                        width=160,
                        title="Position",
                        layout=ui.Row(
                            ui.Column(
                                ui.Label("X"),
                                ui.Label("Y"),
                                ui.Label("Z"),
                            ),
                            ui.Column(
                                self.pos_x_label,
                                self.pos_y_label,
                                self.pos_z_label
                            ),
                        )
                    ),
                    ui.GroupBox(
                        title="State",
                        layout=ui.Row(
                            ui.Column(
                                ui.Label("X"),
                                ui.Label("Y"),
                                ui.Label("Z"),
                            ),
                            ui.Column(
                                self.cal_x_label,
                                self.cal_y_label,
                                self.cal_z_label
                            ),
                            ui.Column(
                                self.rm_x_label,
                                self.rm_y_label,
                                self.rm_z_label
                            )
                        )
                    ),
                    ui.Row(
                        ui.Label("Laser Sensor"),
                        self.laser_state_label,
                        stretch=(0, 1)
                    )
                ),
                ui.Spacer(),
                stretch=(0, 0, 0, 0, 0, 0, 0, 0, 0, 1)
            ),
            ui.Spacer(),
            stretch=(0, 1)
        ))
        # Init buttons
        if self.movement_buttons:
            self.movement_buttons[0].checked = True
        self.position = 0, 0, 0

    @property
    def step_width(self):
        for button in self.movement_buttons:
            if button.checked:
                return abs(button.movement_width)
        return 0

    @property
    def step_color(self):
        for button in self.movement_buttons:
            if button.checked:
                return button.movement_color
        return "black"

    @property
    def position(self):
        return self.__position

    @position.setter
    def position(self, value):
        self.__position = value[0], value[1], value[2]
        # TODO
        self.pos_x_label.text = f"{value[0] / 1000.:.3f} mm"
        self.pos_y_label.text = f"{value[1] / 1000.:.3f} mm"
        self.pos_z_label.text = f"{value[2] / 1000.:.3f} mm"

    @property
    def caldone(self):
        return self.__caldone

    @caldone.setter
    def caldone(self, value):
        def getcal(value):
            return value & 0x1
        def getrm(value):
            return (value >> 1) & 0x1
        self.__caldone = value[0], value[1], value[2]
        self.cal_x_label.text = "cal {}".format(getcal(value[0]))
        self.cal_x_label.stylesheet = "color: green" if getcal(value[0]) else "color: red"
        self.cal_y_label.text = "cal {}".format(getcal(value[1]))
        self.cal_y_label.stylesheet = "color: green" if getcal(value[1]) else "color: red"
        self.cal_z_label.text = "cal {}".format(getcal(value[2]))
        self.cal_z_label.stylesheet = "color: green" if getcal(value[2]) else "color: red"
        self.rm_x_label.text = "rm {}".format(getrm(value[0]))
        self.rm_x_label.stylesheet = "color: green" if getrm(value[0]) else "color: red"
        self.rm_y_label.text = "rm {}".format(getrm(value[1]))
        self.rm_y_label.stylesheet = "color: green" if getrm(value[1]) else "color: red"
        self.rm_z_label.text = "rm {}".format(getrm(value[2]))
        self.rm_z_label.stylesheet = "color: green" if getrm(value[2]) else "color: red"
        state = value == (3, 3, 3)
        self.controls_layout.enabled = state

    def on_back(self):
        self.emit("move", 0, self.step_width, 0)

    def on_front(self):
        self.emit("move", 0, -self.step_width, 0)

    def on_left(self):
        self.emit("move", -self.step_width, 0, 0)

    def on_right(self):
        self.emit("move", self.step_width, 0, 0)

    def on_up(self):
        self.emit("move", 0, 0, self.step_width)

    def on_down(self):
        self.emit("move", 0, 0, -self.step_width)

    def on_colorcode(self, state):
        for button in self.control_buttons:
            button.stylesheet = f"QPushButton{{color:{self.step_color};font-size:22px;}}"
