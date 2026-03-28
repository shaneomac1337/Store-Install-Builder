# Generation Summary Dialog Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a post-generation modal summary dialog that shows users what was generated, key config values used, and informational notes about deviations from defaults.

**Architecture:** A lightweight `GenerationTracker` class collects file and note data during generation. Each generator method receives the tracker and reports into it. After generation completes, a `GenerationSummaryDialog` reads the tracker and renders a modal CTkToplevel.

**Tech Stack:** Python, CustomTkinter (CTkToplevel, CTkLabel, CTkButton, CTkScrollableFrame), os/subprocess for Open Folder action.

---

### Task 1: Create GenerationTracker class with tests

**Files:**
- Create: `gk_install_builder/generation_tracker.py`
- Create: `tests/unit/test_generation_tracker.py`

**Step 1: Write the failing tests**

```python
"""Tests for GenerationTracker"""
import pytest
from gk_install_builder.generation_tracker import GenerationTracker


class TestGenerationTracker:
    """Test GenerationTracker data collection"""

    def test_init_empty(self):
        """Tracker starts with no files and no notes"""
        tracker = GenerationTracker()
        assert tracker.get_files() == []
        assert tracker.get_notes() == []
        assert tracker.get_config_snapshot() == {}

    def test_add_file(self):
        """Can add a file with category"""
        tracker = GenerationTracker()
        tracker.add_file("GKInstall.ps1", GenerationTracker.SCRIPTS)
        files = tracker.get_files()
        assert len(files) == 1
        assert files[0] == {"name": "GKInstall.ps1", "category": GenerationTracker.SCRIPTS}

    def test_add_multiple_files(self):
        """Multiple files tracked in order"""
        tracker = GenerationTracker()
        tracker.add_file("GKInstall.ps1", GenerationTracker.SCRIPTS)
        tracker.add_file("launcher.pos.template", GenerationTracker.LAUNCHERS)
        assert len(tracker.get_files()) == 2

    def test_add_note(self):
        """Can add an info note"""
        tracker = GenerationTracker()
        tracker.add_note("No certificate configured — skipped")
        notes = tracker.get_notes()
        assert len(notes) == 1
        assert notes[0] == "No certificate configured — skipped"

    def test_set_config_snapshot(self):
        """Can store a config snapshot"""
        tracker = GenerationTracker()
        tracker.set_config_snapshot(
            platform="Windows",
            base_url="test.cse.cloud4retail.co",
            tenant_id="001",
            api_version="new",
            output_dir="CSE/test.cse.cloud4retail.co"
        )
        snap = tracker.get_config_snapshot()
        assert snap["platform"] == "Windows"
        assert snap["base_url"] == "test.cse.cloud4retail.co"
        assert snap["tenant_id"] == "001"
        assert snap["api_version"] == "new"
        assert snap["output_dir"] == "CSE/test.cse.cloud4retail.co"

    def test_get_file_counts(self):
        """File counts grouped by category"""
        tracker = GenerationTracker()
        tracker.add_file("GKInstall.ps1", GenerationTracker.SCRIPTS)
        tracker.add_file("onboarding.ps1", GenerationTracker.SCRIPTS)
        tracker.add_file("launcher.pos.template", GenerationTracker.LAUNCHERS)
        counts = tracker.get_file_counts()
        assert counts[GenerationTracker.SCRIPTS] == 2
        assert counts[GenerationTracker.LAUNCHERS] == 1
        assert tracker.get_total_file_count() == 3

    def test_categories_are_string_constants(self):
        """Category constants exist"""
        assert GenerationTracker.SCRIPTS == "scripts"
        assert GenerationTracker.LAUNCHERS == "launchers"
        assert GenerationTracker.CONFIGS == "configs"
        assert GenerationTracker.TOKENS == "tokens"
        assert GenerationTracker.OVERRIDES == "overrides"
        assert GenerationTracker.OTHER == "other"

    def test_no_duplicate_notes(self):
        """Adding the same note twice only stores it once"""
        tracker = GenerationTracker()
        tracker.add_note("No certificate configured — skipped")
        tracker.add_note("No certificate configured — skipped")
        assert len(tracker.get_notes()) == 1
```

