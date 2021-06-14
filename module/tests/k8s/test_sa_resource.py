import os
from unittest import mock
import json
import pytest
import kubernetes
from kubernetes.client.rest import ApiException
from k8s_user.k8s.sa_resource import SAResource


FIXTURE_DIR = os.path.join(
    os.path.dirname(os.path.realpath(__file__)),
    "..", 'fixtures',
    )


def test__saresource__init():
    name = "joe"
    namespace = "default"
    sar = SAResource(
        name=name,
        namespace=namespace,
    )
    with open(os.path.join(FIXTURE_DIR, "04_sa_resource_init.json")) as f:
        expected_sa_resource = json.loads(f.read())
        assert sar.get_text().to_dict() == expected_sa_resource


@mock.patch('k8s_user.k8s.sa_resource.kubernetes.client.CoreV1Api')
def test__saresource__get_resource(mock_CoreV1Api):

    name = "joe"
    namespace = "namespace"
    mock_response = {'dummy': "response"}
    mock_read_sa = mock.MagicMock()
    mock_read_sa.return_value = mock_response
    mock_CoreV1Api.return_value.read_namespaced_service_account = mock_read_sa

    mock_api_client = mock.Mock(spec=kubernetes.client.ApiClient) 
    sar = SAResource(
        name=name,
        namespace=namespace,
    )
    assert sar.get_resource(mock_api_client) == mock_response
    mock_read_sa.assert_called_once_with(name=name, namespace=namespace)
    # test the cache worked
    assert sar._resource_cache == mock_response


@mock.patch('k8s_user.k8s.sa_resource.kubernetes.client.CoreV1Api')
def test__saresource__get_resource__404(mock_CoreV1Api):

    name = "joe"
    namespace = "namespace"
    mock_response = {'dummy': "response"}
    mock_read_sa = mock.MagicMock()
    mock_read_sa.side_effect = ApiException(status = 404)
    mock_CoreV1Api.return_value.read_namespaced_service_account = mock_read_sa

    mock_api_client = mock.Mock(spec=kubernetes.client.ApiClient) 
    sar = SAResource(
        name=name,
        namespace=namespace,
    )
    assert sar.get_resource(mock_api_client) is None
    mock_read_sa.assert_called_once_with(name=name, namespace=namespace)


@pytest.mark.parametrize("resource,expected", 
[
    pytest.param({"dummy": "resource"}, True),
    pytest.param(None, False),
])
def test__saresource__resource_exists(resource, expected):
    name = "joe"
    namespace = "default"
    mock_api_client = mock.Mock(spec=kubernetes.client.ApiClient) 
    sar = SAResource(
        name=name,
        namespace=namespace)
    with mock.patch.object(sar, 'get_resource') as mock__get_resource:
        mock__get_resource.return_value = resource
        assert sar.resource_exists(mock_api_client) == expected


@mock.patch('k8s_user.k8s.sa_resource.kubernetes.client.CoreV1Api')
def test__saresource__create__new(mock_CoreV1Api):

    mock_response = {'dummy': "response"}
    mock_create_sa = mock.MagicMock()
    mock_create_sa.return_value = mock_response
    mock_CoreV1Api.return_value.create_namespaced_service_account = mock_create_sa

    name = "joe"
    namespace = "default"
    mock_api_client = mock.Mock(spec=kubernetes.client.ApiClient) 
    sar = SAResource(
        name=name,
        namespace=namespace)

    with mock.patch.object(sar, 'resource_exists') as mock__resource_exists:
        mock__resource_exists.return_value = False
        assert sar.create(mock_api_client) == mock_response
        mock_create_sa.assert_called_once()


@mock.patch('k8s_user.k8s.sa_resource.kubernetes.client.CoreV1Api')
def test__saresource__create__existing(mock_CoreV1Api):

    mock_response = {'dummy': "response"}

    name = "joe"
    namespace = "default"
    mock_api_client = mock.Mock(spec=kubernetes.client.ApiClient) 
    sar = SAResource(
        name=name,
        namespace=namespace)

    with mock.patch.object(sar, 'resource_exists') as mock__resource_exists:
        mock__resource_exists.return_value = True
        with mock.patch.object(sar, 'get_resource') as mock__get_resource:
            mock__get_resource.return_value = mock_response
            assert sar.create(mock_api_client) == mock_response


@mock.patch('k8s_user.k8s.sa_resource.kubernetes.client.CoreV1Api')
def test__saresource__get_token_secret_resource(mock_CoreV1Api):

    mock_response = {'dummy': "response"}
    mock_read_secret = mock.MagicMock()
    mock_read_secret.return_value = mock_response

    name = "joe"
    namespace = "default"
    mock_api_client = mock.Mock(spec=kubernetes.client.ApiClient) 
    sar = SAResource(
        name=name,
        namespace=namespace)
    with mock.patch.object(sar, 'get_token_secret_resource_name') as mock__get_token_secret_resource_name:
        mock__get_token_secret_resource_name.return_value = "joe-token-1234"
        mock_CoreV1Api.return_value.read_namespaced_secret = mock_read_secret
        assert sar.get_token_secret_resource(mock_api_client) == mock_response


@mock.patch('k8s_user.k8s.sa_resource.kubernetes.client.CoreV1Api')
def test__saresource__get_token(mock_CoreV1Api):


    class DummSecret:
        def __init__(self):
            self.data = {"token": "mytoken"}

    name = "joe"
    namespace = "default"
    mock_api_client = mock.Mock(spec=kubernetes.client.ApiClient) 
    sar = SAResource(
        name=name,
        namespace=namespace)
    with mock.patch.object(sar, 'get_token_secret_resource') as mock__get_token_secret_resource:
        mock__get_token_secret_resource.return_value = DummSecret()
        assert sar.get_token(mock_api_client) == "mytoken"