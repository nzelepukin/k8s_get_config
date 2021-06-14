from typing import Optional, Dict, List
import time
from datetime import datetime, timezone
import kubernetes
from kubernetes.client.rest import ApiException


class SAResource:
    def __init__(
        self,
        name: str,
        namespace: str,
        metadata: Optional[Dict] = None,
        extra_kwargs: Dict = {},
    ):
        self._resource_cache = None
        self._resource_token_secret_cache = None
        self.name = name
        self.namespace = namespace
        self.metadata = metadata if isinstance(metadata, dict) else {}
        self.automount_service_account_token = extra_kwargs.get(
            "automount_service_account_token", False
        )

    def get_text(self):
        """Return the text of the ServiceAccount that will be set to the
        kubernetes api."""
        metadata = self.metadata
        metadata.update({"name": self.name})
        return kubernetes.client.V1ServiceAccount(
            kind="ServiceAccount",
            metadata=kubernetes.client.V1ObjectMeta(**metadata),
            automount_service_account_token=self.automount_service_account_token,
        )

    def get_resource(self, api_client: kubernetes.client.ApiClient, cache=True):
        """Get the ServiceAccount object from the kubernetes cluster based on 
        the self.name. If cache is set to True, then cache the result and fetch from
        the cache on subsequent lookups.
        """
        if cache and self._resource_cache:
            return self._resource_cache
        api_instance = kubernetes.client.CoreV1Api(api_client)

        try:
            response = api_instance.read_namespaced_service_account(
                name=self.name, namespace=self.namespace
            )
        except ApiException as exc:
            response = None
            if exc.status != 404:
                raise
        self._resource_cache = response
        return response

    def resource_exists(
        self, api_client: kubernetes.client.ApiClient, cache: Optional[bool] = True
    ) -> bool:
        """Return if the ServiceAccount exists in the cluster"""
        return bool(self.get_resource(api_client, cache))

    def create(self, api_client: kubernetes.client.ApiClient):
        """Create the ServiceAccount in the kubernetes cluster"""
        if not self.resource_exists(api_client):
            api_instance = kubernetes.client.CoreV1Api(api_client)
            return api_instance.create_namespaced_service_account(
                namespace=self.namespace, body=self.get_text()
            )
        else:
            return self.get_resource(api_client)

    def get_token_secret_resource_name(
        self, api_client: kubernetes.client.ApiClient, timeout: int = 10
    ):
        start = time.time()
        cert = None
        while time.time() - start < timeout:
            sa = self.get_resource(api_client, cache=False)
            try:
                token = [s for s in sa.secrets if "token" in s.name][0].name
            except (IndexError, AttributeError, TypeError):
                token = None
            if token:
                break
            time.sleep(1)
        return token

    def get_token_secret_resource(
        self, api_client: kubernetes.client.ApiClient, cache=True
    ):
        if cache and self._resource_token_secret_cache:
            return self._resource_token_secret_cache
        api_instance = kubernetes.client.CoreV1Api(api_client)
        token_resource_name = self.get_token_secret_resource_name(api_client)
        try:
            response = api_instance.read_namespaced_secret(
                name=token_resource_name, namespace=self.namespace
            )
        except ApiException as exc:
            response = None
            if exc.status != 404:
                raise
        self._resource_token_secret_cache = response
        return response

    def get_token(self, api_client: kubernetes.client.ApiClient, timeout: int = 10):
        start = time.time()
        token = None
        while time.time() - start < timeout:
            secret = self.get_token_secret_resource(api_client, cache=False)
            try:
                token = secret.data["token"]
            except (IndexError, AttributeError):
                token = None
            if token:
                break
            time.sleep(1)
        return token
