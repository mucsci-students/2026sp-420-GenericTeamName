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
A **command-line interface (CLI)** for managing scheduler configuration files used by the [course-constraint-scheduler](https://pypi.org/project/course-constraint-scheduler/). The CLI lets you edit courses, faculty, rooms, and labs in a JSON config file, view summaries, save or reload config, and run the constraint solver to generate schedules (JSON or CSV output).

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

### 1. Start the CLI

Run the app with a path to your scheduler config JSON (e.g. `example.json`). Use **`uv run`** so the scheduler package is available:

```bash
uv run python src/main.py path/to/config.json
```

Example with the included sample config:

```bash
uv run python src/main.py src/example.json
```

If you run with `python` alone (without `uv run`), the **course-constraint-scheduler** package may not be found and the “Run scheduler” option will report that the scheduler is not installed.

### 2. Main menu

After startup you’ll see:

1. **Course Management** – Add, modify, or delete courses (course ID, credits, rooms, labs, conflicts, faculty).
2. **Faculty Management** – Add, modify, or delete faculty; set available times and course preferences.
3. **Room Management** – Add, modify, or delete rooms.
4. **Lab Management** – Add, modify, or delete labs.
5. **Config Management** – View config summary, save without exiting, or save and exit.
6. **Run / display schedule** – Set config path, limit, format (CSV/JSON), output file, and optimization; run the scheduler or display config summary.
7. **Exit without saving** – Quit and discard unsaved changes (with confirmation if there are changes).

### 3. Saving

- Use **Config Management (5)** → “Save config (without exiting)” or “Save config and exit” to write the current in-memory config to the JSON file. A backup (`.bak`) is created before overwriting.
- Changes to courses, faculty, rooms, or labs are only written when you save via Config Management or exit with “Save config and exit.”

### 4. Running the scheduler

- Choose **6) Run / display schedule**, then **6) Run scheduler**.
- You can set:
  - Config file path (defaults to the file you started the CLI with)
  - Limit (number of schedules to generate)
  - Output format (CSV or JSON)
  - Output file path (optional; if omitted, schedules are printed to the console)
  - Whether to optimize schedules
- Generated schedules are written to the chosen file or printed. The solver uses the same config format (courses, faculty, rooms, labs, time slots, etc.) as the rest of the CLI.

### 5. Running tests

From the project root, with pytest installed:

```bash
uv run pytest src/config/
```

Or, if the venv is activated:

```bash
pytest src/config/
```

---

## Project layout (summary)

- **`src/main.py`** – Entry point: `python src/main.py <config.json>`
- **`src/cli/`** – CLI logic: `main.py`, `course.py`, `faculty.py`, `room.py`, `lab.py`, `config_mgmt.py`, `common.py`
- **`src/run.py`** – Run/display schedule menu and scheduler invocation
- **`src/config/`** – Config loading/saving and summary (`config_mgr.py`); tests in `test_config.py`, `conftest.py`
- **`src/example.json`** – Sample scheduler config
