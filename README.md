# Scheduler Application - GenericTeamName - Spring 2026

Project Version: 2 (March 8, 2026)
--------------
Project Authors:

Tyler Strohl

Kyle Smith

Chayse Altland

Damion Crawford

Mohamed Mussa

Ibrahim Ntege

Shane del Villar

--------------
# Description:

A **graphical-user interface (GUI)** for managing scheduler configuration files used by the [course-constraint-scheduler](https://pypi.org/project/course-constraint-scheduler/). The GUI lets you edit faculty, courses, rooms, and labs in a JSON config file, view summaries, save or reload config, and run the constraint solver to generate schedules (JSON or CSV output). 

Users may export schedules & import pre-existing schedules. These can be viewed under a Schedule Viewer.

Config files follow the schema expected by the scheduler (see the [scheduler configuration docs](https://pypi.org/project/course-constraint-scheduler/) for the full format).

---

## Requirements

- **Python 3.12+**
- **Libraries** (installed automatically via `uv sync` or `pip install -e .`):
  - **course-constraint-scheduler** (≥2.6.1) – constraint solver for generating schedules; brings in:
    - **z3-solver** – Microsoft Z3 theorem prover used by the scheduler
    - **Pydantic** – config validation
    - Other runtime deps (e.g. bidict, click) as specified by the scheduler package
- **For running tests:** **pytest** (install with `pip install pytest` or add as a dev dependency)

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

## How to Use

### 1. Start the GUI

Run the app with python (or python3) and the file named **"main.py"**. Use **`uv run`** so the scheduler package is available:

```bash
uv run python main.py
```

If you run with `python` alone (without `uv run`), the **course-constraint-scheduler** package may not be found and the “Run scheduler” option will report that the scheduler is not installed. **This is vital to ensure schedules are generated properly.**

### 2. Main menu

After startup you’ll see 3 panels:

**Config Editor [Left-Panel]**
1. **Change Config File** - Prompts the user to select a config file from their chosen directory.
2. **Faculty** – Add, modify, or delete faculty; set available times and course preferences.
3. **Courses** – Add, modify, or delete courses (course ID, credits, rooms, labs, conflicts, faculty).
4. **Rooms** – Add, modify, or delete rooms.
5. **Labs** – Add, modify, or delete labs.
6. **View Config Summary** – Displays your current config JSON file.
7. **Save Config** – Save your current config file.

**Schedule Generator [Mid-Panel]**
1. **Set Limit (# Of Schedules)** - Prompts the user to specify (up to) how many schedules may be generated.
2. **Toggle Optimization** - Enables/Disables optimization flags (ex: a faculty member cannot teach two classes at the same time).
3. **Generate Schedules** - Generate & save schedules to a new JSON file, given the provided config file.

NOTE: Schedule Generation can be long. If generation fails, use "uv sync" to ensure the scheduler dependency has been added properly.

**Schedule Viewer [Right-Panel**
1. **View Schedules** - Displays schedules in a table format. Users can switch between multiple schedules (if applicable).
2. **Export Schedules** - Export the generated schedules to a new file.
3. **Import Schedules** - Import pre-existing schedules to view or modify.

### 3. Saving

- Use **Save Config** → to write the current in-memory config to the JSON file. A backup (`.bak`) is created before overwriting.
- Config is saved when changes (such as adding/modifying/deleting) are made. The user will receive a message when this occurs.

### 4. Running the scheduler

- Choose **Generate Schedules**, then **View Schedules**.
- You can set:
  - Config file path
  - Limit (number of schedules to generate)
  - Output file path
  - Whether to optimize schedules
- Generated schedules are written to the chosen file. The solver uses the same config format (courses, faculty, rooms, labs, time slots, etc.) as the rest of the GUI.

### 5. Running tests

From the project root, with pytest installed:

```bash
uv run pytest tests/[name_of_test_file.py]
```

Or, if the venv is activated:

```bash
pytest tests/[name_of_test_file.py]
```

---

## Project layout (summary)

- **`main.py`** – Entry point: `python main.py.
- **`app`** – Contains GUI files such as 'main_window.py' & logic files such as 'course_gui.py' & 'room_gui.py'.
- **`src`** – Contains CLI files from first project sprint.
- **`tests`** – Location of written pytests.
- **`example.json`** – Sample scheduler config.
