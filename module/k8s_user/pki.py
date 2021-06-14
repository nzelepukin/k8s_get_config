from typing import Optional, Dict, List, Any
from datetime import datetime, timezone
import base64
import collections
from cryptography import x509
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import serialization


NAME_ATTRIBUTE_MAPING = {
    "O": NameOID.ORGANIZATION_NAME,
    "OU": NameOID.ORGANIZATIONAL_UNIT_NAME,
    "CN": NameOID.COMMON_NAME,
    "C": NameOID.COUNTRY_NAME,
    "ST": NameOID.STATE_OR_PROVINCE_NAME,
    "L": NameOID.LOCALITY_NAME,
    "STREET": NameOID.STREET_ADDRESS,
    "SN": NameOID.SURNAME,
    "GN": NameOID.GIVEN_NAME,
    "T": NameOID.TITLE,
    "DC": NameOID.DOMAIN_COMPONENT,
    "UID": NameOID.USER_ID,
}


KeyBundle = collections.namedtuple("KeyBundle", "user_name user_key user_csr user_cert")


class Key:
    """A wrapper object to manage a Key

    This can be used to generate a Key or it can be used to load
    and act upon an existing Key.
    """

    def __init__(
        self,
        key_size: Optional[int] = 4092,
        key_data: Optional[bytes] = None,
        key_file: Optional[str] = None,
        key_file_password: Optional[str] = None,
    ):
        """
        :param key_size: the size of the RSA key generated. Defaults to 4092
        :param key_data: an optional bytestring of an existing PEM key. If provided,
            a new key will not be generated.
        :param key_file: an optional filesystem path to an existing PEM key. If provided,
            a new key will not be generated.
        :param key_password: an optional encryption password for the key_file if the key_file
            attribute is provided.
        """
        self.created = False
        self.key_size = key_size
        self.key_data = key_data
        self.key_file = key_file
        self.key_file_password = key_file_password

        if self.key_file or self.key_data:
            self.load()
        else:
            self.generate()
            self.created = True

    def load_data(self, key_data: bytes, password: Optional[str] = None) -> Any:
        """Load a Key from a PEM-formatted byte string
        
        :param key_data: a byte string of Key data in PEM format
        :returns: a key object
        """
        private_key = serialization.load_pem_private_key(
            key_data, password=password, backend=default_backend()
        )
        return private_key

    def load_file(self, path: str, password: Optional[str] = None) -> Any:
        """Load a Key from a PEM file
        
        :param path: a filesystem path to a PEM Key file
        :param password: an optional password to decrypt the key
        :returns: a key object
        """
        with open(path, "rb") as f:
            return self.load_data(f.read(), password=password)

    def load(self):
        """Loads a Key object based on key_data or key_file attribute"""
        if self.key_data:
            self.key = self.load_data(
                key_data=self.key_data, password=self.key_file_password
            )
        elif self.key_file:
            self.key = self.load_file(
                path=self.key_file, password=self.key_file_password
            )
        else:
            raise ValueError("Must supply key_data or key_file")

    def generate(self):
        """Generate a Key based on this object's attributes"""
        self.key = rsa.generate_private_key(
            public_exponent=65537, key_size=self.key_size, backend=default_backend()
        )

    @property
    def base64(self) -> str:
        """Return a base64-encoded representation of this Key."""
        return base64.b64encode(self.pem).decode("utf-8")

    @property
    def pem(self) -> str:
        """Return a PEM representation of this Key."""
        return self.key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption(),
        )

    def save(self, path: str):
        """Save a PEM representation of this Key to the provided path"""
        with open(path, "wb") as f:
            f.write(self.pem)


