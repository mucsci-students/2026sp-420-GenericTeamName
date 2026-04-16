'''
    File: test_generator.py
    Date: 03/06/2026
    Author: Tyler Strohl & Mohamed Mussa
    Class: CMSC 420
    Description: Pytests for Schedule Generator tasks.
'''
import json
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
from PyQt6.QtWidgets import QApplication
from app.generator_gui import GenConfigManager


# We need a QApplication running before any Qt window or button can be created.
# Without this, Qt crashes the whole program the moment a test tries to open
# a dialog. scope="session" means we only create it once for all tests.
@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


def _make_parent(tmp_path, config_data):
    # GenConfigManager needs a "parent" object that has a config_mgr attached.
    # In the real app this is the main window. In tests we fake it with a
    # MagicMock so no real window needs to open.
    # We also write a real config file to disk because the code reads from it.
    config_file = tmp_path / "config.json"
    config_file.write_text(json.dumps(config_data), encoding="utf-8")

    mock_config_mgr = MagicMock()
    mock_config_mgr.filepath = str(config_file)
    mock_config_mgr.data = config_data

    mock_parent = MagicMock()
    mock_parent.config_mgr = mock_config_mgr
    mock_parent.schedules = []

    return mock_parent, config_file, mock_config_mgr


# ---------------------------------------------------------------------------
# set_limit
# ---------------------------------------------------------------------------

def test_set_limit(tmp_path, mocker, qapp):
    config_data = {"limit": 2}
    mock_parent, config_file, mock_config_mgr = _make_parent(tmp_path, config_data)

    manager = GenConfigManager()
    manager.config_path = config_file
    manager._config_data = config_data

    # Pretend the user typed "10" into the input box and clicked OK.
    mocker.patch("app.generator_gui.QInputDialog.getText", return_value=("10", True))
    # Suppress the "saved!" popup so it doesn't block the test.
    mocker.patch("app.generator_gui.QMessageBox.information")

    manager.set_limit(mock_parent)

    # The limit in memory should now be 10.
    assert manager._config_data["limit"] == 10
    # The config file should have been saved.
    mock_config_mgr.save.assert_called_once()


# ---------------------------------------------------------------------------
# set_optimize
# ---------------------------------------------------------------------------

def test_set_optimize_true(tmp_path, mocker, qapp):
    """User checks all six optimizer boxes and clicks OK — all six flags saved."""
    config_data = {"optimizer_flags": []}
    mock_parent, config_file, mock_config_mgr = _make_parent(tmp_path, config_data)

    manager = GenConfigManager()
    manager.config_path = config_file
    manager._config_data = config_data

    # Replace the whole QDialog class so it never tries to draw a real window.
    # mock_dialog.exec() returning True means the user clicked OK.
    mock_dialog = MagicMock()
    mock_dialog.exec.return_value = True
    mocker.patch("app.generator_gui.QDialog", return_value=mock_dialog)

    # Make every checkbox report that it is checked.
    mocker.patch("app.generator_gui.QCheckBox.isChecked", return_value=True)
    # Suppress layout and button widgets — we don't need them to do anything.
    mocker.patch("app.generator_gui.QVBoxLayout")
    mocker.patch("app.generator_gui.QDialogButtonBox")
    mocker.patch("app.generator_gui.QMessageBox.information")

    manager.set_optimize(mock_parent)

    assert len(manager._config_data["optimizer_flags"]) == 6
    assert "faculty_course" in manager._config_data["optimizer_flags"]
    assert "pack_rooms" in manager._config_data["optimizer_flags"]


def test_set_optimize_false(tmp_path, mocker, qapp):
    """User unchecks all six optimizer boxes and clicks OK — empty list saved."""
    config_data = {"optimizer_flags": ["faculty_course"]}
    mock_parent, config_file, mock_config_mgr = _make_parent(tmp_path, config_data)

    manager = GenConfigManager()
    manager.config_path = config_file
    manager._config_data = config_data

    mock_dialog = MagicMock()
    mock_dialog.exec.return_value = True
    mocker.patch("app.generator_gui.QDialog", return_value=mock_dialog)

    # Make every checkbox report that it is unchecked.
    mocker.patch("app.generator_gui.QCheckBox.isChecked", return_value=False)
    mocker.patch("app.generator_gui.QVBoxLayout")
    mocker.patch("app.generator_gui.QDialogButtonBox")
    mocker.patch("app.generator_gui.QMessageBox.information")

    manager.set_optimize(mock_parent)

    assert manager._config_data["optimizer_flags"] == []


