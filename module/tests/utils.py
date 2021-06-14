import datetime
from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend


def get_self_signed_cert(key_file):

    with open(key_file) as f:
        key_data = f.read()

    key = serialization.load_pem_private_key(
            key_data.encode('utf-8'), password=None, backend=default_backend()
        )

    subject = issuer = x509.Name([
        x509.NameAttribute(NameOID.COUNTRY_NAME, u"US"),
        x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, u"Illinois"),
        x509.NameAttribute(NameOID.LOCALITY_NAME, u"Chicago"),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, u"test"),
        x509.NameAttribute(NameOID.COMMON_NAME, u"example.com"),
    ])
    cert = x509.CertificateBuilder().subject_name(
        subject
    ).issuer_name(
        issuer
    ).public_key(
        key.public_key()
    ).serial_number(
        x509.random_serial_number()
    ).not_valid_before(
        datetime.datetime.utcnow()
    ).not_valid_after(
        # Our certificate will be valid for 10 days
        datetime.datetime.utcnow() + datetime.timedelta(days=10)
    ).add_extension(
        x509.SubjectAlternativeName([x509.DNSName(u"localhost")]),
        critical=False,
    # Sign our certificate with our private key
    ).sign(key, hashes.SHA256(),  backend=default_backend())

    return cert