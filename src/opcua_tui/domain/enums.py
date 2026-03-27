from enum import Enum


class SessionStatus(str, Enum):
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    ERROR = "error"


class SecurityMode(str, Enum):
    NONE = "none"
    SIGN = "sign"
    SIGN_AND_ENCRYPT = "sign-and-encrypt"


class SecurityPolicy(str, Enum):
    NONE = "none"
    BASIC128RSA15 = "basic128rsa15"
    BASIC256 = "basic256"
    BASIC256SHA256 = "basic256sha256"
    AES128_SHA256_RSAOAEP = "aes128_sha256_rsaoaep"
    AES256_SHA256_RSAPSS = "aes256_sha256_rsapss"


class AuthenticationMode(str, Enum):
    ANONYMOUS = "anonymous"
    USERNAME_PASSWORD = "username_password"
    CERTIFICATE = "certificate"