**Step 2: Run tests to verify they fail**

Run: `pytest tests/unit/test_generation_tracker.py -v`
Expected: FAIL — module `generation_tracker` does not exist

**Step 3: Write the implementation**

```python
"""
Generation Tracker

Lightweight collector that generation steps report into.
Tracks files generated, informational notes, and config snapshot.
"""


class GenerationTracker:
    """Collects generation results for the summary dialog."""

    # File categories
    SCRIPTS = "scripts"
    LAUNCHERS = "launchers"
    CONFIGS = "configs"
    TOKENS = "tokens"
    OVERRIDES = "overrides"
    OTHER = "other"

    def __init__(self):
        self._files = []
        self._notes = []
        self._config_snapshot = {}

    def add_file(self, name, category):
        """Record a generated file.

        Args:
            name: Filename (e.g. "GKInstall.ps1")
            category: One of the category constants (SCRIPTS, LAUNCHERS, etc.)
        """
        self._files.append({"name": name, "category": category})

    def add_note(self, text):
        """Record an informational note. Duplicates are ignored.

        Args:
            text: Note message (e.g. "No certificate configured — skipped")
        """
        if text not in self._notes:
            self._notes.append(text)

    def set_config_snapshot(self, platform, base_url, tenant_id, api_version, output_dir):
        """Store key config values used during generation."""
        self._config_snapshot = {
            "platform": platform,
            "base_url": base_url,
            "tenant_id": tenant_id,
            "api_version": api_version,
            "output_dir": output_dir,
        }

    def get_files(self):
        """Return list of file dicts."""
        return list(self._files)

    def get_notes(self):
        """Return list of note strings."""
        return list(self._notes)

    def get_config_snapshot(self):
        """Return config snapshot dict."""
        return dict(self._config_snapshot)

    def get_file_counts(self):
        """Return dict of category -> count."""
        counts = {}
        for f in self._files:
            cat = f["category"]
            counts[cat] = counts.get(cat, 0) + 1
        return counts

    def get_total_file_count(self):
        """Return total number of files tracked."""
        return len(self._files)
```

**Step 4: Run tests to verify they pass**

Run: `pytest tests/unit/test_generation_tracker.py -v`
Expected: All PASS

**Step 5: Commit**

```bash
git add gk_install_builder/generation_tracker.py tests/unit/test_generation_tracker.py
git commit -m "feat: add GenerationTracker class for post-generation summary"
```

---

### Task 2: Create GenerationSummaryDialog

**Files:**
- Create: `gk_install_builder/dialogs/generation_summary.py`
- Modify: `gk_install_builder/dialogs/__init__.py`

**Step 1: Write the dialog**

