import copy
import math
import os

from comet import ui
from comet.settings import SettingsMixin
from qutie.qutie import QtCore, QtGui

from analysis_pqc import STATUS_PASSED

from .config import load_sequence, list_configs, SEQUENCE_DIR

from .components import PositionsComboBox
from .components import OperatorWidget
from .components import WorkingDirectoryWidget

from .settings import settings
from .utils import from_table_unit, to_table_unit, make_path

__all__ = ['StartSequenceDialog', 'StartSampleDialog']

class StartSequenceDialog(ui.Dialog, SettingsMixin):

    def __init__(self, context, table_enabled):
        super().__init__()
        self.title = "Start Sequence"
        self._contact_checkbox = ui.CheckBox(
            text="Move table and contact with Probe Card",
            checked=context.has_position,
            enabled=context.has_position and table_enabled
        )
        self._position_checkbox = ui.CheckBox(
            text="Move table after measurements",
            checked=False,
            enabled=table_enabled,
            changed=self.on_position_checkbox_toggled
        )
        self._positions_combobox = PositionsComboBox(
            enabled=False
        )
        self._operator_combobox = OperatorWidget()
        self._output_combobox = WorkingDirectoryWidget()
        self._button_box = ui.DialogButtonBox(
            buttons=("yes", "no"),
            accepted=self.accept,
            rejected=self.reject
        )
        self._button_box.qt.button(self._button_box.QtClass.Yes).setAutoDefault(False)
        self._button_box.qt.button(self._button_box.QtClass.No).setDefault(True)
        self.layout = ui.Column(
            ui.Label(
                text=self._create_message(context)
            ),
            ui.GroupBox(
                title="Table",
                layout=ui.Column(
                    self._contact_checkbox,
                    ui.Row(
                        self._position_checkbox,
                        self._positions_combobox
                    ),
                    ui.Spacer()
                )
            ),
            ui.Row(
                ui.GroupBox(
                    title="Operator",
                    layout=self._operator_combobox
                ),
                ui.GroupBox(
                    title="Working Directory",
                    layout=self._output_combobox
                )
            ),
            self._button_box,
            stretch=(1, 0, 0, 0)
        )

    def load_settings(self):
        self._position_checkbox.checked = bool(self.settings.get('move_on_success') or False)
        self._positions_combobox.load_settings()
        self._operator_combobox.load_settings()
        self._output_combobox.load_settings()

    def store_settings(self):
        self.settings['move_on_success'] = self._position_checkbox.checked
        self._positions_combobox.store_settings()
        self._operator_combobox.store_settings()
        self._output_combobox.store_settings()

    def on_position_checkbox_toggled(self, state):
        self._positions_combobox.enabled = state

    def move_to_contact(self):
        return self._contact_checkbox.checked

    def move_to_position(self):
        if self.move_to_contact() and self._position_checkbox.checked:
            current = self._positions_combobox.current
            if current:
                index = self._positions_combobox.index(current)
                positions = settings.table_positions
                if 0 <= index < len(positions):
                    position = positions[index]
                    return position.x, position.y, position.z
        return None

    def _create_message(self, context):
        if isinstance(context, SampleSequence):
            return "<b>Are you sure to start all enabled sequences for all enabled samples?</b>"
        elif isinstance(context, SampleTreeItem):
            return f"<b>Are you sure to start all enabled sequences for '{context.name}'?</b>"
        elif isinstance(context, ContactTreeItem):
            return f"<b>Are you sure to start sequence '{context.name}'?</b>"

