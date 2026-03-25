# Maya Model Checker v2

A plugin-based model validation tool for Autodesk Maya. Load any combination of checks, run them against a mesh, and get colour-coded feedback through rendered images and turntable videos — all from a single UI.

---

## Features

- **Plugin-based architecture** — checks are individual modules you load in and out at will, no restarts needed
- **Categorised UI** — checks are automatically sorted into tabs (Geometry, UVs, Misc)
- **Arnold image renders** — optional per-check still renders with result text overlaid
- **Turntable renders** — optional 360° playblast videos per failing check
- **TXT and JSON reports** — exportable check results with timestamps
- **Persistent check registration** — checks you load are remembered between Maya sessions

---

## Built-in Checks

### Geometry
| Check | What it does |
|---|---|
| **Lamina Faces** | Detects faces that share all their edges (stacked faces). Highlights them in red. |
| **Non-Manifold Edges** | Detects edges shared by more than two faces. Marks them with red curves. |
| **Non-Manifold Vertices** | Detects vertices that connect otherwise disconnected parts of the mesh. |
| **Polycount** | Checks whether the face count falls within a user-defined min/max range. |

### UVs
| Check | What it does |
|---|---|
| **Overlapping UVs** | Detects UV faces that overlap other UV faces. Highlights them in red. |
| **Texel Density** | Visualises texel density variation across the mesh using a blue-to-red colour ramp. |

### Misc
| Check | What it does |
|---|---|
| **Naming Convention** | Checks whether the mesh name starts and ends with a user-defined prefix and/or suffix. |
| **Polygon Density** | Checks the polygon density of the mesh and indicates it using a yellow-to-red colour ramp. |

---

## Installation

**Requirements:**
- Autodesk Maya (tested on Maya 2025 and Maya 2026)
- Arnold renderer (mtoa) — only required if using image renders
- Python packages: `Pillow`, `platformdirs`

**Install third-party packages into Maya's Python:**

Find `mayapy.exe` (usually at `C:/Program Files/Autodesk/Maya<version>/bin/mayapy.exe`) and run:

```
mayapy -m pip install Pillow platformdirs
```

**Install the tool:**

1. Copy the `model_checker_v2` folder into your Maya scripts directory:
    ```
    Documents/maya/scripts/model_checker_v2/
    ```
2. Make sure the folder contains `__init__.py` — if it does, you're good to go.

---

## Usage

**Launch the tool** by running this in Maya's Script Editor:

```python
import importlib
from model_checker_v2 import base_tool, ui_tool
importlib.reload(ui_tool)
importlib.reload(base_tool)

base_tool.ModelChecker()
```

Tip: drag this snippet onto a Maya shelf button so you can launch it with one click.

**Running checks:**

1. Either type a mesh name into the target field, or select a mesh in the viewport and check *Use current selection*
2. Click *Load Check* to load any check module (`.py` file) from disk
3. Set an output folder path if you want reports or renders saved
4. Toggle which output types you want (TXT report, JSON report, image renders, turntable renders)
5. Hit *Run All* or *Run Selected*

The tool duplicates your mesh before running any checks, so your original is never modified. Results are shown inline in the UI with colour-coded status indicators.

---

## Writing Your Own Check

All checks inherit from `BaseCheck`. Create a new `.py` file with the following structure:

```python
from model_checker_v2 import base_check
import maya.cmds as cmds

class MyCustomCheck(base_check.BaseCheck):
    def __init__(self, layout):
        super().__init__(layout)
        self.category = "Geometry"   # "Geometry", "UVs", or "Misc"
        self.check_cb = None
        self.arnold_shader_data = None  # set to "vertex" to enable image renders
        self.turntable_render = False

    def run(self, mesh, *args) -> dict:
        # your check logic here
        status = "PASS"
        details = "Everything looks good"
        self.update_result_message(status, self.GREEN)
        self.update_status_message("Completed", self.BLUE_COMPLETED)

        return {
            "name": "My Custom Check",
            "status": status,
            "details": details
        }

    def build_ui(self, *args):
        super().build_ui()
        self.check_cb = cmds.checkBox("My Custom Check", p=self.check_content)
```

Load it into the tool via the *Load Check* button. It will be registered and reloaded automatically on the next session.

---

## Output Files

All output files are saved into a `ModelChecker_Output/` folder inside your chosen output directory:

| File type | Contents |
|---|---|
| `.txt` report | Plain text summary of all check results with timestamps |
| `.json` report | Structured report data, useful for pipeline integration |
| `tests_images/` | Per-check Arnold renders with result text overlaid |
| `tests_turntables/` | Per-check 360° turntable playblasts as `.avi` files |

---

## Project Structure

```
model_checker_v2/
├── __init__.py
├── base_tool.py          # Core tool logic, report generation, render pipeline
├── ui_tool.py            # Maya UI definition
├── base_check.py         # Base class all check plugins inherit from
├── content/
│   └── remove_plugin_img.png
└── plugin_modules/       # Individual check modules
    ├── lamina_faces.py
    ├── naming_convention.py
    ├── non_manifold_edges.py
    ├── non_manifold_vertices.py
    ├── overlapping_uvs.py
    ├── polycount.py
    ├── polygon_density.py
    └── texel_density.py
```