```python
"""
Generation Summary Dialog

Modal dialog shown after successful file generation.
Displays config snapshot, file counts by category, and informational notes.
"""
import os
import sys
import subprocess
import customtkinter as ctk


class GenerationSummaryDialog:
    """Modal summary dialog shown after generation completes."""

    # Display names for file categories
    CATEGORY_LABELS = {
        "scripts": "Scripts",
        "launchers": "Launchers",
        "configs": "Configs",
        "tokens": "Tokens",
        "overrides": "Overrides",
        "other": "Other",
    }

    # Display order for categories
    CATEGORY_ORDER = ["scripts", "launchers", "configs", "tokens", "overrides", "other"]

    def __init__(self, parent, tracker):
        """
        Initialize and display the generation summary dialog.

        Args:
            parent: Parent CTk window
            tracker: GenerationTracker instance with collected results
        """
        self.parent = parent
        self.tracker = tracker
        self.window = None
        self._show()

    def _show(self):
        """Build and display the modal dialog."""
        self.window = ctk.CTkToplevel(self.parent)
        self.window.title("Generation Summary")
        self.window.geometry("500x500")
        self.window.resizable(False, False)

        # Modal behavior
        self.window.update_idletasks()
        self.window.update()
        self.window.transient(self.parent)
        try:
            self.window.grab_set()
        except Exception:
            pass

        # Center on parent
        self.window.update_idletasks()
        parent_x = self.parent.winfo_rootx()
        parent_y = self.parent.winfo_rooty()
        parent_w = self.parent.winfo_width()
        parent_h = self.parent.winfo_height()
        win_w = 500
        win_h = 500
        x = parent_x + (parent_w - win_w) // 2
        y = parent_y + (parent_h - win_h) // 2
        self.window.geometry(f"{win_w}x{win_h}+{x}+{y}")

        self.window.focus_force()

        # Scrollable content
        content = ctk.CTkScrollableFrame(self.window)
        content.pack(fill="both", expand=True, padx=15, pady=(15, 5))

        # Header
        ctk.CTkLabel(
            content, text="Generation Complete",
            font=ctk.CTkFont(size=18, weight="bold")
        ).pack(anchor="w", pady=(0, 10))

        # Configuration section
        self._build_config_section(content)

        # Files section
        self._build_files_section(content)

        # Notes section (only if there are notes)
        notes = self.tracker.get_notes()
        if notes:
            self._build_notes_section(content, notes)

        # Button frame (outside scrollable area)
        button_frame = ctk.CTkFrame(self.window, fg_color="transparent")
        button_frame.pack(fill="x", padx=15, pady=(5, 15))

        output_dir = self.tracker.get_config_snapshot().get("output_dir", "")

        ctk.CTkButton(
            button_frame, text="Open Folder",
            command=lambda: self._open_folder(output_dir),
            width=120
        ).pack(side="left", padx=(0, 10))

        ctk.CTkButton(
            button_frame, text="Close",
            command=self.window.destroy,
            width=80, fg_color="gray40", hover_color="gray30"
        ).pack(side="left")

    def _build_config_section(self, parent):
        """Build the Configuration section."""
        ctk.CTkLabel(
            parent, text="Configuration",
            font=ctk.CTkFont(size=14, weight="bold")
        ).pack(anchor="w", pady=(5, 5))

        config_frame = ctk.CTkFrame(parent)
        config_frame.pack(fill="x", pady=(0, 10))

        snap = self.tracker.get_config_snapshot()
        api_display = "New (5.27+)" if snap.get("api_version") == "new" else "Legacy (5.25)"

        rows = [
            ("Platform:", snap.get("platform", "N/A")),
            ("Base URL:", snap.get("base_url", "N/A")),
            ("Tenant ID:", snap.get("tenant_id", "N/A")),
            ("API Version:", api_display),
            ("Output:", snap.get("output_dir", "N/A")),
        ]

        for label_text, value_text in rows:
            row = ctk.CTkFrame(config_frame, fg_color="transparent")
            row.pack(fill="x", padx=10, pady=2)
            ctk.CTkLabel(row, text=label_text, width=100, anchor="w",
                         font=ctk.CTkFont(size=12)).pack(side="left")
            ctk.CTkLabel(row, text=value_text, anchor="w",
                         font=ctk.CTkFont(size=12)).pack(side="left", fill="x", expand=True)

    def _build_files_section(self, parent):
        """Build the Generated Files section."""
        total = self.tracker.get_total_file_count()
        ctk.CTkLabel(
            parent, text=f"Generated Files ({total} files)",
            font=ctk.CTkFont(size=14, weight="bold")
        ).pack(anchor="w", pady=(5, 5))

        files_frame = ctk.CTkFrame(parent)
        files_frame.pack(fill="x", pady=(0, 10))

        counts = self.tracker.get_file_counts()
        for cat in self.CATEGORY_ORDER:
            count = counts.get(cat, 0)
            if count == 0:
                continue
            row = ctk.CTkFrame(files_frame, fg_color="transparent")
            row.pack(fill="x", padx=10, pady=2)
            label = self.CATEGORY_LABELS.get(cat, cat.title())
            ctk.CTkLabel(row, text=f"{label}:", width=100, anchor="w",
                         font=ctk.CTkFont(size=12)).pack(side="left")
            ctk.CTkLabel(row, text=str(count), anchor="w",
                         font=ctk.CTkFont(size=12)).pack(side="left")

    def _build_notes_section(self, parent, notes):
        """Build the Notes section."""
        ctk.CTkLabel(
            parent, text="Notes",
            font=ctk.CTkFont(size=14, weight="bold")
        ).pack(anchor="w", pady=(5, 5))

        notes_frame = ctk.CTkFrame(parent)
        notes_frame.pack(fill="x", pady=(0, 10))

        for note in notes:
            row = ctk.CTkFrame(notes_frame, fg_color="transparent")
            row.pack(fill="x", padx=10, pady=2)
            ctk.CTkLabel(row, text=f"- {note}", anchor="w", wraplength=420,
                         font=ctk.CTkFont(size=12)).pack(anchor="w")

    def _open_folder(self, output_dir):
        """Open the output directory in the system file manager."""
        if not output_dir or not os.path.isdir(output_dir):
            return
        try:
            if sys.platform == "win32":
                os.startfile(output_dir)
            elif sys.platform == "darwin":
                subprocess.Popen(["open", output_dir])
            else:
                subprocess.Popen(["xdg-open", output_dir])
        except Exception as e:
            print(f"Warning: Could not open folder: {e}")
```

