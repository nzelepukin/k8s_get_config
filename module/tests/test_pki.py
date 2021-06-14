import os
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend
from cryptography.x509 import CertificateSigningRequest
from cryptography.hazmat.primitives.asymmetric.rsa import RSAPrivateKey
from k8s_user.pki import CSRandKey, CSR, Key, Cert

FIXTURE_DIR = os.path.join(
    os.path.dirname(os.path.realpath(__file__)),
    'fixtures',
    )

def test__key__init():
    k = Key()
    private_key = serialization.load_pem_private_key(
            k.pem,
            password=None,
            backend=default_backend()
        )
    assert k.key.private_numbers().q == private_key.private_numbers().q
    assert k.key.private_numbers().q == private_key.private_numbers().q


def test__key__load__from_file():
    k = Key(key_file=os.path.join(FIXTURE_DIR, "01_crypto_key.pem"))
    assert isinstance(k.key, RSAPrivateKey)
    assert (k.key.private_numbers().q ==
            144297355258033432961864249587566476417513395433306785930002598799109052058830086122084681049876654212847918251721493275668666135181801876080277008509389732804065133754794433634493195096633781919315478959132232587747522900893559497688267541882710926783531946921083827536107483831548399710096915589910119439697)
    assert (k.key.private_numbers().p ==
            155077597940994614685764714448196016481909530132221791492830636731403171936034167712684220338148449908312644390351813791630716591276752117103135699908938691335706645010018715863379137684598697481255169748674781389790109894698488651804364689336883691051597751748383115970680207826187946147682102388504221500771)


def test__key__generate():
    k = Key()
    assert not k.key_data
    assert not k.key_file
    assert isinstance(k.key, RSAPrivateKey)


def test__key__pem():
    k = Key()
    assert k.pem.decode("utf-8").startswith(
        "-----BEGIN RSA PRIVATE KEY-----")
    assert k.pem.decode("utf-8").endswith(
        "-----END RSA PRIVATE KEY-----\n")


def test__key__key_size():
    k = Key(key_size=2048)
    assert k.key.key_size == 2048


def test__key__save(tmp_path):
    k = Key()
    save_key = tmp_path / "key.pem"
    save_key.write_text("")
    k.save(path=save_key)

    with open(save_key) as f:
        k_from_file = serialization.load_pem_private_key(
                f.read().encode('utf-8'),
                password=None,
                backend=default_backend()
            )
        assert k.key.private_numbers().q == k_from_file.private_numbers().q
        assert k.key.private_numbers().q == k_from_file.private_numbers().q


def test__csr__init__key_match_csr_pubkey():
    k = Key()
    c = CSR(key=k, common_name="joe")
    assert (
        k.key.public_key().public_numbers().n ==
        c.csr.public_key().public_numbers().n
    )


def test__csr__load__from_file():
    k = Key(key_file=os.path.join(FIXTURE_DIR, "test04.key.pem"))
    cc = CSR(
        key=k,
        common_name="joe",
        csr_file=os.path.join(FIXTURE_DIR, "test04.csr.pem"))
    assert isinstance(cc.csr, CertificateSigningRequest)
    assert cc.csr.public_key().public_numbers().n == 47697849059556405225747884313444170230030763816433424631631373035711182936368092649968208614416434022706607776706324413502341646317728827547598067098252623604160016708295920244436964094624216727598081805820171341579513988264184396479085413667959684451333717475411285092373155692928873455930722519946733243885198520393782085591298880494985667255726797562061384487642807064782445358954937287712299058062046560400309940827255822634838060272875179078009131074978614249938179755360975280671537534506114111380505615383103391819800386789809167326284319333814600623689721087222405250502813469759449422767530797497646722237196915919525305165416484479205320285164625866942224505136347391509813145384639803900734490703721063552632775563762971875368305794470978647770107216064397414692148379270363411512853466501343962894822538634363330537679807995968768407745496270487574977770291585894697235327603924041831173934111279292064391522446476633459734055630905561810936892196777410004514290786614793639818503079345991842899845903465235429185309458399354358565380517620947176121344242378629202349277826925156970347574030013644291109396127155790643428605001831430439957635533484191537871485301724854443550268456964714674197789858655962524737938114211
    assert cc.csr.is_signature_valid


def test__csr__generate():
    k = Key()
    cc = CSR(
        key=k,
        common_name="joe",)
    assert not cc.csr_file
    assert not cc.csr_data
    assert isinstance(cc.csr, CertificateSigningRequest)
    assert cc.csr.is_signature_valid


