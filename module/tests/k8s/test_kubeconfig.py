import os
from unittest import mock
import pytest
import kubernetes
from k8s_user.pki import KeyBundle
from k8s_user.k8s.kubeconfig import (
    GenericConfigGen, ClusterConfigGen,
    CSRUserConfigGen, CSRKubeConfig, TokenKubeConfig)
from k8s_user.workflows.sa_workflow import TokenBundle


FIXTURE_DIR = os.path.join(
    os.path.dirname(os.path.realpath(__file__)),
    'fixtures',
    )


@pytest.mark.parametrize("in1,in2,expected", 
[
    pytest.param({}, {}, {}),
    pytest.param(
        {"name": "1"}, {"name2": "2"},
        {"name": "1", "name2": "2"}),
    pytest.param(
        {"name": {}}, {"name2": {}},
        {"name": {}, "name2": {}}),
    pytest.param(
        {"name": {"value": "1"}}, {"name2": {"a": "b"}},
        {"name": {"value": "1"}, "name2": {"a": "b"}}),
])
def test__GenericConfigGen(in1, in2, expected):
    assert GenericConfigGen(in1, in2).to_dict() == expected


@pytest.mark.parametrize("in1,in2,expected", 
[
    pytest.param({}, {}, {}),
    pytest.param(
        {"name": "1"}, {"name2": "2"},
        {"name": "1", "name2": "2"}),
    pytest.param(
        {"name": {}}, {"name2": {}},
        {"name": {}, "name2": {}}),
    pytest.param(
        {"name": {"value": "1"}}, {"name2": {"a": "b"}},
        {"name": {"value": "1"}, "name2": {"a": "b"}}),
])
def test__GenericConfigGen_2x(in1, in2, expected):
    assert (
        GenericConfigGen(in1, {}) |
        GenericConfigGen(in2, {})
    ).to_dict() == expected


def test__ClusterConfigGen(tmp_path):

    save_ca_cert = tmp_path / "ca-cert.pem"
    save_ca_cert.write_text("hi")

    class DummyConfiguration:
        host = "localhost"
        ssl_ca_cert = save_ca_cert

    mock_api_client = mock.Mock(spec=kubernetes.client.ApiClient)
    mock_api_client.configuration = DummyConfiguration()
    ccg = ClusterConfigGen(mock_api_client, "my_cluster")
    assert ccg.to_dict() == {
        'clusters': [{'cluster': {'certificate-authority-data': 'aGk=',
                                   'server': 'localhost'},
                      'name': 'my_cluster'}]}


def test__CSRUserConfigGen(tmp_path):

    save_cert = tmp_path / "cert.pem"
    save_cert.write_text("hi")

    dummy_keybundle = KeyBundle(
            user_name="myname",
            user_key="mykey",
            user_csr="mycsr",
            user_cert="mycrt",
        )

    class DummyConfiguration:
        host = "localhost"
        ssl_ca_cert = save_cert

    mock_api_client = mock.Mock(spec=kubernetes.client.ApiClient)
    mock_api_client.configuration = DummyConfiguration()
    ccg = CSRUserConfigGen(mock_api_client, dummy_keybundle)
    assert ccg.to_dict() == {
        'users': [{'name': 'myname',
                   'user': {'client-certificate-data': 'mycrt',
                            'client-key-data': 'mykey'}}]}


def test__multi__ConfigGen(tmp_path):

    save_cert = tmp_path / "cert.pem"
    save_cert.write_text("hi")

    save_ca_cert = tmp_path / "ca-cert.pem"
    save_ca_cert.write_text("hi")

    dummy_keybundle = KeyBundle(
            user_name="myname",
            user_key="mykey",
            user_csr="mycsr",
            user_cert="mycrt",
        )

    class DummyConfiguration:
        host = "localhost"
        ssl_ca_cert = save_cert

    mock_api_client = mock.Mock(spec=kubernetes.client.ApiClient)
    mock_api_client.configuration = DummyConfiguration()

    assert (ClusterConfigGen(mock_api_client, "my_cluster") |
            CSRUserConfigGen(mock_api_client, dummy_keybundle) |
            GenericConfigGen(
                {"apiVersion": "v1",
                "kind": "Config", "preferences": {}}, {})
            ).to_dict() == {
                'apiVersion': 'v1',
                'clusters': [{'cluster': {'certificate-authority-data': 'aGk=',
                                        'server': 'localhost'},
                            'name': 'my_cluster'}],
                'kind': 'Config',
                'preferences': {},
                'users': [{'name': 'myname',
                        'user': {'client-certificate-data': 'mycrt',
                                    'client-key-data': 'mykey'}}],
            }


def test__CSRKubeConfig(tmp_path):

    save_cert = tmp_path / "cert.pem"
    save_cert.write_text("hi")

    dummy_keybundle = KeyBundle(
            user_name="myname",
            user_key="mykey",
            user_csr="mycsr",
            user_cert="mycrt",
        )

    class DummyConfiguration:
        host = "localhost"
        ssl_ca_cert = save_cert

    mock_api_client = mock.Mock(spec=kubernetes.client.ApiClient)
    mock_api_client.configuration = DummyConfiguration()

    kc = CSRKubeConfig(
        mock_api_client,
        "mycontext",
        "mycluster",
        dummy_keybundle,
    )

    assert kc.generate() == {
        'apiVersion': 'v1',
        'clusters': [{'cluster': {'certificate-authority-data': 'aGk=',
                                  'server': 'localhost'},
                      'name': 'mycontext'}],
        'contexts': [{'context': {'cluster': 'mycontext',
                                  'user': 'myname'},
                      'name': 'mycluster'}],
        'current-context': 'mycluster',
        'kind': 'Config',
        'preferences': {},
        'users': [{'name': 'myname',
                   'user': {'client-certificate-data': 'mycrt',
                            'client-key-data': 'mykey'}}],
        }


def test__TokenKubeConfig(tmp_path):

    save_cert = tmp_path / "cert.pem"
    save_cert.write_text("hi")

    dummy_tokenbundle = TokenBundle(
            user_name="myname",
            user_token="mytoken",
        )

    class DummyConfiguration:
        host = "localhost"
        ssl_ca_cert = save_cert

    mock_api_client = mock.Mock(spec=kubernetes.client.ApiClient)
    mock_api_client.configuration = DummyConfiguration()

    kc = TokenKubeConfig(
        mock_api_client,
        "mycontext",
        "mycluster",
        dummy_tokenbundle,
    )

    assert kc.generate() == {
        'apiVersion': 'v1',
        'clusters': [{'cluster': {'certificate-authority-data': 'aGk=',
                                  'server': 'localhost'},
                      'name': 'mycontext'}],
        'contexts': [{'context': {'cluster': 'mycontext',
                                  'user': 'myname'},
                      'name': 'mycluster'}],
        'current-context': 'mycluster',
        'kind': 'Config',
        'preferences': {},
        'users': [{'name': 'myname',
                   'user': {'token': 'mytoken'}}],
        }
