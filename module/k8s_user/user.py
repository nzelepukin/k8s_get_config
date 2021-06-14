import os
from typing import Dict
import base64
import collections
from abc import ABC, abstractmethod
import yaml
from .k8s.csr_resource import CSRResource
from .k8s.kubeconfig import CSRKubeConfig, TokenKubeConfig
from .pki import Cert, CSRandKey, KeyBundle
from .workflows.csr_workflow import UserCSRWorkflow
from .workflows.sa_workflow import UserTokenWorkflow


class K8sUser(ABC):
    """Base Class for creating a user"""

    def __init__(self, name: str):
        self.name = name

    @abstractmethod
    def get_user_create_workflow_klass(self):
        return None

    @abstractmethod
    def get_kubeconfig_klass(self):
        return None

    def additional_inputs(self, inputs: Dict) -> Dict:
        return inputs

    def create(self, api_client, inputs: Dict) -> None:
        user_create_workflow_klass = self.get_user_create_workflow_klass()
        if not user_create_workflow_klass:
            raise NotImplementedError(
                "create method requires a get_user_create_workflow_klass"
            )
        self.api_client = api_client

        user_create_workflow_klass(
            inputs={
                **dict(
                    api_client=api_client,
                    kubeconfig_klass=self.get_kubeconfig_klass(),
                    user=self,
                ),
                **self.additional_inputs(inputs),
            },
        ).start()


class CSRK8sUser(K8sUser):
    def get_kubeconfig_klass(self):
        return CSRKubeConfig

    def get_user_create_workflow_klass(self):
        return UserCSRWorkflow


class TokenK8sUser(K8sUser):
    def get_kubeconfig_klass(self):
        return TokenKubeConfig

    def get_user_create_workflow_klass(self):
        return UserTokenWorkflow
