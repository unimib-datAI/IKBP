from __future__ import annotations
import os, glob

from prompts import llama_v2_prompt, cerbero_prompt
from llama_cpp import Llama
from huggingface_hub import hf_hub_download
import asyncio


class PhiModel:
    def __init__(self, n_gpu_layers=-1):

        # self.llm = Llama(
        #     model_path=hf_hub_download(
        #         repo_id="QuantFactory/Phi-3.5-mini-ITA-GGUF",
        #         filename="Phi-3.5-mini-ITA.Q8_0.gguf",
        #     ),
        #     n_ctx=20000,
        #     n_gpu_layers=n_gpu_layers,
        # )
        self.llm = None

    def tokenize(self, inputs: str):
        return self.tokenizer.encode(inputs)

    def prepare_message(
        self,
        messages: list[dict],
        max_new_tokens: int,
        min_token_reply: int = 256,
    ):
        return (
            cerbero_prompt(messages, max_new_tokens, min_token_reply),
            max_new_tokens,
        )

    async def generate_stream(
        self,
        inputs: str,
        max_new_tokens: int,
        temperature: float,
        top_k: int,
        top_p: float,
        min_p: float,
        token_repetition_penalty_max: float,
        token_repetition_penalty_sustain: int,
        token_repetition_penalty_decay: int,
    ):
        max_new_tokens = min(max_new_tokens, 4096)
        try:
            stream = self.llm(
                inputs,
                max_tokens=max_new_tokens,
                temperature=temperature,
                top_k=top_k,
                top_p=top_p,
                repeat_penalty=token_repetition_penalty_max,
                min_p=min_p,
                stop=[
                    "[|Assistente|]",
                    "[/USER]",
                    "[/INST]",
                    "[INST]",
                    "[|Umano|]",
                    "[/INST]",
                ],
                stream=True,
            )
            for output in stream:
                yield output["choices"][0]["text"]
                await asyncio.sleep(0.01)
                # stop if the output is empty
                if not output:
                    break
        except Exception as e:
            print("Error during text generation: ", e)
            yield f"Error {str(e)}"

    def generate(self, inputs, max_new_tokens):
        # No streaming, using generate_simple:
        response = self.generator.generate_simple(inputs, max_new_tokens)
        # print(text)

        # remove prompt from response:
        response = response.replace(inputs, "")
        response = response.lstrip()

        # return response time here?
        return {response}