def test_set_optimize_partial(tmp_path, mocker, qapp):
    """User checks only the first three boxes — only those three flags saved.

    This was added because the reviewer asked for a test where some flags
    are on and some are off, not just all-on or all-off.
    side_effect gives each checkbox its own return value in order:
    box 1 = True, box 2 = True, box 3 = True, box 4 = False, box 5 = False, box 6 = False.
    """
    config_data = {"optimizer_flags": []}
    mock_parent, config_file, mock_config_mgr = _make_parent(tmp_path, config_data)

    manager = GenConfigManager()
    manager.config_path = config_file
    manager._config_data = config_data

    mock_dialog = MagicMock()
    mock_dialog.exec.return_value = True
    mocker.patch("app.generator_gui.QDialog", return_value=mock_dialog)

    mocker.patch(
        "app.generator_gui.QCheckBox.isChecked",
        side_effect=[True, True, True, False, False, False]
    )
    mocker.patch("app.generator_gui.QVBoxLayout")
    mocker.patch("app.generator_gui.QDialogButtonBox")
    mocker.patch("app.generator_gui.QMessageBox.information")

    manager.set_optimize(mock_parent)

    expected = ["faculty_course", "faculty_room", "faculty_lab"]
    assert manager._config_data["optimizer_flags"] == expected


def test_set_optimize_cancel(tmp_path, mocker, qapp):
    """User opens the dialog then clicks Cancel — flags stay exactly as they were."""
    initial_flags = ["faculty_course", "same_room"]
    config_data = {"optimizer_flags": list(initial_flags)}
    mock_parent, config_file, mock_config_mgr = _make_parent(tmp_path, config_data)

    manager = GenConfigManager()
    manager.config_path = config_file
    manager._config_data = config_data

    # exec() returning False means the user clicked Cancel.
    mock_dialog = MagicMock()
    mock_dialog.exec.return_value = False
    mocker.patch("app.generator_gui.QDialog", return_value=mock_dialog)

    mocker.patch("app.generator_gui.QVBoxLayout")
    mocker.patch("app.generator_gui.QDialogButtonBox")
    mocker.patch("app.generator_gui.QMessageBox.information")

    manager.set_optimize(mock_parent)

    assert manager._config_data["optimizer_flags"] == initial_flags


# ---------------------------------------------------------------------------
# _save
# ---------------------------------------------------------------------------

def test_save_writes_file(tmp_path, mocker):
    """Check that _save actually writes the config data to disk."""
    manager = GenConfigManager()

    test_path = tmp_path / "test_save.json"
    manager.config_path = test_path
    manager._config_data = {"key": "value"}

    mock_info = mocker.patch("app.generator_gui.QMessageBox.information")

    manager._save(None)

    assert test_path.exists()
    assert json.loads(test_path.read_text())["key"] == "value"
    mock_info.assert_called_once()


def test_save_handles_os_error(tmp_path, mocker):
    """If the disk write fails, _save should show an error box, not crash."""
    manager = GenConfigManager()

    config_file = tmp_path / "config.json"
    manager.config_path = config_file
    manager._config_data = {"limit": 2}

    mock_critical = mocker.patch("app.generator_gui.QMessageBox.critical")
    # Force the file write to fail with a disk-full error.
    mocker.patch.object(Path, "write_text", side_effect=OSError("Disk full"))

    manager._save(None)

    mock_critical.assert_called_once()
    assert mock_critical.call_args[0][1] == "Save failed"


# ---------------------------------------------------------------------------
# run_scheduler — shared setup
# ---------------------------------------------------------------------------

