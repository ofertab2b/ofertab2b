#!/usr/bin/env python3
"""
Script para generar certificados SSL auto-firmados.
Ejecutar con: python generate_certs.py
"""

import os
from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
from datetime import datetime, timedelta, timezone

def generate_certificates(hostname='pel5cd229bqsm', days=365):
    """Genera certificados SSL auto-firmados."""
    
    base_dir = os.path.dirname(__file__)
    cert_path = os.path.join(base_dir, 'cert.pem')
    key_path = os.path.join(base_dir, 'key.pem')
    
    print(f"Generando certificados SSL auto-firmados...")
    print(f"Hostname: {hostname}")
    print(f"Válido por: {days} días")
    
    # Generar clave privada
    print("Generando clave privada (RSA 2048)...")
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
        backend=default_backend()
    )
    
    # Crear certificado auto-firmado
    print("Creando certificado auto-firmado...")
    subject = issuer = x509.Name([
        x509.NameAttribute(NameOID.COUNTRY_NAME, u"US"),
        x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, u"State"),
        x509.NameAttribute(NameOID.LOCALITY_NAME, u"City"),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, u"My Org"),
        x509.NameAttribute(NameOID.COMMON_NAME, hostname),
    ])
    
    cert = x509.CertificateBuilder().subject_name(
        subject
    ).issuer_name(
        issuer
    ).public_key(
        private_key.public_key()
    ).serial_number(
        x509.random_serial_number()
    ).not_valid_before(
        datetime.now(timezone.utc)
    ).not_valid_after(
        datetime.now(timezone.utc) + timedelta(days=days)
    ).add_extension(
        x509.SubjectAlternativeName([
            x509.DNSName(hostname),
            x509.DNSName(u"localhost"),
            x509.DNSName(u"127.0.0.1"),
        ]),
        critical=False,
    ).sign(private_key, hashes.SHA256(), default_backend())
    
    # Guardar la clave privada
    print(f"Guardando clave privada en: {key_path}")
    with open(key_path, "wb") as f:
        f.write(private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption()
        ))
    
    # Guardar el certificado
    print(f"Guardando certificado en: {cert_path}")
    with open(cert_path, "wb") as f:
        f.write(cert.public_bytes(serialization.Encoding.PEM))
    
    print("\n✓ Certificados generados correctamente")
    print(f"  Certificado: {cert_path}")
    print(f"  Clave privada: {key_path}")
    print(f"\nPuedes acceder a la aplicación en: https://{hostname}:5000/")
    print("Nota: El navegador mostrará una advertencia de seguridad porque el certificado es auto-firmado.")

if __name__ == '__main__':
    generate_certificates()
