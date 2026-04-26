# Scheduler Application - GenericTeamName - Spring 2026 - CMSC 420

Project Version: 4 (April 26, 2026)
--------------
Project Authors:

Tyler Strohl

Kyle Smith

Chayse Altland

Shane del Villar

Mohamed Mussa

Ibrahim Ntege

Damion Crawford

--------------
# Description:

A **graphical-user interface (GUI)** for managing scheduler configuration files used by the [course-constraint-scheduler](https://pypi.org/project/course-constraint-scheduler/).

The user may edit faculty, courses, rooms, labs, timeslots, & meeting patterns. Schedules can be generated & exported to a JSON or PDF file, and [JSON] schedules may be imported back into the program. The user can specify the maximum # of schedules they'd like generated as well as any optimizations.
All changes are saved to a JSON config file. These files may be saved as or loaded.

Config files follow the schema expected by the scheduler (see the [scheduler configuration docs](https://pypi.org/project/course-constraint-scheduler/) for the full format).

When schedules are generated, they will appear in the main panel. These can be cycled through, and filters such as viewing by a specific room, may also be applied.

---

## Requirements

- **Python 3.12+**
- **Libraries** (installed automatically via `uv sync` or `pip install -e .`):
  - **course-constraint-scheduler** (≥2.6.1) – constraint solver for generating schedules; brings in:
    - **z3-solver** – Microsoft Z3 theorem prover used by the scheduler
    - **Pydantic** – config validation
    - Other runtime deps (e.g. bidict, click) as specified by the scheduler package
- **For running tests:** **pytest** (install with `pip install pytest` or add as a dev dependency)
- **AI assistant** **OpenAPI Key** (place the OpenAPI key in ai/ai_assistant.py to use the AI Assistant)

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

### 2. Navigating the menus

After startup you’ll see the following:

- Menu-Bar **[Top-Left]** with a theme toggle, 'File', 'Edit', 'Generator', 'Viewer', & 'Help'.
- Quick-Access Bar **[Top-Middle]** for quick-access to commonly used features (open, save, import, export, undo, redo, etc).
- Configuration **[Left]** to see the active config file details.
- Schedule **[Middle]**. This is where schedules will be displayed.
- Assistant **[Right]**. This panel contains an AI Chatbot; another way to interact with the program.

Below are more details on these:

A.) Menu-Bar [Top-Left]:
-------------

**Theme Toggle**
The user has a variety of color themes to choose from. The default choice is Light. However, some users may find Dark easier to view than Light.
Light & Dark are the easiest themes to view.

**File**
1. **Change Config File** - Select a config file from your chosen directory. The file is then loaded into the program.
2. **View Summary** – Displays a summary of your current config JSON file in a new window.
3. **Save Config** – Save your current config file.
4. **Save Config As** – Save-As your current config file (with any name) to your chosen directory.

**Edit**
1. **Faculty** – Add, modify, or delete faculty; set available times and course preferences. Times & preferences may be set under 'Modify Faculty'.
2. **Courses** – Add, modify, or delete courses (course ID, credits, rooms, labs, conflicts, faculty).
   
+ Courses also contains the Timeslot Config Editor, under 'Timeslots':
  - **Class Meeting Patterns** - Add, modify, or delete class meeting patterns.
  - **Edit Timeslots** - Add, modify, or delete course timeslots.

3. **Rooms** – Add, modify, or delete rooms.
4. **Labs** – Add, modify, or delete labs.

**Generator**
1. **Limit # Of Schedules** - Specify the maximum # of schedules that are generated.
2. **Toggle Optimization** - Select or un-select any optimization flags (ex: a faculty member cannot teach two classes at the same time).
3. **Generate Schedules** - Generate & save schedules to a new JSON file, given the provided config file. A progress-bar is displayed to the user during generation.

NOTE: If generation fails, use "uv sync" to ensure the scheduler dependency has been added properly.

**Viewer**
1. **View Schedules** - Displays schedules in a table format (no filters). Users can switch between multiple schedules (if applicable).
2. **View by Faculty** - Filter that displays only courses taught by a specified faculty member.
3. **View by Room** - Filter that displays only courses taught in a specified room.
4. **View by Lab** - Filter that displays only courses taught in a specified lab.
5. **Export Schedules** - Export the generated schedules to a new JSON file.
6. **Import Schedules** - Import pre-existing schedules to view or modify.
7. **Clear Schedules** - Clears the currently generated or imported schedules.

**Help**
Provides a list of Keyboard Shortcuts to use in the program.
These shortcuts are:
- Open configuration…     => Ctrl+O
- Save configuration      => Ctrl+S
- Generate schedules      => Ctrl+G
- Refresh schedule grid   => F5
- Import schedules        => Ctrl+Shift+I
- Export schedules        => Ctrl+Shift+E
- Configuration summary   => F2
- Send assistant message  => Ctrl+Enter (or Enter in the message field)


B.) Quick-Access Bar [Top-Middle]:
-------------

This panel is used for quick-access to commonly used features (open, save, import, export, etc).

This was made to make the UI experience smoother, & to improve usage for Mac OS users.

C.) Configuration [Left]:
-------------

