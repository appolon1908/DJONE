"""Isolated safety regression tests. No native process, socket or provider runs."""
import importlib.util
import io
import json
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi import HTTPException

ROOT = Path(__file__).resolve().parents[1]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


bridge = load("djone_bridge_synthetic_test", "services/mixxx-bridge/app/main.py")
native = load("djone_native_synthetic_test", "native/mixxx_adapter.py")


def command():
    return bridge.Command(command_id="synthetic", action="play", deck=1, value=True)


def test_bridge_database_failure_closes_every_execution_gate():
    with patch.object(bridge.psycopg, "connect", side_effect=RuntimeError("synthetic unavailable database")):
        assert bridge.safety() == {"execution_enabled": False, "emergency_stop": True, "certified": False}


@pytest.mark.parametrize("state,status", [
    ({"execution_enabled": True, "emergency_stop": True, "certified": True}, 423),
    ({"execution_enabled": True, "emergency_stop": False, "certified": False}, 423),
])
def test_emergency_stop_and_missing_certification_prevent_native_calls(state, status):
    with patch.object(bridge, "TOKEN", "synthetic-test"), \
            patch.object(bridge, "safety", return_value=state), \
            patch.object(bridge, "native") as transport:
        with pytest.raises(HTTPException) as raised:
            bridge.execute(command(), x_bridge_token="synthetic-test")
        assert raised.value.status_code == status
        transport.assert_not_called()


def test_disabled_execution_never_reaches_native_transport():
    with patch.object(bridge, "TOKEN", "synthetic-test"), \
            patch.object(bridge, "safety", return_value={
                "execution_enabled": False, "emergency_stop": False, "certified": True}), \
            patch.object(bridge, "native") as transport:
        result = bridge.execute(command(), x_bridge_token="synthetic-test")
        assert result["executed"] is False
        assert result["accepted"] is False
        transport.assert_not_called()


def test_bridge_rejects_missing_credentials_before_database_or_transport():
    with patch.object(bridge, "TOKEN", ""), \
            patch.object(bridge, "safety") as safety, \
            patch.object(bridge, "native") as transport:
        with pytest.raises(HTTPException) as raised:
            bridge.execute(command(), x_bridge_token=None)
        assert raised.value.status_code == 401
        safety.assert_not_called()
        transport.assert_not_called()


def test_bridge_health_probe_is_read_only_and_does_not_claim_native_readiness():
    with patch.object(bridge, "native", return_value={"ok": False}) as transport, \
            patch.object(bridge, "safety", return_value={
                "execution_enabled": False, "emergency_stop": True, "certified": False}):
        result = bridge.health()
        transport.assert_called_once_with({"op": "get", "deck": 1, "control": "play"})
        assert result["native_reachable"] is False
        assert result["transport_ready"] is False
        assert result["execution_enabled"] is False


def request_native(payload, token="synthetic-test", destination=None):
    handler = object.__new__(native.Handler)
    handler.rfile = io.BytesIO((json.dumps(payload) + "\n").encode())
    handler.wfile = io.BytesIO()
    with patch.object(native, "TOKEN", token), \
            patch.object(native, "midi_dest", return_value=destination) as midi, \
            patch.object(native.subprocess, "check_output", side_effect=AssertionError("No real MIDI process")):
        handler.handle()
    return json.loads(handler.wfile.getvalue()), midi.call_count


def test_native_missing_token_is_rejected_before_hardware_discovery():
    result, calls = request_native({"op": "state"}, token="")
    assert result == {"ok": False, "error": "unauthorized"}
    assert calls == 0


def test_native_unknown_operation_is_rejected_before_hardware_discovery():
    result, calls = request_native({"op": "shell", "token": "synthetic-test"})
    assert result["error"] == "unsupported"
    assert calls == 0


def test_native_missing_mapping_never_executes_a_command():
    result, _ = request_native({"op": "command", "action": "play", "deck": 1, "token": "synthetic-test"})
    assert result["error"] == "mixxx_mapping_not_connected"
    assert result["executed"] is False


def test_discovered_mapping_is_still_not_execution_certification():
    result, _ = request_native({"op": "command", "action": "play", "deck": 1,
                                "token": "synthetic-test"}, destination="48:0")
    assert result["error"] == "mapping_not_certified"
    assert result["executed"] is False
