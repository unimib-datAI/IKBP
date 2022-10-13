import uvicorn
import argparse
from fastapi import FastAPI, Body
from pydantic import BaseModel
from TrieNER import TrieNER
from typing import List, Optional, Dict
from pathlib import Path
from datetime import datetime

app = FastAPI()

ANN_SET_NAME = 'entities_trie_ner_v1.0.0'

@app.post('/api/triener')
async def run(doc: dict = Body(...)):
  annotations = tner.find_matches(doc['text'])

  ann_set = {
    'name': ANN_SET_NAME,
    'next_annid': len(annotations) + 1,
    'annotations': annotations
  }

  doc['annotation_sets'][ANN_SET_NAME] = ann_set

  return doc


if __name__ == '__main__':
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--host", type=str, default="127.0.0.1", help="host to listen at",
    )
    parser.add_argument(
        "--port", type=int, default="30310", help="port to listen at",
    )
    parser.add_argument(
        "--path-to-saved-tries", type=str, default=None, dest='path_to_saved_tries', help="Base path to saved tries",
    )
    parser.add_argument(
        "--trie-name", type=str, default=None, dest='trie_name', help="Name of the trie to use"
    )

    args = parser.parse_args()

    if args.path_to_saved_tries is None:
        args.path_to_saved_tries = './'
    if args.trie_name is None:
        args.trie_name = 'kb'

    path_to_trie = Path(args.path_to_saved_tries) / args.trie_name
    tner = TrieNER(path_to_trie)

    uvicorn.run(app, host = args.host, port = args.port)