def _setup_run_scheduler(mocker, manager, mock_parent, mock_schedules, limit):
    # Scheduler and load_config_from_file are imported inside run_scheduler's
    # function body, so we patch them at their source module "scheduler.*".
    # Everything else (QProgressDialog, QMessageBox, ScheduleWorker) is patched
    # at "app.generator_gui.*" because generator_gui.py imported them with
    # "from PyQt6.QtWidgets import ..." which created its own local copies.
    # Patching PyQt6.QtWidgets directly would have no effect on those copies.
    mock_sched_instance = MagicMock()
    mock_sched_instance.get_models.return_value = mock_schedules

    mocker.patch("scheduler.Scheduler", return_value=mock_sched_instance)
    mocker.patch("scheduler.load_config_from_file")
    mocker.patch("scheduler.config.CombinedConfig", MagicMock())

    mocker.patch("app.generator_gui.QProgressDialog")
    mocker.patch("app.generator_gui.QMessageBox")

    mock_worker = MagicMock()
    mock_worker_cls = mocker.patch(
        "app.generator_gui.ScheduleWorker", return_value=mock_worker
    )

    return mock_sched_instance, mock_worker, mock_worker_cls


# ---------------------------------------------------------------------------
# run_scheduler — schedule generation scenarios
# ---------------------------------------------------------------------------

def test_gen_new_file(tmp_path, mocker, qapp):
    """Baseline: running the scheduler starts the worker with the right arguments."""
    config_data = {"limit": 1}
    mock_parent, config_file, _ = _make_parent(tmp_path, config_data)

    manager = GenConfigManager()
    manager.config_path = config_file
    manager._config_data = config_data

    mock_schedules = [[{"course_id": "CMSC 140"}]]
    mock_sched, mock_worker, mock_worker_cls = _setup_run_scheduler(
        mocker, manager, mock_parent, mock_schedules, limit=1
    )

    manager.run_scheduler(mock_parent)

    # The background worker must have been started.
    mock_worker.start.assert_called_once()
    # The worker must have received the scheduler object and the limit of 1.
    mock_worker_cls.assert_called_once_with(mock_sched, 1)


def test_run_scheduler_multiple_schedules(tmp_path, mocker, qapp):
    """When limit is 3, the worker is told to generate up to 3 schedules."""
    config_data = {"limit": 3}
    mock_parent, config_file, _ = _make_parent(tmp_path, config_data)

    manager = GenConfigManager()
    manager.config_path = config_file
    manager._config_data = config_data

    mock_schedules = [
        [{"course_id": "CMSC 140"}],
        [{"course_id": "CMSC 201"}],
        [{"course_id": "CMSC 420"}],
    ]
    mock_sched, mock_worker, mock_worker_cls = _setup_run_scheduler(
        mocker, manager, mock_parent, mock_schedules, limit=3
    )

    manager.run_scheduler(mock_parent)

    mock_worker.start.assert_called_once()
    mock_worker_cls.assert_called_once_with(mock_sched, 3)


def test_run_scheduler_zero_limit(tmp_path, mocker, qapp):
    """Edge case: a limit of 0 should still set up and start the worker without crashing."""
    config_data = {"limit": 0}
    mock_parent, config_file, _ = _make_parent(tmp_path, config_data)

    manager = GenConfigManager()
    manager.config_path = config_file
    manager._config_data = config_data

    mock_sched, mock_worker, mock_worker_cls = _setup_run_scheduler(
        mocker, manager, mock_parent, mock_schedules=[], limit=0
    )

    manager.run_scheduler(mock_parent)

    mock_worker.start.assert_called_once()
    mock_worker_cls.assert_called_once_with(mock_sched, 0)


def test_run_scheduler_config_load_fails(tmp_path, mocker, qapp):
    """If no config file is selected, the scheduler should never be created."""
    config_data = {"limit": 5}
    mock_parent, config_file, mock_config_mgr = _make_parent(tmp_path, config_data)
    # Setting filepath to None simulates the user not having picked a config file yet.
    mock_config_mgr.filepath = None

    manager = GenConfigManager()
    manager.config_path = config_file
    manager._config_data = config_data

    mock_scheduler_cls = mocker.patch("scheduler.Scheduler")
    mocker.patch("app.generator_gui.QMessageBox")

    manager.run_scheduler(mock_parent)

    # Scheduler.__init__ should never have been called.
    mock_scheduler_cls.assert_not_called()