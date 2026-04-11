from pathlib import Path

import pytest

from opcua_tui.infrastructure.opcua import pki
from opcua_tui.infrastructure.opcua.pki import ClientPkiStore


def test_pki_store_generates_and_reuses_material(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    calls: list[tuple[Path, Path]] = []

    def fake_generate(self, *, key_path: Path, cert_path: Path) -> None:
        calls.append((key_path, cert_path))
        key_path.write_text("-----BEGIN PRIVATE KEY-----\nfake\n-----END PRIVATE KEY-----\n")
        cert_path.write_bytes(b"fake-cert")

    monkeypatch.setattr(pki.ClientPkiStore, "_generate_client_certificate", fake_generate)
    monkeypatch.setattr(
        pki.ClientPkiStore, "_sha256_fingerprint", lambda *_args, **_kwargs: "ABC123"
    )

    store = ClientPkiStore(root=tmp_path / "pki")
    first = store.ensure_client_certificate_material()
    second = store.ensure_client_certificate_material()

    assert first.certificate_path.exists()
    assert first.private_key_path.exists()
    assert first.fingerprint_sha256 == "ABC123"
    assert second.certificate_path == first.certificate_path
    assert second.private_key_path == first.private_key_path
    assert calls == [(first.private_key_path, first.certificate_path)]


def test_pki_store_rejects_half_provided_paths(tmp_path: Path) -> None:
    store = ClientPkiStore(root=tmp_path / "pki")

    with pytest.raises(ValueError, match="Private key path is required"):
        store.ensure_client_certificate_material(certificate_path="client.der")

    with pytest.raises(ValueError, match="Certificate path is required"):
        store.ensure_client_certificate_material(private_key_path="client.key")
