import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), "exllama"))

import glob
import asyncio
import uvicorn
from typing import Union
from pathlib import Path
from fastapi import FastAPI
from pydantic import BaseModel
from typing import Any, Dict, Optional, List
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI, HTTPException, Request

# from EXLlamaModel import EXLlamaModel
# from exllama.generator import ExLlamaGenerator
from cerberoModel import CerberoModel
from PhiModel import PhiModel

# exllama imports:

import argparse
import sys
import os

# [Parse arguments]:
parser = argparse.ArgumentParser(description="Simple FastAPI wrapper for ExLlama")

parser.add_argument(
    "-d",
    "--directory",
    type=str,
    help="Path to directory containing config.json, model.tokenizer and * .safetensors",
)
parser.add_argument(
    "-gl",
    "--gpu_layers",
    type=int,
    default=-1,
    help="Number of layers to put in GPU; -1 for all.",
)

args = parser.parse_args()

# Directory check:
# if args.directory is not None:
#     args.tokenizer = os.path.join(args.directory, "tokenizer.model")
#     args.config = os.path.join(args.directory, "config.json")
#     st_pattern = os.path.join(args.directory, "*.safetensors")
#     st = glob.glob(st_pattern)
#     if len(st) == 0:
#         print(f" !! No files matching {st_pattern}")
#         sys.exit()
#     if len(st) > 1:
#         print(f" !! Multiple files matching {st_pattern}")
#         sys.exit()
#     args.model = st[0]
# else:
#     if args.tokenizer is None or args.config is None or args.model is None:
#         print(" !! Please specify -d")
#         sys.exit()
# -------


# Setup FastAPI:
app = FastAPI()
semaphore = asyncio.Semaphore(1)

# I need open CORS for my setup, you may not!!
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# -------


# fastapi_chat.html uses this to check what model is being used.
# (My Webserver uses this to check if my LLM is running):
@app.get("/check")
def check():
    # just return name without path or safetensors so we don't expose local paths:
    model = os.path.basename(args.model).replace(".safetensors", "")

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
        print("generate", req.max_new_tokens)
        _MESSAGE, max_new_tokens = model.prepare_message(
            messages=req.messages,
            max_new_tokens=req.max_new_tokens,
        )

        if req.stream:
            # copy of generate_simple() so that I could yield each token for streaming without having to change generator.py and make merging updates a nightmare:
            print("temp", req.temperature)
            return StreamingResponse(
                model.generate_stream(
                    _MESSAGE,
                    max_new_tokens,
                    req.temperature,
                    req.top_k,
                    req.top_p,
                    req.min_p,
                    req.token_repetition_penalty_max,
                    req.token_repetition_penalty_sustain,
                    req.token_repetition_penalty_decay,
                ),
                media_type="text/event-stream",
            )
        else:
            return model.generate(_MESSAGE, max_new_tokens)
    except Exception as e:
        print("Exception", e)
        return {"response": f"Exception while processing request: {e}"}

    finally:
        semaphore.release()


@app.post("/generate-test")
async def stream_data_test(req: GenerateRequest):
    while True:
        try:
            # Attempt to acquire the semaphore without waiting, in a loop...
            await asyncio.wait_for(semaphore.acquire(), timeout=0.1)
            break
        except asyncio.TimeoutError:
            print("Server is busy")
            await asyncio.sleep(1)

    try:

        _MESSAGE, max_new_tokens = model.prepare_message(
            messages=req.messages,
            max_new_tokens=req.max_new_tokens,
        )

        if req.stream:
            # copy of generate_simple() so that I could yield each token for streaming without having to change generator.py and make merging updates a nightmare:
            print("temp", req.temperature)
            return StreamingResponse(
                model.generate_stream(
                    _MESSAGE,
                    max_new_tokens,
                    req.temperature,
                    req.top_k,
                    req.top_p,
                    req.min_p,
                    req.token_repetition_penalty_max,
                    req.token_repetition_penalty_sustain,
                    req.token_repetition_penalty_decay,
                )
            )
        else:
            return model.generate(_MESSAGE, max_new_tokens)
    except Exception as e:
        print("Exception", e)
        return {"response": f"Exception while processing request: {e}"}

    finally:
        semaphore.release()


# -------


if __name__ == "__main__":
    model = PhiModel(args.gpu_layers)

    # -------

    # [start fastapi]:
    _PORT = 7862
    uvicorn.run(app, host="0.0.0.0", port=_PORT)
