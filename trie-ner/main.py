import uvicorn
import argparse
from fastapi import FastAPI, Body
from pydantic import BaseModel
from TrieNER import TrieNER
from typing import List, Optional, Dict
from pathlib import Path

app = FastAPI()

@app.get('/api/trie-ner')
# async def run(doc: dict = Body(...)):
async def run():
    p = Path(args.path_to_saved_tries) / args.trie_name

    # doc = Document.from_dict(doc)

    trie = TrieNER(p)

    return trie.get_entities()



if __name__ == '__main__':
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--host", type=str, default="127.0.0.1", help="host to listen at",
    )
    parser.add_argument(
        "--port", type=int, default="30310", help="port to listen at",
    )
    parser.add_argument(
        "--path-to-saved-tries", type=int, default=None, dest='path_to_saved_tries', help="Base path to saved tries",
    )
    parser.add_argument(
        "--trie-name", type=str, default=None, dest='trie_name', help="Name of the trie to use"
    )

    args = parser.parse_args()

    if args.path_to_saved_tries is None:
        args.path_to_saved_tries = './'
    if args.trie_name is None:
        args.trie_name = 'kb'

    uvicorn.run(app, host = args.host, port = args.port)