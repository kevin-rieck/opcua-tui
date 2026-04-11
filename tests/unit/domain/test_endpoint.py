from opcua_tui.domain.endpoint import sanitize_endpoint


def test_sanitize_endpoint_redacts_userinfo() -> None:
    value = sanitize_endpoint("opc.tcp://user:pass@localhost:4840")
    assert value == "opc.tcp://***@localhost:4840"


def test_sanitize_endpoint_keeps_plain_endpoint() -> None:
    value = sanitize_endpoint("opc.tcp://localhost:4840")
    assert value == "opc.tcp://localhost:4840"
