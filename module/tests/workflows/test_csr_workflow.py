import os
import base64
from unittest import mock
import yaml
from cryptography.hazmat.primitives import serialization
from k8s_user.workflows.csr_workflow import UserCSRWorkflow
from k8s_user.k8s.csr_resource import CSRResource
from k8s_user.k8s.kubeconfig import CSRKubeConfig, ClusterConfigGen
from ..utils import get_self_signed_cert


FIXTURE_DIR = os.path.join(
    os.path.dirname(os.path.realpath(__file__)),
    "..", 'fixtures',
    )


class FakeUser:
    name = "fakename"


@mock.patch.object(ClusterConfigGen, 'host', new_callable=mock.PropertyMock)
@mock.patch.object(ClusterConfigGen, 'cluster_ca_cert', new_callable=mock.PropertyMock)
def test_usercsrworkflow(mock_cluster_ca_cert, mock_host, tmpdir):

    mock_cluster_ca_cert.return_value = "<ca-cert-data>"
    mock_host.return_value = "test-host"
    kubeconfig_path = os.path.join(tmpdir.dirname, 'kubeconfig.yaml')

    def mock_get_cert_func(self, *args, **kwargs):
        cert_file = os.path.join(tmpdir.dirname, 'fakename.key.pem')
        cert = get_self_signed_cert(cert_file)
        cert_bytes = cert.public_bytes(serialization.Encoding.PEM)
        return base64.b64encode(cert_bytes)

    with mock.patch.object(CSRResource, 'get_cert', mock_get_cert_func):

        fuser = FakeUser()
        csr_wf = UserCSRWorkflow(inputs={
            "api_client": mock.MagicMock(),
            "kubeconfig_klass": CSRKubeConfig,
            "user": fuser,
            "creds_dir": tmpdir.dirname,
            "out_kubeconfig": kubeconfig_path,
        })
        csr_wf.start()

        with open(kubeconfig_path) as c:
            kubeconfig_yaml = (yaml.safe_load(c))
        
        assert kubeconfig_yaml['users'][0]['user']['client-certificate-data']
        assert kubeconfig_yaml['users'][0]['user']['client-key-data']
        assert kubeconfig_yaml['users'][0]['name'] == 'fakename'

        assert kubeconfig_yaml['clusters'][0]['cluster']['certificate-authority-data'] == '<ca-cert-data>'
        assert kubeconfig_yaml['clusters'][0]['cluster']['server'] == 'test-host'
