import os
from unittest import mock
import json
import pytest
import kubernetes
from kubernetes.client.rest import ApiException
from k8s_user.pki import CSRandKey, CSR, Key
from k8s_user.k8s.csr_resource import CSRResource


FIXTURE_DIR = os.path.join(
    os.path.dirname(os.path.realpath(__file__)),
    "..", 'fixtures',
    )


def test__csrresource__init():
    name = "joe"
    cak = CSRandKey(common_name=name)
    csrr = CSRResource(
        name=name,
        csr_str=cak.csr.base64)
    with open(os.path.join(FIXTURE_DIR, "02_csr_resource_init.json")) as f:
        expected_csr_resource = json.loads(f.read())
        expected_csr_resource['spec']['request'] = cak.csr.base64
        assert csrr.get_text().to_dict() == expected_csr_resource



@mock.patch('k8s_user.k8s.csr_resource.kubernetes.client.CertificatesV1beta1Api')
def test__csrresource__get_resource(mock_CertificatesV1beta1Api):

    name = "joe"
    mock_response = {'dummy': "response"}
    mock_read_csr = mock.MagicMock()
    mock_read_csr.return_value = mock_response
    mock_CertificatesV1beta1Api.return_value.read_certificate_signing_request_status = mock_read_csr

    mock_api_client = mock.Mock(spec=kubernetes.client.ApiClient) 
    cak = CSRandKey(common_name=name)
    csrr = CSRResource(
        name=name,
        csr_str=cak.csr.base64)
    assert csrr.get_resource(mock_api_client) == mock_response
    mock_read_csr.assert_called_once_with(name)
    # test the cache worked
    assert csrr._resource_cache == mock_response


@mock.patch('k8s_user.k8s.csr_resource.kubernetes.client.CertificatesV1beta1Api')
def test__csrresource__get_resource__404(mock_CertificatesV1beta1Api):

    name = "joe"
    mock_read_csr = mock.MagicMock()
    mock_read_csr.side_effect = ApiException(status = 404)
    mock_CertificatesV1beta1Api.return_value.read_certificate_signing_request_status = mock_read_csr

    mock_api_client = mock.Mock(spec=kubernetes.client.ApiClient) 
    cak = CSRandKey(common_name=name)
    csrr = CSRResource(
        name=name,
        csr_str=cak.csr.base64)
    assert csrr.get_resource(mock_api_client) is None
    mock_read_csr.assert_called_once_with(name)


@pytest.mark.parametrize("resource,expected", 
[
    pytest.param({"dummy": "resource"}, True),
    pytest.param(None, False),
])
def test__csrresource__resource_exists(resource, expected):
    name = "joe"
    mock_api_client = mock.Mock(spec=kubernetes.client.ApiClient) 
    cak = CSRandKey(common_name=name)
    csrr = CSRResource(
        name=name,
        csr_str=cak.csr.base64)
    with mock.patch.object(csrr, 'get_resource') as mock__get_resource:
        mock__get_resource.return_value = resource
        assert csrr.resource_exists(mock_api_client) == expected


@mock.patch('k8s_user.k8s.csr_resource.kubernetes.client.CertificatesV1beta1Api')
def test__csrresource__create__new(mock_CertificatesV1beta1Api):

    mock_response = {'dummy': "response"}
    mock_create_csr = mock.MagicMock()
    mock_create_csr.return_value = mock_response
    mock_CertificatesV1beta1Api.return_value.create_certificate_signing_request = mock_create_csr

    name = "joe"
    mock_api_client = mock.Mock(spec=kubernetes.client.ApiClient) 
    cak = CSRandKey(common_name=name)
    csrr = CSRResource(
        name=name,
        csr_str=cak.csr.base64)

    with mock.patch.object(csrr, 'resource_exists') as mock__resource_exists:
        mock__resource_exists.return_value = False
        assert csrr.create(mock_api_client) == mock_response
        mock_create_csr.assert_called_once()


@mock.patch('k8s_user.k8s.csr_resource.kubernetes.client.CertificatesV1beta1Api')
def test__csrresource__create__existing(mock_CertificatesV1beta1Api):

    mock_response = {'dummy': "response"}

    name = "joe"
    mock_api_client = mock.Mock(spec=kubernetes.client.ApiClient) 
    cak = CSRandKey(common_name=name)
    csrr = CSRResource(
        name=name,
        csr_str=cak.csr.base64)

    with mock.patch.object(csrr, 'resource_exists') as mock__resource_exists:
        mock__resource_exists.return_value = True
        with mock.patch.object(csrr, 'get_resource') as mock__get_resource:
            mock__get_resource.return_value = mock_response
            assert csrr.create(mock_api_client) == mock_response


@mock.patch('k8s_user.k8s.csr_resource.kubernetes.client.CertificatesV1beta1Api')
def test__csrresource__approve(mock_CertificatesV1beta1Api):
    class DummyStatus:
        conditions = None

    class DummyResponse:
        def __init__(self):
            self.status = DummyStatus()

    mock_response = DummyResponse()

    mock_approve_csr = mock.MagicMock()
    mock_approve_csr.return_value = mock_response
    mock_CertificatesV1beta1Api.return_value.replace_certificate_signing_request_approval = mock_approve_csr

    name = "joe"
    mock_api_client = mock.Mock(spec=kubernetes.client.ApiClient) 
    cak = CSRandKey(common_name=name)
    csrr = CSRResource(
        name=name,
        csr_str=cak.csr.base64)

    with mock.patch.object(csrr, 'get_resource') as mock__get_resource:
        mock__get_resource.return_value = mock_response
        assert csrr.approve(mock_api_client) == mock_response
        mock_approve_csr.assert_called_once()
        assert csrr._resource_cache == mock_response

# def test__csrresource__get_cert():

#     class DummyStatus:
#         certificate = "foo_cert"

#     class DummyResponse:
#         def __init__(self):
#             self.status = DummyStatus()

#     mock_response = DummyResponse()

#     name = "joe"
#     mock_api_client = mock.Mock(spec=kubernetes.client.ApiClient) 
#     cak = CSRandKey(common_name=name)
#     csrr = CSRResource(
#         name=name,
#         csr_str=cak.csr.base64)

#     with mock.patch.object(csrr, 'get_resource') as mock__get_resource:
#         breakpoint()
#         mock__get_resource.return_value = mock_response
#         assert csrr.approve(mock_api_client) == 'foo_cert'
