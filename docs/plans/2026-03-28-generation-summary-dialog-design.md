# Generation Summary Dialog — Design

**Date:** 2026-03-28
**Branch:** feature/system-services
**Approach:** B — Summary Dialog with Generation Tracker

## Problem

After clicking "Generate Installation Files", users receive no meaningful feedback. The current `_show_success()` creates a `CTkInputDialog` and immediately destroys it, so it's effectively invisible. Technical consultants using the tool want confirmation that generation succeeded and a quick summary of what was produced.

## Solution

Two components:

### 1. GenerationTracker

A lightweight collector class that generation steps report into during `generate()`.

**Tracks:**
- **Files generated** — path + category (scripts, launchers, configs, tokens, overrides, other)
- **Info notes** — contextual observations with type (info or notice)
- **Config snapshot** — key values used during generation (platform, base URL, tenant, API version, output dir)

**Flow:**
1. `generate()` creates a `GenerationTracker` instance
2. Passes it to each `_generate_*` and `_copy_*` method
3. Each method calls `tracker.add_file(filename, category)` and `tracker.add_note(text)` alongside existing `print()` statements
4. After all steps complete, `generate()` passes the tracker to the summary dialog

**File categories:**
- `scripts` — GKInstall, onboarding, store-initialization
- `launchers` — 7 component launcher templates
- `configs` — JSON configs (onboarding, init, structure, environments)
- `tokens` — password/credential files
- `overrides` — installer override XMLs
- `other` — certificate, any uncategorized files

### 2. Summary Dialog

A modal `CTkToplevel` window (`dialogs/generation_summary.py`) shown after successful generation.

**Layout (top to bottom):**
- Header: "Generation Complete"
- Configuration section: platform, base URL, tenant ID, API version, output directory
- Generated Files section: file counts grouped by category, total count
- Notes section (conditional — hidden when empty): informational notes
- Action buttons: "Open Folder" + "Close"

**Size:** ~500x500, centered on parent, scrollable if content overflows.

**Open Folder action:** `os.startfile()` on Windows, `subprocess.Popen(["xdg-open", path])` on Linux.

### Note Generation Logic

Principle: silent on defaults, noted on deviations or skips.

| Condition | Note |
|-----------|------|
| Certificate copied | "Certificate included: certificate.p12" |
| No certificate configured | "No certificate configured — skipped" |
| N environments configured | "{N} environments configured" |
| No environments | "No environments configured" |
| Installer overrides disabled | "Installer overrides disabled" |
| Hostname detection disabled | "Hostname detection disabled" |
| API version is legacy | "Using Legacy API (5.25)" |
| File detection enabled | "File-based detection enabled" |
| Custom component versions set | "Custom versions: POS v5.27.1, WDM v5.26.0" |

Defaults (overrides enabled, hostname detection enabled, new API, default versions) produce no notes.

## Files Changed

**New files:**
- `gk_install_builder/generation_tracker.py` — GenerationTracker class
- `gk_install_builder/dialogs/generation_summary.py` — Summary dialog

**Modified files (minimal changes):**
- `gk_install_builder/generator.py` — create tracker in `generate()`, pass to steps, show dialog at end
- `gk_install_builder/generators/gk_install_generator.py` — add tracker.add_file() calls
- `gk_install_builder/generators/helper_file_generator.py` — add tracker.add_file() and tracker.add_note() calls
- `gk_install_builder/generators/launcher_generator.py` — add tracker.add_file() calls
- `gk_install_builder/generators/onboarding_generator.py` — add tracker.add_file() calls
- `gk_install_builder/utils/file_operations.py` — add tracker.add_file() for certificate copy

## Risk Assessment

**Low risk.** Changes are additive:
- Generation logic unchanged — same sequence, same file creation, same error handling
- Tracker parameter is optional (defaults to None) — if omitted, generation works exactly as before
- Existing tests unaffected — generation behavior is identical
- New tests cover tracker and dialog independently

## Non-Goals

- Live progress during generation (generation is < 1 second)
- Detailed per-file content preview
- Export/save summary to file (can be added later if needed)