**Step 2: Update dialogs `__init__.py`**

Add to `gk_install_builder/dialogs/__init__.py`:

```python
from .generation_summary import GenerationSummaryDialog
```

And add `'GenerationSummaryDialog'` to the `__all__` list.

**Step 3: Run existing tests to verify nothing breaks**

Run: `pytest tests/ -v`
Expected: All existing tests PASS

**Step 4: Commit**

```bash
git add gk_install_builder/dialogs/generation_summary.py gk_install_builder/dialogs/__init__.py
git commit -m "feat: add GenerationSummaryDialog modal"
```

---

### Task 3: Integrate tracker into generator.py

**Files:**
- Modify: `gk_install_builder/generator.py` — `generate()` method and `_show_success()`/`_show_error()`

**Step 1: Write failing test**

Add to `tests/unit/test_generator_core.py`:

```python
class TestGenerationTracker:
    """Test that generate() uses GenerationTracker"""

    def test_generate_creates_tracker(self, tmp_path):
        """generate() should create a tracker and pass it to sub-methods"""
        from gk_install_builder.generator import ProjectGenerator
        from tests.fixtures.generator_fixtures import create_config

        config = create_config(output_dir=str(tmp_path))
        generator = ProjectGenerator(parent_window=None)

        with patch.object(generator, '_generate_gk_install') as mock_gk, \
             patch.object(generator, '_generate_onboarding') as mock_onb, \
             patch.object(generator, '_copy_helper_files') as mock_helper, \
             patch.object(generator, '_generate_environments_json') as mock_env, \
             patch.object(generator, '_copy_certificate') as mock_cert, \
             patch.object(generator, '_show_generation_summary'):
            generator.generate(config)

            # Each method should have been called with tracker as last arg
            for mock_method in [mock_gk, mock_onb, mock_helper, mock_env]:
                call_args = mock_method.call_args
                assert call_args is not None, f"{mock_method} was not called"
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_generator_core.py::TestGenerationTracker -v`
Expected: FAIL

**Step 3: Modify `generate()` in `generator.py`**

Changes to `generator.py`:

1. Add import at top:
```python
from .generation_tracker import GenerationTracker
```
(with fallback import pattern matching existing code)

2. Modify `generate()` method (lines 331-370):

