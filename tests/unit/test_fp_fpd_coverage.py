"""Regression: every component must be dispatched in every FP/FPD parsing site.

Catches the class of bug where a new component is added to the components list
but the property-name dispatch is forgotten in the FP/FPD parsers (the bug that
hit RCS-SERVICE silently from commit 2d34ba7 onward).
"""
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[2]
PS1_TEMPLATE = REPO_ROOT / "gk_install_builder" / "templates" / "GKInstall.ps1.template"
SH_TEMPLATE = REPO_ROOT / "gk_install_builder" / "templates" / "GKInstall.sh.template"
API_CLIENT = REPO_ROOT / "gk_install_builder" / "integrations" / "api_client.py"


COMPONENT_PROPERTIES = {
    "POS": ("POSClient_Version", "POSClient_Update_Version"),
    "ONEX-POS": ("OneX_Version", "OneX_Update_Version"),
    "WDM": ("WDM_Version", "WDM_Update_Version"),
    "FLOW-SERVICE": ("FlowService_Version", "FlowService_Update_Version"),
    "LPA-SERVICE": ("LPA_Version", "LPA_Update_Version"),
    "STOREHUB-SERVICE": ("StoreHub_Version", "SH_Update_Version"),
    "RCS-SERVICE": ("RCS_Version", "RCS_Update_Version"),
    "MQTT-BROKER": ("StoreMQTTBroker_Version", "StoreMQTTBroker_Update_Version"),
}


# (site_name, file_path, anchor_phrase, end_phrase) — slice the file between the
# anchor (start of the FP or FPD parsing block) and the end phrase (end of that
# block). The slice is used as the search corpus for property-name presence.
DISPATCH_SITES = [
    (
        "PS1 FP",
        PS1_TEMPLATE,
        "Step 1: Try FP scope first",
        'Write-Host "Found $($versions.Count) components in FP scope"',
    ),
    (
        "PS1 FPD",
        PS1_TEMPLATE,
        "Step 2: For components not found in FP, try FPD scope",
        "Found additional $($versions.Count",
    ),
    (
        "SH FP",
        SH_TEMPLATE,
        "Step 1: Try FP scope first (modified/customized versions)",
        'Found $COMPONENT_TYPE version in FP scope',
    ),
    (
        "SH FPD",
        SH_TEMPLATE,
        "Step 2: If not found in FP, try FPD scope",
        'Found $COMPONENT_TYPE version in FPD scope',
    ),
    (
        "Py FP",
        API_CLIENT,
        "# Step 1: Try FP scope first",
        "# Step 2: For components not found in FP, try FPD scope",
    ),
    (
        "Py FPD",
        API_CLIENT,
        "# Step 2: For components not found in FP, try FPD scope",
        "loading_dialog.destroy()",
    ),
]


def _slice(file_path: Path, start_phrase: str, end_phrase: str) -> str:
    text = file_path.read_text(encoding="utf-8")
    start = text.find(start_phrase)
    if start == -1:
        raise AssertionError(
            f"Could not find start anchor in {file_path.name}: {start_phrase!r}"
        )
    end = text.find(end_phrase, start)
    if end == -1:
        raise AssertionError(
            f"Could not find end anchor in {file_path.name}: {end_phrase!r}"
        )
    return text[start:end]


@pytest.mark.parametrize("site,path,start_phrase,end_phrase", DISPATCH_SITES)
@pytest.mark.parametrize("component,props", list(COMPONENT_PROPERTIES.items()))
def test_dispatch_site_handles_component(
    site, path, start_phrase, end_phrase, component, props
):
    """Each FP/FPD dispatch block must reference both property names per component."""
    block = _slice(path, start_phrase, end_phrase)
    missing = [prop for prop in props if prop not in block]
    assert not missing, (
        f"Site '{site}' is missing property dispatch for component "
        f"{component!r}: {missing!r}. Add a switch/case/elif branch in "
        f"{path.name} between anchors {start_phrase!r} and {end_phrase!r}."
    )


def test_mqtt_broker_in_versions_init():
    """MQTT-BROKER must appear in the versions init dict in api_client.py."""
    source = API_CLIENT.read_text(encoding="utf-8")
    assert '"MQTT-BROKER": {"value": None, "source": None}' in source


def test_mqtt_broker_property_ids_dispatched():
    """Both FP and FPD property IDs for MQTT Broker must appear in api_client.py."""
    source = API_CLIENT.read_text(encoding="utf-8")
    assert "StoreMQTTBroker_Version" in source
    assert "StoreMQTTBroker_Update_Version" in source


def test_mqtt_broker_in_config_service_system_types():
    """MQTT-BROKER must be present in the Config-Service system_types dict."""
    source = API_CLIENT.read_text(encoding="utf-8")
    assert "mqtt_broker_system_type" in source
    assert "GKR-Store-MQTT-Broker" in source
