import sys
import abc
from typing import Dict
import collections

StepReturn = collections.namedtuple("StepReturn", "next_step message")


class BaseStep(abc.ABC):

    name = "base"

    def __init__(self, inputs: Dict):
        self.user = inputs.get("user")
        self.api_client = inputs.get("api_client")

    @abc.abstractmethod
    def run(self):
        return None

    def _run(self):
        print(f"Running: {self.name}", file=sys.stdout)
        step_return = self.run()
        print(f"  {step_return.message}", file=sys.stdout)
        return step_return


class EndStep(BaseStep):

    name = "end"

    def run(self) -> StepReturn:
        return StepReturn(next_step=None, message="")


class WorkflowBase(abc.ABC):

    step_instances = {}

    def __init__(self, inputs: Dict):
        self.start_step = self.get_start_step().name
        for step_class in self.steps:
            self.step_instances[step_class.name] = step_class(inputs)

    @abc.abstractmethod
    def get_start_step(self):
        return None

    def start(self):
        step_return = StepReturn(self.start_step, "")
        while step_return.next_step:
            step_return = self.step_instances[step_return.next_step]._run()
