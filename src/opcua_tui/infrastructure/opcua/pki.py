from __future__ import annotations

import hashlib
import socket
from dataclasses import dataclass
from pathlib import Path

from asyncua.crypto import cert_gen
from cryptography import x509
from cryptography.hazmat.primitives import serialization
from cryptography.x509.oid import ExtendedKeyUsageOID


@dataclass(slots=True, frozen=True)
class ClientCertificateMaterial:
    certificate_path: Path
    private_key_path: Path
    fingerprint_sha256: str


class ClientPkiStore:
    def __init__(self, root: Path | None = None) -> None:
        self._root = root or Path.home() / ".opcua-tui" / "pki"

    @property
    def root(self) -> Path:
        return self._root

    def ensure_structure(self) -> None:
        for folder in ("own", "trusted", "rejected", "issuers"):
            (self.root / folder).mkdir(parents=True, exist_ok=True)

    async def ensure_client_certificate_material(
        self,
        *,
        certificate_path: str = "",
        private_key_path: str = "",
        app_uri: str = "",
    ) -> ClientCertificateMaterial:
        self.ensure_structure()
        explicit_paths = bool(certificate_path.strip() or private_key_path.strip())

        cert_path, key_path = self._resolve_paths(
            certificate_path=certificate_path,
            private_key_path=private_key_path,
        )
        cert_exists = cert_path.exists()
        key_exists = key_path.exists()

        if cert_exists and key_exists:
            if not explicit_paths:
                # For managed default certs, let asyncua validate/regenerate on URI/validity mismatch.
                await self._generate_client_certificate(
                    key_path=key_path,
                    cert_path=cert_path,
                    app_uri=app_uri.strip() or "urn:opcua-tui:client",
                )
            return ClientCertificateMaterial(
                certificate_path=cert_path,
                private_key_path=key_path,
                fingerprint_sha256=self._sha256_fingerprint(cert_path),
            )

        if cert_exists != key_exists:
            raise ValueError(
                f"Certificate and private key must both exist. cert={cert_path} key={key_path}"
            )

        await self._generate_client_certificate(
            key_path=key_path,
            cert_path=cert_path,
            app_uri=app_uri.strip() or "urn:opcua-tui:client",
        )
        return ClientCertificateMaterial(
            certificate_path=cert_path,
            private_key_path=key_path,
            fingerprint_sha256=self._sha256_fingerprint(cert_path),
        )

    def _resolve_paths(
        self,
        *,
        certificate_path: str,
        private_key_path: str,
    ) -> tuple[Path, Path]:
        cert_raw = certificate_path.strip()
        key_raw = private_key_path.strip()

        if cert_raw and not key_raw:
            raise ValueError("Private key path is required when certificate path is provided.")
        if key_raw and not cert_raw:
            raise ValueError("Certificate path is required when private key path is provided.")

        if cert_raw and key_raw:
            return (Path(cert_raw).expanduser(), Path(key_raw).expanduser())

        return (
            self.root / "own" / "client_certificate.der",
            self.root / "own" / "client_private_key.pem",
        )

    async def _generate_client_certificate(
        self,
        *,
        key_path: Path,
        cert_path: Path,
        app_uri: str,
    ) -> None:
        key_path.parent.mkdir(parents=True, exist_ok=True)
        cert_path.parent.mkdir(parents=True, exist_ok=True)
        await cert_gen.setup_self_signed_certificate(
            key_file=key_path,
            cert_file=cert_path,
            app_uri=app_uri,
            host_name=socket.gethostname(),
            cert_use=[ExtendedKeyUsageOID.CLIENT_AUTH],
            subject_attrs={"commonName": "OPC UA TUI Client"},
        )

    def _sha256_fingerprint(self, certificate_path: Path) -> str:
        raw_bytes = certificate_path.read_bytes()
        if b"-----BEGIN CERTIFICATE-----" in raw_bytes:
            cert = x509.load_pem_x509_certificate(raw_bytes)
            encoded = cert.public_bytes(serialization.Encoding.DER)
        else:
            cert = x509.load_der_x509_certificate(raw_bytes)
            encoded = cert.public_bytes(serialization.Encoding.DER)
        return hashlib.sha256(encoded).hexdigest().upper()
