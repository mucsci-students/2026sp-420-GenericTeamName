# GenericTeamName
--------------

Tyler Strohl
Kyle Smith
Chayse Altland
Damion Crawford
Mohamed Mussa
Ibrahim Ntege
Shane del Villar

--------------
A **GUI** for managing scheduler configuration files used by the [course-constraint-scheduler](https://pypi.org/project/course-constraint-scheduler/). Edit courses, faculty, rooms, and labs; generate, view, import, and export schedules. Config files follow the schema expected by the scheduler (see the [scheduler configuration docs](https://pypi.org/project/course-constraint-scheduler/)).

---

## Requirements

- **Python 3.12+**
- **Libraries** (installed automatically via `uv sync` or `pip install -e .`):
  - **course-constraint-scheduler** (≥2.6.1) – constraint solver for generating schedules; brings in:
    - **z3-solver** – Microsoft Z3 theorem prover used by the scheduler
    - **Pydantic** – config validation
    - Other runtime deps (e.g. bidict, click) as specified by the scheduler package
  - **PyQt6** – GUI framework

---

## Installation

From the project root (where `pyproject.toml` and `uv.lock` are):

```bash
uv sync
```

Or with pip:

```bash
pip install -e .
```

---

## Running the GUI

To run the graphical interface:

```bash
uv run python main.py
```

Run from the project root (where `main.py` is). Use **`uv run python main.py`** so dependencies (including the scheduler) are available. The GUI opens the default config at `config/config.json`; use **Change Config File** in the app to select a different config.

---

## Project layout (summary)

- **`main.py`** – Entry point for the GUI: `uv run python main.py`
- **`app/`** – GUI code: `main_window.py`, `course_gui.py`, `faculty_gui.py`, `room_gui.py`, `lab_gui.py`, `generator_gui.py`
- **`config/`** – Config loading/saving (`config_mgr.py`)
