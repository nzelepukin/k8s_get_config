import os
from typing import Dict
import collections
import base64
from ..pki import Cert, CSRandKey, KeyBundle
from ..k8s.csr_resource import CSRResource
from . import StepReturn, BaseStep, EndStep, WorkflowBase


class GetCSRandKeyStep(BaseStep):

    name = "get_csr_and_key"

    def __init__(self, inputs):
        self.in_key = inputs.get("in_key")
        self.in_key_password = inputs.get("in_key_password")
        self.in_csr = inputs.get("in_csr")
        self.metadata = inputs.get("metadata")
        super().__init__(inputs)

    def run(self) -> StepReturn:
        self.user.candk = CSRandKey(
            common_name=self.user.name,
            key_file=self.in_key,
            key_file_password=self.in_key_password,
            csr_file=self.in_csr,
        )
        self.user.csr_resource = CSRResource(
            name=self.user.name,
            csr_str=self.user.candk.csr.base64,
            metadata=self.metadata,
        )
        return StepReturn(
            next_step="save_key",
            message=(
                f"key {'created' if self.user.candk.key.created else 'loaded'}; "
                f"csr {'created' if self.user.candk.csr.created else 'loaded'}"
            ),
        )


class SaveKeyStep(BaseStep):

    name = "save_key"

    def __init__(self, inputs):
        self.in_key = inputs.get("in_key")
        self.creds_dir = inputs.get("creds_dir")
        super().__init__(inputs)

    def run(self) -> StepReturn:
        saved = False
        if self.creds_dir and not self.in_key:
            key_path = os.path.join(self.creds_dir, f"{self.user.name}.key.pem")
            if os.path.exists(key_path):
                raise Exception(f"Key already exists at {key_path}")
            self.user.candk.key.save(key_path)
            saved = True
        return StepReturn(
            next_step="save_csr",
            message=f"key saved to {key_path}" if saved else "skipped save",
        )


class SaveCSRStep(BaseStep):

    name = "save_csr"

    def __init__(self, inputs):
        self.in_csr = inputs.get("in_csr")
        self.creds_dir = inputs.get("creds_dir")
        super().__init__(inputs)

    def run(self) -> StepReturn:
        saved = False
        if self.creds_dir and not self.in_csr:
            csr_path = os.path.join(self.creds_dir, f"{self.user.name}.csr.pem")
            self.user.candk.csr.save(csr_path)
            saved = True
        return StepReturn(
            next_step="csr_resource_exists",
            message=f"csr saved to {csr_path}" if saved else "skipped save",
        )


class ResourceExistsStep(BaseStep):

    name = "csr_resource_exists"

    def run(self) -> StepReturn:
        exists = self.user.csr_resource.resource_exists(self.api_client)
        if exists:
            return StepReturn(
                next_step="csr_approve_resource", message="csr resource exists"
            )
        return StepReturn(
            next_step="csr_create_resource", message="csr resource does not exist yet."
        )


class CreateResourceStep(BaseStep):

    name = "csr_create_resource"

    def run(self) -> StepReturn:
        self.user.csr_resource.create(self.api_client)
        return StepReturn(
            next_step="csr_approve_resource", message="csr resource created"
        )


class ApproveResourceStep(BaseStep):

    name = "csr_approve_resource"

    def run(self) -> StepReturn:
        self.user.csr_resource.approve(self.api_client)
        return StepReturn(next_step="get_cert", message="csr resource approved")


class GetCertStep(BaseStep):

    name = "get_cert"

    def run(self) -> StepReturn:
        cert_str = self.user.csr_resource.get_cert(self.api_client)
        self.user.crt = Cert(crt_data=base64.b64decode(cert_str))
        return StepReturn(next_step="save_cert", message="crt retrieved from k8s")


class SaveCertStep(BaseStep):

    name = "save_cert"

    def __init__(self, inputs):
        self.creds_dir = inputs.get("creds_dir")
        super().__init__(inputs)

    def run(self) -> StepReturn:
        saved = False
        if self.creds_dir:
            crt_path = os.path.join(self.creds_dir, f"{self.user.name}.crt.pem")
            self.user.crt.save(crt_path)
            saved = True
        return StepReturn(
            next_step="make_kubeconfig",
            message=f"crt saved to {crt_path}" if saved else "skipped save",
        )


class MakeKubeConfigStep(BaseStep):

    name = "make_kubeconfig"

    def __init__(self, inputs):
        self.cluster_name = inputs.get("cluster_name")
        self.context_name = inputs.get("context_name")
        self.kubeconfig_klass = inputs.get("kubeconfig_klass")
        super().__init__(inputs)

    def run(self) -> StepReturn:
        keybundle = KeyBundle(
            user_name=self.user.name,
            user_key=self.user.candk.key.base64,
            user_csr=self.user.candk.key.base64,
            user_cert=self.user.crt.base64,
        )
        self.user.kubeconfig = self.kubeconfig_klass(
            self.api_client, self.cluster_name, self.context_name, keybundle,
        )
        self.user.kubeconfig_dict = self.user.kubeconfig.generate()

        return StepReturn(next_step="save_kubeconfig", message="kubeconfig generated")


class SaveKubeconfigStep(BaseStep):

    name = "save_kubeconfig"

    def __init__(self, inputs):
        self.out_kubeconfig = inputs.get("out_kubeconfig")
        super().__init__(inputs)

    def run(self) -> StepReturn:
        self.user.kubeconfig.save(self.out_kubeconfig)
        return StepReturn(
            next_step="end", message=f"kubeconfig saved to {self.out_kubeconfig}"
        )


class UserCSRWorkflow(WorkflowBase):
    steps = [
        GetCSRandKeyStep,
        SaveKeyStep,
        SaveCSRStep,
        ResourceExistsStep,
        CreateResourceStep,
        ApproveResourceStep,
        GetCertStep,
        SaveCertStep,
        MakeKubeConfigStep,
        SaveKubeconfigStep,
        EndStep,
    ]

    def get_start_step(self):
        return GetCSRandKeyStep
