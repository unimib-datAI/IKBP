from __future__ import annotations
from exllama.model import ExLlama, ExLlamaCache, ExLlamaConfig
from exllama.tokenizer import ExLlamaTokenizer
from exllama.generator import ExLlamaGenerator
import os, glob
from LLM import LLM
from prompts import llama_v2_prompt


class EXLlamaModel(LLM):
    def _load(self, model_directory: str, gpu_split: str = None):
        tokenizer_path = os.path.join(model_directory, "tokenizer.model")
        model_config_path = os.path.join(model_directory, "config.json")
        st_pattern = os.path.join(model_directory, "*.safetensors")
        model_path = glob.glob(st_pattern)[0]

        self.config = ExLlamaConfig(model_config_path)  # create config from config.json
        self.config.model_path = model_path  # supply path to model weights file
        self.config.set_auto_map(gpu_split)
        if "8k" in model_directory.lower():
            self.config.max_seq_len = 8192
            self.config.compress_pos_emb = 4
        else:
            self.config.max_seq_len = 2048
        print("created config")

        self.instance = ExLlama(
            self.config
        )  # create ExLlama instance and load the weights
        print("loaded model")
        self.tokenizer = ExLlamaTokenizer(
            tokenizer_path
        )  # create tokenizer from tokenizer model file
        print("loaded tokenizer")

        self.cache = ExLlamaCache(self.instance)  # create cache for inference
        print("created cache")
        self.generator = ExLlamaGenerator(
            self.instance, self.tokenizer, self.cache
        )  # create generator
        print("created generator")

    def tokenize(self, inputs: str):
        return self.tokenizer.encode(inputs)

    def prepare_message(
        self,
        messages: list[dict],
        max_new_tokens: int,
        min_token_reply: int = 256,
    ):
        return (
            llama_v2_prompt(messages, max_new_tokens, min_token_reply),
            max_new_tokens,
        )

    async def generate_stream(self, inputs: str, max_new_tokens: int):
        new_text = ""
        last_text = ""

        self.generator.end_beam_search()

        ids = self.tokenizer.encode(inputs)
        self.generator.gen_begin_reuse(ids)

        for i in range(max_new_tokens):
            token = self.generator.gen_single_token()
            text = self.tokenizer.decode(self.generator.sequence[0])
            new_text = text[len(inputs) :]

            # Get new token by taking difference from last response:
            new_token = new_text.replace(last_text, "")
            last_text = new_text

            # print(new_token, end="", flush=True)
            yield new_token

            # [End conditions]:
            # if break_on_newline and # could add `break_on_newline` as a GenerateRequest option?
            # if token.item() == tokenizer.newline_token_id:
            #    print(f"newline_token_id: {tokenizer.newline_token_id}")
            #    break
            if token.item() == self.tokenizer.eos_token_id:
                # print(f"eos_token_id: {tokenizer.eos_token_id}")
                break

        # all done:
        self.generator.end_beam_search()

    def generate(self, inputs, max_new_tokens):
        # No streaming, using generate_simple:
        response = self.generator.generate_simple(inputs, max_new_tokens)
        # print(text)

        # remove prompt from response:
        response = response.replace(inputs, "")
        response = response.lstrip()

        # return response time here?
        return {response}
