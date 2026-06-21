"""Generate a self-signed TLS cert valid for the local WiFi (en0) IP."""
import datetime
import ipaddress
import socket
import sys
from pathlib import Path

import netifaces
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID

ROOT = Path(__file__).parent.parent

def _local_ip() -> str:
    try:
        addrs = netifaces.ifaddresses("en0")
        return addrs[netifaces.AF_INET][0]["addr"]
    except (KeyError, ValueError, OSError):
        pass
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]
    except Exception:
        return "127.0.0.1"
    finally:
        s.close()

def generate(cert_path: Path, key_path: Path) -> str:
    local_ip = _local_ip()

    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)

    subject = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, local_ip)])
    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(subject)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime.datetime.now(datetime.timezone.utc))
        .not_valid_after(datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=365))
        .add_extension(
            x509.SubjectAlternativeName([
                x509.IPAddress(ipaddress.IPv4Address(local_ip)),
                x509.IPAddress(ipaddress.IPv4Address("127.0.0.1")),
                x509.DNSName("localhost"),
            ]),
            critical=False,
        )
        .sign(key, hashes.SHA256())
    )

    key_path.write_bytes(
        key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.TraditionalOpenSSL,
            serialization.NoEncryption(),
        )
    )
    cert_path.write_bytes(cert.public_bytes(serialization.Encoding.PEM))
    return local_ip

if __name__ == "__main__":
    cert_file = ROOT / "cert.pem"
    key_file  = ROOT / "key.pem"
    ip = generate(cert_file, key_file)
    print(f"Certificate generated → {cert_file}  (IP: {ip})")
