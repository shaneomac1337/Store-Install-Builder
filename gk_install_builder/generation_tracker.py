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
            text: Note message (e.g. "No certificate configured -- skipped")
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
