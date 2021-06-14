from typing import Optional, Dict, List
import base64
import yaml
import kubernetes


def _read_cert(path):
    with open(path, "rb") as f:
        return f.read()


def _base64(cert_data):
    return base64.b64encode(cert_data).decode("utf-8")


class GenericConfigGen:
    def __init__(self, left, right, **kwargs):
        self.left = left
        self.right = right

    def to_dict(self):
        left = self.left.to_dict() if hasattr(self.left, "to_dict") else self.left
        right = self.right.to_dict() if hasattr(self.right, "to_dict") else self.right
        return {**right, **left}

    def __or__(self, other):
        return GenericConfigGen(self, other)


class ClusterConfigGen:
    """Add server information to a kubeconfig"""

    def __init__(
        self, api_client: kubernetes.client.ApiClient, cluster_name: str, **kwargs,
    ):
        self.api_client = api_client
        self.cluster_name = cluster_name

    @property
    def cluster_ca_cert(self):
        return _base64(_read_cert(self.api_client.configuration.ssl_ca_cert))

    @property
    def host(self):
        return self.api_client.configuration.host

    def to_dict(self):
        return {
            "clusters": [
                {
                    "cluster": {
                        "certificate-authority-data": self.cluster_ca_cert,
                        "server": self.host,
                    },
                    "name": self.cluster_name,
                },
            ]
        }

    def __or__(self, other):
        return GenericConfigGen(self, other)


class CSRUserConfigGen:
    """Add User information to a kubeconfig"""

    def __init__(self, api_client: kubernetes.client.ApiClient, keybundle, **kwargs):
        self.api_client = api_client
        self.keybundle = keybundle

    @property
    def cert(self):
        return _base64(_read_cert(self.api_client.configuration.cert_file))

    def to_dict(self):
        return {
            "users": [
                {
                    "name": self.keybundle.user_name,
                    "user": {
                        "client-certificate-data": self.keybundle.user_cert,
                        "client-key-data": self.keybundle.user_key,
                    },
                },
            ]
        }

    def __or__(self, other):
        return GenericConfigGen(self, other)


class TokenUserConfigGen:
    """Add a token to a kubeconfig"""

    def __init__(self, api_client: kubernetes.client.ApiClient, tokenbundle, **kwargs):
        self.api_client = api_client
        self.tokenbundle = tokenbundle

    def to_dict(self):
        return {
            "users": [
                {
                    "name": self.tokenbundle.user_name,
                    "user": {"token": self.tokenbundle.user_token,},
                },
            ]
        }

    def __or__(self, other):
        return GenericConfigGen(self, other)


class KubeConfigBase:
    def __init__(
        self,
        api_client: kubernetes.client.ApiClient,
        config_gen_klasses: Optional[Dict] = None,
        **kwargs,
    ):
        self.api_client = api_client
        self.kubeconfig_dict = {}
        self.config_kwargs = {}
        if config_gen_klasses:
            self._config_gen_klasses.update(config_gen_klasses)

    def generate(self):
        self.kubeconfig_dict = (
            self._config_gen_klasses["cluster"](**self.config_kwargs)
            | self._config_gen_klasses["user"](**self.config_kwargs)
            | self._config_gen_klasses["generic"](*self.static_config())
        ).to_dict()
        return self.kubeconfig_dict

    def save(self, path):
        if not self.kubeconfig_dict:
            self.generate()
        with open(path, "w") as f:
            f.write(yaml.dump(self.kubeconfig_dict))


class CSRKubeConfig(KubeConfigBase):
    """Generate a Kubeconfig with user csr"""

    _config_gen_klasses = {
        "cluster": ClusterConfigGen,
        "user": CSRUserConfigGen,
        "generic": GenericConfigGen,
    }

    def __init__(
        self,
        api_client: kubernetes.client.ApiClient,
        cluster_name: str,
        context_name: str,
        keybundle,
        config_gen_klasses: Optional[Dict] = None,
        **kwargs,
    ):
        super().__init__(
            api_client=api_client, config_gen_klasses=config_gen_klasses, **kwargs
        )

        updates = {
            "cluster_name": cluster_name,
            "context_name": context_name,
            "keybundle": keybundle,
            "api_client": api_client,
        }
        self.config_kwargs.update(updates)

    def static_config(self):
        return (
            {"apiVersion": "v1", "kind": "Config", "preferences": {}},
            {
                "current-context": self.config_kwargs["context_name"],
                "contexts": [
                    {
                        "context": {
                            "cluster": self.config_kwargs["cluster_name"],
                            "user": self.config_kwargs["keybundle"].user_name,
                        },
                        "name": self.config_kwargs["context_name"],
                    },
                ],
            },
        )


class TokenKubeConfig(KubeConfigBase):
    """Generate a Kubeconfig with user token"""

    _config_gen_klasses = {
        "cluster": ClusterConfigGen,
        "user": TokenUserConfigGen,
        "generic": GenericConfigGen,
    }

    def __init__(
        self,
        api_client: kubernetes.client.ApiClient,
        cluster_name: str,
        context_name: str,
        tokenbundle,
        config_gen_klasses: Optional[Dict] = None,
        **kwargs,
    ):
        super().__init__(
            api_client=api_client, config_gen_klasses=config_gen_klasses, **kwargs
        )

        updates = {
            "cluster_name": cluster_name,
            "context_name": context_name,
            "tokenbundle": tokenbundle,
            "api_client": api_client,
        }
        self.config_kwargs.update(updates)

    def static_config(self):
        return (
            {"apiVersion": "v1", "kind": "Config", "preferences": {}},
            {
                "current-context": self.config_kwargs["context_name"],
                "contexts": [
                    {
                        "context": {
                            "cluster": self.config_kwargs["cluster_name"],
                            "user": self.config_kwargs["tokenbundle"].user_name,
                        },
                        "name": self.config_kwargs["context_name"],
                    },
                ],
            },
        )