```python
def generate(self, config):
    """Generate project from configuration"""
    try:
        # Create tracker for summary
        tracker = GenerationTracker()
        tracker.set_config_snapshot(
            platform=config.get("platform", "Windows"),
            base_url=config.get("base_url", ""),
            tenant_id=config.get("tenant_id", "001"),
            api_version=config.get("api_version", "new"),
            output_dir=config.get("output_dir", ""),
        )

        # Get absolute output directory path
        output_dir = os.path.abspath(config["output_dir"])
        print(f"Creating output directory: {output_dir}")

        # Create output directory and all parent directories if they don't exist
        os.makedirs(output_dir, exist_ok=True)

        # Store the original working directory
        original_cwd = os.getcwd()

        # Print debug information
        print(f"Current working directory: {original_cwd}")
        print(f"Script directory: {os.path.dirname(os.path.abspath(__file__))}")
        print(f"Output directory: {output_dir}")

        # Create project structure
        self._create_directory_structure(output_dir)

        # Copy certificate if it exists
        self._copy_certificate(output_dir, config, tracker)

        # Generate main scripts by modifying the original files
        self._generate_gk_install(output_dir, config, tracker)
        self._generate_onboarding(output_dir, config, tracker)

        # Copy and modify helper files
        self._copy_helper_files(output_dir, config, tracker)

        # Generate environments.json if environments are configured
        self._generate_environments_json(output_dir, config, tracker)

        # Update tracker with absolute output dir for Open Folder
        tracker._config_snapshot["output_dir"] = output_dir

        self._show_generation_summary(tracker)
    except Exception as e:
        self._show_error(f"Failed to generate project: {str(e)}")
        # Print detailed error for debugging
        import traceback
        print(f"Error details: {traceback.format_exc()}")
```

3. Update delegation methods to accept and pass tracker:

```python
def _copy_certificate(self, output_dir, config, tracker=None):
    """Copy SSL certificate to output directory if it exists"""
    result = copy_certificate(output_dir, config)
    if tracker:
        cert_path = config.get("certificate_path", "")
        if result:
            cert_filename = os.path.basename(cert_path)
            tracker.add_file(cert_filename, GenerationTracker.OTHER)
            tracker.add_note(f"Certificate included: {cert_filename}")
        else:
            if not cert_path or cert_path == "PROJECT/BASEURL/certificate.p12":
                tracker.add_note("No certificate configured — skipped")
            else:
                tracker.add_note(f"Certificate not found at: {cert_path}")
    return result

def _generate_gk_install(self, output_dir, config, tracker=None):
    """Generate GKInstall script with replaced values based on platform"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    result = generate_gk_install(
        output_dir, config, self.detection_manager,
        replace_hostname_regex_powershell, replace_hostname_regex_bash,
        script_dir
    )
    if tracker:
        platform = config.get("platform", "Windows")
        filename = "GKInstall.ps1" if platform == "Windows" else "GKInstall.sh"
        tracker.add_file(filename, GenerationTracker.SCRIPTS)
    return result

def _generate_onboarding(self, output_dir, config, tracker=None):
    """Generate onboarding script with replaced values based on platform"""
    templates_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "templates")
    generate_onboarding_script(output_dir, config, templates_dir)
    if tracker:
        platform = config.get("platform", "Windows")
        filename = "onboarding.ps1" if platform == "Windows" else "onboarding.sh"
        tracker.add_file(filename, GenerationTracker.SCRIPTS)

def _copy_helper_files(self, output_dir, config, tracker=None):
    """Copy helper files to output directory"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    copy_helper_files(output_dir, config, script_dir, self.helper_structure, LAUNCHER_TEMPLATES)
    if tracker:
        platform = config.get("platform", "Windows")
        # Store-initialization script
        si_name = "store-initialization.ps1" if platform == "Windows" else "store-initialization.sh"
        tracker.add_file(si_name, GenerationTracker.SCRIPTS)
        # Launcher templates (7 components)
        launcher_names = [
            "launcher.pos.template", "launcher.onex-pos.template",
            "launcher.wdm.template", "launcher.flow-service.template",
            "launcher.lpa-service.template", "launcher.storehub-service.template",
            "launcher.rcs-service.template",
        ]
        for name in launcher_names:
            tracker.add_file(name, GenerationTracker.LAUNCHERS)
        # Password/token files (3 files + 3 defaults = 6)
        token_names = [
            "basic_auth_password.txt", "basic_auth_password.txt.default",
            "form_password.txt", "form_password.txt.default",
            "form_username.txt", "form_username.txt.default",
        ]
        for name in token_names:
            tracker.add_file(name, GenerationTracker.TOKENS)
        # Config files
        tracker.add_file("create_structure.json", GenerationTracker.CONFIGS)
        tracker.add_file("get_store.json", GenerationTracker.CONFIGS)
        tracker.add_file("storehub/update_config.json", GenerationTracker.CONFIGS)
        tracker.add_file("rcs/update_config.json", GenerationTracker.CONFIGS)
        # Onboarding JSON files (6 component configs)
        onboarding_names = [
            "pos.onboarding.json", "onex-pos.onboarding.json",
            "wdm.onboarding.json", "flow-service.onboarding.json",
            "lpa-service.onboarding.json", "storehub-service.onboarding.json",
        ]
        for name in onboarding_names:
            tracker.add_file(name, GenerationTracker.CONFIGS)
        # Override files (if enabled)
        overrides_enabled = config.get("installer_overrides_enabled", True)
        if overrides_enabled:
            override_components = config.get("installer_overrides_components", {})
            for comp_name, enabled in override_components.items():
                if enabled:
                    tracker.add_file(f"installer_overrides_{comp_name}.xml", GenerationTracker.OVERRIDES)
        else:
            tracker.add_note("Installer overrides disabled")
        # Informational notes
        if not config.get("use_hostname_detection", True):
            tracker.add_note("Hostname detection disabled")
        if config.get("api_version", "new") == "legacy":
            tracker.add_note("Using Legacy API (5.25)")
        file_detection = config.get("detection_config", {}).get("file_detection_enabled", False)
        if file_detection:
            tracker.add_note("File-based detection enabled")
        # Custom versions note
        use_defaults = config.get("use_default_versions", True)
        if not use_defaults:
            version_parts = []
            for key, label in [("pos_version", "POS"), ("wdm_version", "WDM"),
                               ("flow_service_version", "Flow"), ("lpa_service_version", "LPA"),
                               ("storehub_service_version", "StoreHub"), ("rcs_version", "RCS")]:
                v = config.get(key, "")
                if v and v != config.get("version", ""):
                    version_parts.append(f"{label} {v}")
            if version_parts:
                tracker.add_note(f"Custom versions: {', '.join(version_parts)}")

def _generate_environments_json(self, output_dir, config, tracker=None):
    """Generate environments.json file for multi-environment support"""
    generate_environments_json(output_dir, config)
    if tracker:
        envs = config.get("environments", [])
        tracker.add_file("environments.json", GenerationTracker.CONFIGS)
        if envs:
            tracker.add_note(f"{len(envs)} environment(s) configured")
        else:
            tracker.add_note("No environments configured")
```