class SequenceManager(ui.Dialog, SettingsMixin):
    """Dialog for managing custom sequence configuration files."""

    def __init__(self):
        super().__init__()
        # Properties
        self.title = "Sequence Manager"
        # Layout
        self.resize(640, 480)
        self._sequence_tree = ui.Tree(
            header=("Name", "Filename"),
            indentation=0,
            selected=self.on_sequence_tree_selected
        )
        self.add_button = ui.Button(
            text="&Add",
            clicked=self.on_add_sequence
        )
        self.remove_button = ui.Button(
            text="&Remove",
            enabled=False,
            clicked=self.on_remove_sequence
        )
        self.preview_textarea = ui.TextArea(
            readonly=True
        )
        font = self.preview_textarea.qt.font()
        font.setFamily("Monospace")
        self.preview_textarea.qt.setFont(font)
        self.layout = ui.Column(
            ui.Row(
                ui.Column(
                    self._sequence_tree,
                    self.preview_textarea,
                    stretch=(4, 3)
                ),
                ui.Column(
                    self.add_button,
                    self.remove_button,
                    ui.Spacer()
                ),
                stretch=(1, 0)
            ),
            ui.DialogButtonBox(
                buttons=("ok", "cancel"),
                accepted=self.accept,
                rejected=self.reject
            ),
            stretch=(1, 0)
        )

    @property
    def current_sequence(self):
        """Return selected sequence object or None if nothing selected."""
        item = self._sequence_tree.current
        if item is not None:
            return item.sequence
        return None

    def load_settings(self):
        self.load_settings_dialog_size()
        self.load_settings_sequences()

    def load_settings_dialog_size(self):
        """Load dialog size from settings."""
        width, height = self.settings.get('sequence_manager_dialog_size') or (640, 480)
        self.resize(width, height)

    def load_settings_sequences(self):
        """Load all built-in and custom sequences from settings."""
        self._sequence_tree.clear()
        def load_all_sequences():
            configs = []
            for name, filename in list_configs(SEQUENCE_DIR):
                configs.append((name, filename, True))
            for filename in list(set(self.settings.get('custom_sequences') or [])):
                if os.path.exists(filename):
                    try:
                        sequence = load_sequence(filename)
                    except:
                        pass
                    else:
                        configs.append((sequence.name, filename, False))
            return configs
        for name, filename, builtin in load_all_sequences():
            try:
                sequence = load_sequence(filename)
                item = self._sequence_tree.append([sequence.name, '(built-in)' if builtin else filename])
                item.sequence = sequence
                item.sequence.builtin = builtin
                item.qt.setToolTip(1, filename)
            except Exception as exc:
                logging.error("failed to load sequence: %s", filename)
                pass
        self._sequence_tree.fit()
        if len(self._sequence_tree):
            self._sequence_tree.current = self._sequence_tree[0]

    def store_settings(self):
        self.store_settings_dialog_size()
        self.store_settings_sequences()

    def store_settings_dialog_size(self):
        """Store dialog size to settings."""
        self.settings['sequence_manager_dialog_size'] = self.width, self.height

    def store_settings_sequences(self):
        """Store custom sequences to settings."""
        sequences = []
        for item in self._sequence_tree:
            if not item.sequence.builtin:
                sequences.append(item.sequence.filename)
        self.settings['custom_sequences'] = list(set(sequences))

    def on_sequence_tree_selected(self, item):
        """Load sequence config preview."""
        self.remove_button.enabled = False
        self.preview_textarea.clear()
        if item is not None:
            self.remove_button.enabled = not item.sequence.builtin
            if os.path.exists(item.sequence.filename):
                with open(item.sequence.filename) as f:
                    self.preview_textarea.qt.setText(f.read())
                    self.preview_textarea.qt.textCursor().setPosition(0)
                    self.preview_textarea.qt.ensureCursorVisible()

    def on_add_sequence(self):
        filename = ui.filename_open(filter="YAML files (*.yml, *.yaml);;All files (*)")
        if filename:
            try:
                sequence = load_sequence(filename)
            except Exception as exc:
                ui.show_exception(exc)
            else:
                if filename not in self.sequence_filenames:
                    item = self._sequence_tree.append([sequence.name, filename])
                    item.qt.setToolTip(1, filename)
                    item.sequence = sequence
                    item.sequence.builtin = False
                    self._sequence_tree.current = item

    def on_remove_sequence(self):
        item = self.sequence_tree.current
        if item and not item.sequence.builtin:
            if ui.show_question(
                title="Remove Sequence",
                text=f"Do yo want to remove sequence '{item.sequence.name}'?"
            ):
                self._sequence_tree.remove(item)
                self.remove_button.enabled = len(self._sequence_tree)

    @property
    def sequence_filenames(self):
        filenames = []
        for sequence_item in self._sequence_tree:
            filenames.append(sequence_item.sequence.filename)
        return filenames

