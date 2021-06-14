import os
from unittest import mock
import yaml
from k8s_user.workflows.sa_workflow import UserTokenWorkflow
from k8s_user.k8s.sa_resource import SAResource
from k8s_user.k8s.kubeconfig import TokenKubeConfig, ClusterConfigGen
from ..utils import get_self_signed_cert


FIXTURE_DIR = os.path.join(
    os.path.dirname(os.path.realpath(__file__)),
    "..", 'fixtures',
    )


class FakeUser:
    name = "fakename"


@mock.patch.object(ClusterConfigGen, 'host', new_callable=mock.PropertyMock)
@mock.patch.object(ClusterConfigGen, 'cluster_ca_cert', new_callable=mock.PropertyMock)
def test_usersaworkflow(mock_cluster_ca_cert, mock_host, tmpdir):

    mock_cluster_ca_cert.return_value = "<ca-cert-data>"
    mock_host.return_value = "test-host"
    kubeconfig_path = os.path.join(tmpdir.dirname, 'kubeconfig.yaml')

    def mock_get_token_func(self, *args, **kwargs):
        return "test-token"

    with mock.patch.object(SAResource, 'get_token', mock_get_token_func):

        fuser = FakeUser()
        csr_wf = UserTokenWorkflow(inputs={
            "api_client": mock.MagicMock(),
            "kubeconfig_klass": TokenKubeConfig,
            "user": fuser,
            "creds_dir": tmpdir.dirname,
            "out_kubeconfig": kubeconfig_path,
            "namespace": "default",
        })
        csr_wf.start()

        with open(kubeconfig_path) as c:
            kubeconfig_yaml = (yaml.safe_load(c))

        assert kubeconfig_yaml['users'][0]['user']['token'] == 'test-token'
        assert kubeconfig_yaml['users'][0]['name'] == 'fakename'

        assert kubeconfig_yaml['clusters'][0]['cluster']['certificate-authority-data'] == '<ca-cert-data>'
        assert kubeconfig_yaml['clusters'][0]['cluster']['server'] == 'test-host'
