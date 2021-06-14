import collections
from . import StepReturn, BaseStep, EndStep, WorkflowBase
from ..k8s.sa_resource import SAResource


TokenBundle = collections.namedtuple("TokenBundle", "user_name user_token")


class ResourceExistsStep(BaseStep):

    name = "sa_resource_exists"

    def __init__(self, inputs):
        self.name = inputs.get("name")
        self.namespace = inputs.get("namespace")
        self.metadata = inputs.get("metadata")
        super().__init__(inputs)

    def run(self) -> StepReturn:

        self.user.sa_resource = SAResource(
            name=self.user.name, namespace=self.namespace, metadata=self.metadata,
        )
        exists = self.user.sa_resource.resource_exists(self.api_client)
        return StepReturn(
            next_step="sa_get_or_create_resource",
            message="resouce exists" if exists else "resource does not exist",
        )


class GetorCreateSAStep(BaseStep):

    name = "sa_get_or_create_resource"

    def run(self) -> StepReturn:
        self.user.sa_resource.create(self.api_client)
        return StepReturn(next_step="get_token", message="token retrieved")


class GetTokenStep(BaseStep):

    name = "get_token"

    def run(self) -> StepReturn:
        token_str = self.user.sa_resource.get_token(self.api_client)
        self.user.token = token_str
        return StepReturn(next_step="make_kubeconfig", message="token generated")


class MakeKubeConfigStep(BaseStep):

    name = "make_kubeconfig"

    def __init__(self, inputs):
        self.cluster_name = inputs.get("cluster_name")
        self.context_name = inputs.get("context_name")
        self.kubeconfig_klass = inputs.get("kubeconfig_klass")
        super().__init__(inputs)

    def run(self) -> StepReturn:

        tokenbundle = TokenBundle(user_name=self.user.name, user_token=self.user.token,)
        self.user.kubeconfig = self.kubeconfig_klass(
            self.api_client, self.cluster_name, self.context_name, tokenbundle,
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


class UserTokenWorkflow(WorkflowBase):

    steps = [
        ResourceExistsStep,
        GetorCreateSAStep,
        MakeKubeConfigStep,
        GetTokenStep,
        SaveKubeconfigStep,
        EndStep,
    ]

    def get_start_step(self):
        return ResourceExistsStep