class SequenceTree(ui.Tree):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.expands_on_double_click = False
        self.header = ["Name", "Pos", "State"]
        self.qt.header().setMinimumSectionSize(32)
        self.qt.header().resizeSection(1, 32)

    def lock(self):
        for contact in self:
            contact.lock()

    def unlock(self):
        for contact in self:
            contact.unlock()

    def reset(self):
        for contact in self:
            contact.reset()

class SampleSequence:
    """Virtual item holding multiple samples to be executed."""

    def __init__(self, samples):
        self.samples = samples

class SequenceTreeItem(ui.TreeItem):

    ProcessingState = "Processing..."
    ActiveState = "Active"
    SuccessState = "Success"
    ComplianceState = "Compliance"
    TimeoutState = "Timeout"
    ErrorState = "Error"
    StoppedState = "Stopped"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.checkable = True

    def lock(self):
        self.checkable = False
        self.selectable = False
        for child in self.children:
            child.lock()

    def unlock(self):
        self.checkable = True
        self.selectable = True
        for child in self.children:
            child.unlock()

    def reset(self):
        self.state = None
        self.quality = None
        for child in self.children:
            child.reset()

    @property
    def selectable(self):
        return self.qt.flags() & QtCore.Qt.ItemIsSelectable != 0

    @selectable.setter
    def selectable(self, value):
        flags = self.qt.flags()
        if value:
            flags |= QtCore.Qt.ItemIsSelectable
        else:
            flags &= ~QtCore.Qt.ItemIsSelectable
        self.qt.setFlags(flags)

    @property
    def name(self):
        return self[0].value

    @name.setter
    def name(self, value):
        self[0].value = value

    @property
    def enabled(self):
        return self[0].checked

    @enabled.setter
    def enabled(self, enabled):
        self[0].checked = enabled

    @property
    def state(self):
        return self[2].value

    @state.setter
    def state(self, value):
        self[0].bold = (value in (self.ActiveState, self.ProcessingState))
        self[0].color = None
        if value == self.SuccessState:
            self[2].color = "green"
        elif value in (self.ActiveState, self.ProcessingState):
            self[0].color = "blue"
            self[2].color = "blue"
        else:
            self[2].color = "red"
        self[2].value = value

    @property
    def quality(self):
        return self[3].value

    @quality.setter
    def quality(self, value):
        # Oh dear...
        value = value or ""
        if value.lower() == STATUS_PASSED.lower():
            self[3].color = "green"
        else:
            self[3].color = "red"
        self[3].value = value.capitalize()

