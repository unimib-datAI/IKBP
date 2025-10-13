from abc import ABC, abstractmethod


class LLM(ABC):
    def __init__(self, model_diectory: str, gpu_split: str):
        self.model_name = model_diectory
        self._load(model_diectory, gpu_split)

    @abstractmethod
    def _load(self, model_diectory: str):
        pass

    @abstractmethod
    def prepare_message(self, inputs: str):
        pass

    @abstractmethod
    def tokenize(self, inputs: str):
        pass

    @abstractmethod
    def generate_stream(self, inputs: str, max_new_tokens: int):
        pass
