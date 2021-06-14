from typing import Optional, Dict, List
import time
from datetime import datetime, timezone
import kubernetes
from kubernetes.client.rest import ApiException


class CSRResource:
    """Class for managing the CertificateSigningRequest Kubernetes resource.
    
    :param name: the name of the CSR k8s resource
    :param csr_string: a base64 encoded CSR string
    :param metadata: an optional dict with fields matching k8s V1ObjectMeta object
    :param groups: RBAC groups to add to this CSR (defaults to ["system:authenticated"])
    :param usages: CSR usages (defaults to ["client auth"])
    """

    def __init__(
        self,
        name: str,
        csr_str: str,
        metadata: Optional[Dict] = None,
        groups: Optional[List] = None,
        usages: Optional[List] = None,
    ):
        self._resource_cache = None
        self.name = name
        self.csr_str = csr_str
        self.metadata = metadata if isinstance(metadata, dict) else {}
        self.groups = groups if groups else ["system:authenticated"]
        self.usages = usages if usages else ["client auth"]

    def get_text(self):
        """Return the text of the CertificateSigningRequest that will be set to the
        kubernetes api."""
        metadata = self.metadata
        metadata.update({"name": self.name})
        return kubernetes.client.V1beta1CertificateSigningRequest(
            kind="CertificateSigningRequest",
            metadata=kubernetes.client.V1ObjectMeta(**metadata),
            spec=kubernetes.client.models.v1beta1_certificate_signing_request_spec.V1beta1CertificateSigningRequestSpec(
                request=self.csr_str, groups=self.groups, usages=self.usages,
            ),
        )

    def get_resource(
        self, api_client: kubernetes.client.ApiClient, cache: Optional[bool] = True
    ):
        """Get the CertificateSigningRequest object from the kubernetes cluster based on 
        the self.name. If cache is set to True, then cache the result and fetch from
        the cache on subsequent lookups.
        """
        if cache and self._resource_cache:
            return self._resource_cache
        api_instance = kubernetes.client.CertificatesV1beta1Api(api_client)
        try:
            response = api_instance.read_certificate_signing_request_status(self.name)
        except ApiException as exc:
            response = None
            if exc.status != 404:
                raise
        self._resource_cache = response
        return response

    def resource_exists(
        self, api_client: kubernetes.client.ApiClient, cache: Optional[bool] = True
    ) -> bool:
        """Return if the CertificateSigningRequest exists in the cluster"""
        return bool(self.get_resource(api_client, cache))

    def create(self, api_client: kubernetes.client.ApiClient):
        """Create the CertificateSigningRequest in the kubernetes cluster"""
        if not self.resource_exists(api_client):
            api_instance = kubernetes.client.CertificatesV1beta1Api(api_client)
            return api_instance.create_certificate_signing_request(self.get_text())
        else:
            return self.get_resource(api_client)

    def approve(
        self,
        api_client: kubernetes.client.ApiClient,
        message: Optional[str] = "This certificate was approved by the Python Client.",
        reason: Optional[str] = "ApprovedForUser",
    ):
        """Approve the CSR in Kubernetes"""
        csr_status = self.get_resource(api_client, cache=False)
        # create an approval condition
        approval_condition = kubernetes.client.V1beta1CertificateSigningRequestCondition(
            last_update_time=datetime.now(timezone.utc).astimezone(),
            message=message,
            reason=reason,
            type="Approved",
        )

        # patch the existing `body` with the new conditions
        # you might want to append the new conditions to the existing ones
        csr_status.status.conditions = [approval_condition]
        api_instance = kubernetes.client.CertificatesV1beta1Api(api_client)
        response = api_instance.replace_certificate_signing_request_approval(
            self.name, csr_status
        )
        self._resource_cache = response
        return response

    def get_cert(
        self, api_client: kubernetes.client.ApiClient, timeout: Optional[int] = 10
    ):
        """Get the certificate from the CSR object"""
        start = time.time()
        cert = None
        while time.time() - start < timeout:
            csr_status = self.get_resource(api_client, cache=False)
            cert = csr_status.status.certificate
            if cert:
                break
            time.sleep(1)
        return cert
