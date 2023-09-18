import os

import asyncio
from fastapi import FastAPI
from pydantic import BaseModel
from typing import Optional, List
from fastapi.responses import StreamingResponse
from fastapi import FastAPI
from transformers import LlamaForCausalLM, LlamaTokenizer
from peft import PeftModel
from utils import generate_streaming_completion, generate_completion, prepare_message
import traceback
import torch
import os


# [init torch]:
torch.set_grad_enabled(False)
torch.cuda._lazy_init()
torch.backends.cuda.matmul.allow_tf32 = True
# torch.backends.cuda.matmul.allow_fp16_reduced_precision_reduction = True
torch.set_printoptions(precision=10)
torch_devices = [f"cuda:{i}" for i in range(torch.cuda.device_count())]

# Setup FastAPI:
app = FastAPI()
semaphore = asyncio.Semaphore(1)


# fastapi_chat.html uses this to check what model is being used.
# (My Webserver uses this to check if my LLM is running):
@app.get("/check")
def check():
    # just return name without path or safetensors so we don't expose local paths:
    model = os.path.basename(MODEL)

    return {model}


class CountTokensRequest(BaseModel):
    inputs: str


@app.post("/count-tokens")
def count_tokens(req: CountTokensRequest):
    ids = model.tokenize(req.inputs)
    return ids.shape[-1]


class GenerateRequest(BaseModel):
    messages: List[dict]
    max_new_tokens: Optional[int] = 200
    temperature: Optional[float] = 0.7
    top_k: Optional[int] = 20
    top_p: Optional[float] = 0.65
    min_p: Optional[float] = 0.06
    token_repetition_penalty_max: Optional[float] = 1.15
    token_repetition_penalty_sustain: Optional[int] = 256
    token_repetition_penalty_decay: Optional[int] = None
    stream: Optional[bool] = True
    num_beams: Optional[int] = 1


# def get_prompt(message: str, chat_history: list[tuple[str, str]],
#                system_prompt: str) -> str:
def get_prompt(message, chat_history,
                system_prompt):
    texts = [f'<s>[INST] <<SYS>>\n{system_prompt}\n<</SYS>>\n\n']
    # The first user input is _not_ stripped
    do_strip = False
    for user_input, response in chat_history:
        user_input = user_input.strip() if do_strip else user_input
        do_strip = True
        texts.append(f'{user_input} [/INST] {response.strip()} </s><s>[INST] ')
    message = message.strip() if do_strip else message
    texts.append(f'{message} [/INST]')
    return ''.join(texts)


@app.post("/generate")
async def stream_data(req: GenerateRequest):
    while True:
        try:
            # Attempt to acquire the semaphore without waiting, in a loop...
            await asyncio.wait_for(semaphore.acquire(), timeout=0.1)
            break
        except asyncio.TimeoutError:
            print("Server is busy")
            await asyncio.sleep(1)

    try:
        # # Set these from GenerateRequest:
        # model.generator.settings = ExLlamaGenerator.Settings()
        # model.generator.settings.temperature = req.temperature
        # model.generator.settings.top_k = req.top_k
        # model.generator.settings.top_p = req.top_p
        # model.generator.settings.min_p = req.min_p
        # model.generator.settings.token_repetition_penalty_max = (
        #     req.token_repetition_penalty_max
        # )
        # model.generator.settings.token_repetition_penalty_sustain = (
        #     req.token_repetition_penalty_sustain
        # )
        # decay = int(
        #     req.token_repetition_penalty_decay
        #     if req.token_repetition_penalty_decay
        #     else req.token_repetition_penalty_sustain / 2
        # )
        # model.generator.settings.token_repetition_penalty_decay = decay

        _MESSAGE, max_new_tokens = prepare_message(
            messages=req.messages,
            max_new_tokens=req.max_new_tokens,
        )

        if req.stream:
            # copy of generate_simple() so that I could yield each token for streaming without having to change generator.py and make merging updates a nightmare:
            print('stream')
            streamer = generate_streaming_completion({
                    'model': model,
                    'tokenizer': tokenizer,
                    'model_options': req,
                    'message': _MESSAGE
                })
            return StreamingResponse(streamer)
        else:
            return generate_completion({
                    'model': model,
                    'tokenizer': tokenizer,
                    'model_options': req,
                    'message': _MESSAGE
                })
    except Exception as e:
        print(traceback.format_exc())
        print('Exception', e, flush=True)
        return {"response": f"Exception while processing request: {e}"}

    finally:
        semaphore.release()

######

MODEL = os.environ.get('TEXT_GENERATION_MODEL')
WEIGHTS = os.environ.get('TEXT_GENERATION_WEIGHTS', '')

# Comma-separated list of VRAM (in GB) to use per GPU device for model layers, e.g. -gs 20,7,7
GPU_SPLIT= os.environ.get('TEXT_GENERATION_GPU_SPLIT', '')

tokenizer = LlamaTokenizer.from_pretrained(MODEL, add_eos_token=True, use_fast=True)
model = LlamaForCausalLM.from_pretrained(
    MODEL,
    load_in_8bit=True,
    torch_dtype=torch.float16,
    device_map="auto",
)
model = PeftModel.from_pretrained(
  model, 
  WEIGHTS, 
  device_map="auto",
  torch_dtype=torch.float16
)

print('device on', model.device)