This panel shows the active config details.

D.) Schedule [Middle]:
-------------

This main panel displays the following to the user:
- The imported schedules JSON filename (if schedules were imported).
- Which schedule is currently being viewed (if there are any schedules).
- Active Config JSON filename.
- Previous & Next buttons which allow the user to navigate between schedules.
- Table displaying the current schedule. This contains times & course names for each day (Mon - Fri).
  - The user may click on a specific course in the schedule to view more info, such as the faculty teaching the course & in which room.

E.) Assistant [Right]:
-------------

**AI Assistant** - The chatbot can be used as another way to interact with the program. The user describes what they would like to do (ex: add a new room called '210 A'). Then, the chatbot will execute the appropriate command & reflect the changes in the config JSON.

- NOTE: To use the chatbot, the OpenAI key must be entered. This can be placed in the file: **ai/ai_assistant.py**. Replace the empty string with the key.


### 3. Saving

- Use **Save Config** → to write the current in-memory config to the JSON file. A backup (`.bak`) is created before overwriting.
- **Save Config As** may also be used if the user wishes to create a new copy of their config JSON file.
- Config is saved when changes (such as adding/modifying/deleting) are made. The user will receive a message when this occurs.

### 4. Running the scheduler

- Choose **Generator**, then **Generate Schedules**.
- You can set:
  - Limit (number of schedules to generate)
  - Optimization flags
- Schedules are generated using the active config file. The solver uses the same config format (courses, faculty, rooms, labs, time slots, etc.) as the rest of the GUI.
- Generated schedules will be displayed in the main panel, and can be exported by going to **Viewer** then **Export Schedules**.

### 5. Running tests

From the project root, with pytest installed:

```bash
uv run pytest
```

Or, if the venv is activated:

```bash
pytest tests/[name_of_test_file.py]
```

---

## Project layout (summary)

- **`main.py`** – Entry point: `python main.py.
- **`gui/`** – Contains GUI files, such as 'main_window.py', 'menu_widgets.py', 'ui_styles.py', etc.
- **`gui/main_window.py** - Acts as the main view of the program.
- **`tests/`** – Location of written pytests.
- **`config/example.json`** – Sample scheduler config.
- **`config/config.json`** - An empty, default config file.
- **`config/config_mgr.py** - The model that handles configuration changes.
- **`faculty, course, room, lab, timeslot_config, & generator folders** all contain their respective features. These managers all act as controllers.
- **`viewer/** - Contains the 'ViewerManager' to act as a controller for various schedule viewer functions, such as updating view (main_window), and handling import/export with the config manager.
- **`ai/** - Contains ai logic & a controller to handle changes to the main_window view.
