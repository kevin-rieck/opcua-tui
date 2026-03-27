from opcua_tui.domain.enums import SessionStatus


def test_session_status_values() -> None:
    assert SessionStatus.DISCONNECTED.value == "disconnected"
    assert SessionStatus.CONNECTING.value == "connecting"
    assert SessionStatus.CONNECTED.value == "connected"
    assert SessionStatus.ERROR.value == "error"


def test_session_status_is_string_enum() -> None:
    assert str(SessionStatus.CONNECTED.value) == "connected"