@pytest.mark.parametrize("cn,additional_subject,expected", 
[
    pytest.param("joe", None, "CN=joe"),
    pytest.param("joe", {"O": "corp"}, "O=corp,CN=joe"),
    pytest.param("joe", {"OU": "IT"}, "OU=IT,CN=joe"),
    pytest.param("joe", {"C": "US"}, "C=US,CN=joe"),
    pytest.param("joe", {"ST": "IL"}, "ST=IL,CN=joe"),
    pytest.param("joe", {"L": "Chicago"}, "L=Chicago,CN=joe"),
    pytest.param("joe", {"SN": "Doe"}, "2.5.4.4=Doe,CN=joe"),
    pytest.param("joe", {"GN": "Joe"}, "2.5.4.42=Joe,CN=joe"),
    pytest.param("joe", {"T": "mytitle"}, "2.5.4.12=mytitle,CN=joe"),
    pytest.param("joe", {
        "O": "corp",
        "OU": "IT",
        "T": "mytitle",
        "C": "US",
        "ST": "IL",
        "L": "Chicago",
        "SN": "Doe",
        "GN": "Joe",
    }, "2.5.4.42=Joe,2.5.4.4=Doe,L=Chicago,ST=IL,C=US,2.5.4.12=mytitle,OU=IT,O=corp,CN=joe"),
])
def test__csr__subject(cn, additional_subject, expected):
    k = Key()
    c = CSR(key=k, common_name=cn, additional_subject=additional_subject)
    assert c.subject == expected


def test__csr__pem():
    k = Key()
    cc = CSR(key=k, common_name="joe")
    assert cc.pem.decode("utf-8").startswith(
        "-----BEGIN CERTIFICATE REQUEST-----")
    assert cc.pem.decode("utf-8").endswith(
        "-----END CERTIFICATE REQUEST-----\n")


def test__csr__base64():
    k = Key()
    cc = CSR(key=k, common_name="joe")
    assert cc.base64[:32] == "LS0tLS1CRUdJTiBDRVJUSUZJQ0FURSBS"


def test__csr__save(tmp_path):
    k = Key()
    cc = CSR(key=k, common_name="joe")
    save_csr = tmp_path / "csr.pem"
    save_csr.write_text("")
    cc.save(path=save_csr)

    with open(save_csr) as f:
        saved_csr = f.read()

    assert saved_csr.startswith(
        "-----BEGIN CERTIFICATE REQUEST-----")
    assert saved_csr.endswith(
        "-----END CERTIFICATE REQUEST-----\n")


def test__cert__init__crt_file():
    ct = Cert(crt_file=os.path.join(FIXTURE_DIR, "03_cert.pem"))
    assert ct.crt.serial_number == 61276984187087310175771381080539889888


def test__cert__init__crt_data():
    with open(os.path.join(FIXTURE_DIR, "03_cert.pem"), 'rb') as f:
        ct = Cert(crt_data=f.read())
    assert ct.crt.serial_number == 61276984187087310175771381080539889888


def test__cert__init__subject():
    ct = Cert(crt_file=os.path.join(FIXTURE_DIR, "03_cert.pem"))
    assert ct.subject == "CN=john2,O=jazstudios"


def test__cert__pem():
    ct = Cert(crt_file=os.path.join(FIXTURE_DIR, "03_cert.pem"))
    assert ct.pem.decode("utf-8").startswith(
        "-----BEGIN CERTIFICATE-----")
    assert ct.pem.decode("utf-8").endswith(
        "-----END CERTIFICATE-----\n")

def test__cert__save(tmp_path):
    ct = Cert(crt_file=os.path.join(FIXTURE_DIR, "03_cert.pem"))
    save_crt = tmp_path / "cert.pem"
    save_crt.write_text("")
    ct.save(path=save_crt)

    with open(save_crt) as f:
        saved_crt = f.read()
    assert saved_crt.startswith(
        "-----BEGIN CERTIFICATE-----")
    assert saved_crt.endswith(
        "-----END CERTIFICATE-----\n")


def test__csrandkey__init():
    ck = CSRandKey(
        common_name="joe",
        additional_subject={"O": "myorg"},
        key_size=2048,
    )
    assert ck.csr.subject == "O=myorg,CN=joe"

    assert (
        ck.key.key.public_key().public_numbers().n ==
        ck.csr.csr.public_key().public_numbers().n
    )