class CSR:
    """A wrapper object to manage a CSR

    This can be used to generate a CSR or it can be used to load
    and act upon an existing CSR.
    """

    def __init__(
        self,
        key: Key,
        common_name: str,
        additional_subject: Optional[Dict] = None,
        dnsnames: Optional[Dict] = None,
        csr_data: Optional[bytes] = None,
        csr_file: Optional[str] = None,
        signing_hash_algo: Optional[Any] = None,
    ):
        """
        :param key: a pki.Key object to associate with this CSR.
        :param common_name: The Common Name (CN) for the certificate
        :param additional_subject: a dictionary where the keys are the x509 subject
            attributes from cryptography.x509.NameOID OR a short name abbreviation
            for those attributes. See the NAME_ATTRIBUTE_MAPING above.
        :param dnsnames: a list of Subject Alternative Name (SAN) DNS names.
        :param csr_data: an optional bytestring containing an existing PEM CSR. If
            this is specified, a key must be provided as well that matches this CSR.
            If this is given, a CSR will not be generated, but the provided on will be
            used.
        :param csr_file: an optional filesystem path to an existing PEM CSR. If this
            is specified, a key must be provided as well that matches this CSR.
            If this is given, a CSR will not be generated, but the provided one will be
            used.
        :param signing_hash_algo: a hash algorithm to sign the key with. Default is
            hashes.SHA256
        """
        self.created = False
        self.key = key
        self.csr_data = csr_data
        self.csr_file = csr_file
        self.signing_hash_algo = (
            signing_hash_algo if signing_hash_algo else hashes.SHA256
        )

        if not additional_subject:
            additional_subject = {}
        self.attribue_list = [x509.NameAttribute(NameOID.COMMON_NAME, common_name)] + [
            x509.NameAttribute(NAME_ATTRIBUTE_MAPING.get(a, a), v)
            for a, v in additional_subject.items()
        ]

        if not dnsnames:
            dnsnames = {}
        self.dnsnames = dnsnames

        if self.csr_file or self.csr_data:
            self.load()
        else:
            self.generate()
            self.created = True

    def load_data(self, csr_data: bytes) -> Any:
        """Load a CSR from a PEM-formatted byte string
        
        :param csr_data: a byte string of CSR data in PEM format
        :returns: a csr object
        """
        csr = x509.load_pem_x509_csr(csr_data, backend=default_backend())
        return csr

    def load_file(self, path: str) -> Any:
        """Load a CSR from a PEM file
        
        :param path: a filesystem path to a PEM CSR file
        :returns: a csr object
        """
        with open(path, "rb") as f:
            return self.load_data(f.read())

    def load(self):
        """Loads a CSR object based on csr_data or csr_file attribute"""
        if self.csr_data:
            self.csr = self.load_data(csr_data=self.csr_data)
        elif self.csr_file:
            self.csr = self.load_file(path=self.csr_file)
        else:
            raise ValueError("Must supply csr_data or csr_file")

    def generate(self):
        """Generate a CSR based on this object's attributes"""
        self.csr = (
            x509.CertificateSigningRequestBuilder()
            .subject_name(x509.Name(self.attribue_list))
            .add_extension(x509.SubjectAlternativeName(self.dnsnames), critical=False,)
            .sign(self.key.key, self.signing_hash_algo(), default_backend())
        )

    @property
    def subject(self) -> str:
        """Return a subject string based on this object's attributes"""
        return self.csr.subject.rfc4514_string()

    @property
    def pem(self) -> str:
        """Return a PEM representation of this CSR."""
        return self.csr.public_bytes(serialization.Encoding.PEM)

    @property
    def base64(self) -> str:
        """Return a base64-encoded representation of this CSR."""
        return base64.b64encode(self.pem).decode("utf-8")

    def save(self, path: str):
        """Save a PEM representation of this CSR to the provided path"""
        with open(path, "wb") as f:
            f.write(self.pem)


class Cert:
    """A wrapper object to manage a Cert

    This can be used to load and act upon an existing Cert.
    """

    def __init__(
        self, crt_data: Optional[bytes] = None, crt_file: Optional[str] = None
    ):
        """
        :param crt_data: an optional bytestring containing an existing PEM Cert
        :param crt_file: an optional filesystem path to an existing PEM Cert.
            used.
        """
        self.load(crt_data, crt_file)

    def load_data(self, crt_data: bytes) -> Any:
        """Load a Cert from a PEM-formatted byte string
        
        :param crt_data: a byte string of Cert data in PEM format
        :returns: a cert object
        """
        return x509.load_pem_x509_certificate(crt_data, default_backend())

    def load_file(self, path: str) -> Any:
        """Load a Cert from a PEM file
        
        :param path: a filesystem path to a PEM Cert file
        :returns: a cert object
        """
        with open(path, "rb") as f:
            return self.load_data(f.read())

    def load(self, crt_data: Optional[bytes] = None, crt_file: Optional[str] = None):
        """Loads a Cert object based on crt_data or crt_file attribute"""
        if crt_data:
            self.crt = self.load_data(crt_data)
        elif crt_file:
            self.crt = self.load_file(path=crt_file)
        else:
            self.crt = None

    @property
    def pem(self) -> str:
        """Return a PEM representation of this Cert."""
        return self.crt.public_bytes(serialization.Encoding.PEM)

    @property
    def base64(self) -> str:
        """Return a base64-encoded representation of this Cert."""
        return base64.b64encode(self.pem).decode("utf-8")

    @property
    def subject(self) -> str:
        """Return a subject string based on this object's attributes"""
        return self.crt.subject.rfc4514_string()

    def save(self, path: str):
        """Save a PEM representation of this Cert to the provided path"""
        with open(path, "wb") as f:
            f.write(self.pem)


class CSRandKey:
    """A wrapper object to hold both a related CSR and Key

    This can be used to generate a Key and CSR, or it can be used to load
    and act upon an existing Key and CSR.
    """

    def __init__(
        self,
        common_name,
        additional_subject: Optional[Dict] = None,
        dnsnames: Optional[Dict] = None,
        key_size: Optional[int] = 4092,
        key_file: Optional[str] = None,
        key_file_password: Optional[str] = None,
        csr_file: Optional[str] = None,
    ):
        """
        :param common_name: The Common Name (CN) for the certificate
        :param additional_subject: a dictionary where the keys are the x509 subject
            attributes from cryptography.x509.NameOID OR a short name abbreviation
            for those attributes. See the NAME_ATTRIBUTE_MAPING above.
        :param dnsnames: a list of Subject Alternative Name (SAN) DNS names.
        :param key_size: the size of the RSA key generated. Defaults to 4092
        :param key_file: an optional filesystem path to an existing PEM RSA key.
            Only use this when you wish to use an existing key. If you want
            to generate a new one, leave this empty.
        :param key_password: an optional encryption password for the key_file if the key_file
            attribute is provided.
        :param csr_file: an optional filesystem path to an existing PEM CSR. If this
            is specified, a key_file must be provided as well that matches this CSR.
            If this is given, a CSR will not be generated, but the provided one will be
            used.
        """
        self.key = Key(
            key_size=key_size, key_file=key_file, key_file_password=key_file_password,
        )
        self.csr = CSR(
            key=self.key,
            common_name=common_name,
            additional_subject=additional_subject,
            dnsnames=dnsnames,
            csr_file=csr_file,
        )
