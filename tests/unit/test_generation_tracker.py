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