class SampleTreeItem(SequenceTreeItem):
    """Sample (halfmoon) item of sequence tree."""

    def __init__(self, name_prefix=None, name_infix=None, name_suffix=None, sample_type=None, enabled=False, comment=None):
        super().__init__()
        self._name_prefix = name_prefix or ""
        self._name_infix = name_infix or ""
        self._name_suffix = name_suffix or ""
        self._sample_type = sample_type or ""
        self.update_name()
        self.comment = comment or ""
        self.enabled = enabled
        self.sequence = None

    @property
    def sequence_filename(self):
        return self.sequence.filename if self.sequence else None

    def from_settings(self, **kwargs):
        self._name_prefix = kwargs.get("sample_name_prefix") or ""
        self._name_infix = kwargs.get("sample_name_infix") or sample.get("sample_name") or "Unnamed"
        self._name_suffix = kwargs.get("sample_name_suffix") or ""
        self.update_name()
        self.sample_type = kwargs.get("sample_type") or ""
        self.enabled = kwargs.get("sample_enabled") or False
        self.comment = kwargs.get("sample_comment") or ""
        filename = kwargs.get("sample_sequence_filename")
        if filename and os.path.exists(filename):
            sequence = load_sequence(filename)
            self.load_sequence(sequence)
        default_position = float('nan'), float('nan'), float('nan')
        for contact_position in kwargs.get("sample_contacts") or []:
            for contact in self.children:
                if contact.id == contact_position.get("id"):
                    try:
                        x, y, z = tuple(map(from_table_unit, contact_position.get("position")))
                    except:
                        pass
                    else:
                        contact.position = x, y, z
                    finally:
                        break

    def to_settings(self):
        sample_contacts = []
        for contact in self.children:
            if contact.has_position:
                sample_contacts.append({
                    "id": contact.id,
                    "position": tuple(map(to_table_unit, contact.position))
                })
        return {
            "sample_name_prefix": self.name_prefix,
            "sample_name_infix": self.name_infix,
            "sample_name_suffix": self.name_suffix,
            "sample_type": self.sample_type,
            "sample_enabled": self.enabled,
            "sample_comment": self.comment,
            "sample_sequence_filename": self.sequence_filename,
            "sample_contacts": sample_contacts
        }

    @property
    def name(self):
        return ''.join((self.name_prefix, self.name_infix, self.name_suffix)).strip()

    @property
    def name_prefix(self):
        return self._name_prefix

    @name_prefix.setter
    def name_prefix(self, value):
        self._name_prefix = value
        self.update_name()

    @property
    def name_infix(self):
        return self._name_infix

    @name_infix.setter
    def name_infix(self, value):
        self._name_infix = value
        self.update_name()

    @property
    def name_suffix(self):
        return self._name_suffix

    @name_suffix.setter
    def name_suffix(self, value):
        self._name_suffix = value
        self.update_name()

    @property
    def sample_type(self):
        return self._sample_type.strip()

    @sample_type.setter
    def sample_type(self, value):
        self._sample_type = value
        self.update_name()

    def update_name(self):
        tokens = self.name, self.sample_type
        self[0].value = '/'.join((token for token in tokens if token))

    def load_sequence(self, sequence):
        while len(self.children):
            self.qt.takeChild(0)
        self.sequence = sequence
        for contact in sequence.contacts:
            item = self.append(ContactTreeItem(self, contact))
            item.expanded = True

class ContactTreeItem(SequenceTreeItem):
    """Contact (flute) item of sequence tree."""

    def __init__(self, sample, contact):
        super().__init__([contact.name, None])
        self.sample = sample
        self.id = contact.id
        self.name = contact.name
        self.enabled = contact.enabled
        self.contact_id = contact.contact_id
        self.description = contact.description
        self.reset_position()
        for measurement in contact.measurements:
            self.append(MeasurementTreeItem(self, measurement))

    @property
    def position(self):
        return self.__position

    @position.setter
    def position(self, position):
        x, y, z = position
        self.__position = x, y, z
        self[1].value = {False: '', True: 'OK'}.get(self.has_position)

    @property
    def has_position(self):
        return any((not math.isnan(value) for value in self.__position))

    def reset_position(self):
        self.position = float('nan'), float('nan'), float('nan')

class MeasurementTreeItem(SequenceTreeItem):
    """Measurement item of sequence tree."""

    def __init__(self, contact, measurement):
        super().__init__([measurement.name, None])
        self.contact = contact
        self.id = measurement.id
        self.name = measurement.name
        self.type = measurement.type
        self.enabled = measurement.enabled
        self.parameters = copy.deepcopy(measurement.parameters)
        self.default_parameters = copy.deepcopy(measurement.default_parameters)
        self.description = measurement.description
        self.series = {}
        self.analysis = {}