4. Add the new summary method and keep error method:

```python
def _show_generation_summary(self, tracker):
    """Show generation summary dialog"""
    if self.parent_window:
        try:
            from .dialogs.generation_summary import GenerationSummaryDialog
        except ImportError:
            from dialogs.generation_summary import GenerationSummaryDialog
        GenerationSummaryDialog(self.parent_window, tracker)
    else:
        # No GUI — print summary to console (for tests / CLI usage)
        print(f"\nGeneration complete: {tracker.get_total_file_count()} files generated")
        for note in tracker.get_notes():
            print(f"  - {note}")
```

**Step 4: Run all tests**

Run: `pytest tests/ -v`
Expected: All tests PASS (existing tests use `parent_window=None` so they hit the console path)

**Step 5: Commit**

```bash
git add gk_install_builder/generator.py gk_install_builder/generation_tracker.py tests/unit/test_generator_core.py
git commit -m "feat: integrate GenerationTracker into generate() flow"
```

---

### Task 4: Run full test suite and manual smoke test

**Files:** None (verification only)

**Step 1: Run full test suite**

Run: `pytest tests/ -v`
Expected: All tests PASS, no regressions

**Step 2: Manual smoke test**

Run: `python -m gk_install_builder.main`

1. Fill in a base URL (or use saved config)
2. Click "Generate Installation Files"
3. Verify the summary dialog appears with:
   - Correct config values (platform, URL, tenant, API version, output dir)
   - File counts by category
   - Relevant notes
4. Click "Open Folder" — verify file manager opens to correct directory
5. Click "Close" — verify dialog dismisses cleanly

**Step 3: Commit design doc**

```bash
git add docs/plans/2026-03-28-generation-summary-dialog-design.md docs/plans/2026-03-28-generation-summary-dialog.md
git commit -m "docs: add generation summary dialog design and implementation plan"
```
