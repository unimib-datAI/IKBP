import argparse
from fastapi import FastAPI, Body
from pydantic import BaseModel
import uvicorn
from typing import Union, List
import sys
import itertools
import json
import requests
# from multiprocessing import Pool
from entity import EntityMention

from gatenlp import Document

DEFAULT_TAG='aplha_v0.1.0_tint'

class Item(BaseModel):
    text: str

app = FastAPI()

def restructure_newline(text):
  return text.replace('\n', ' ')

@app.post('/api/tintner')
async def encode_mention(doc: dict = Body(...)):

    # replace wrong newlines
    text = restructure_newline(doc['text'])

    doc = Document.from_dict(doc)
    # TODO tint sentences
    entity_set = doc.annset(f'entities_{DEFAULT_TAG}')

    tint_out = nlp_tint(text)

    for ent in tint_out:
        if ent.type_ == 'O':
            continue
        if ent.type_ == 'DATE':
            entity_set.add(ent.begin, ent.end, ent.type_, {
                "ner": {
                    "type": ent.type_,
                    "score": 1.0,
                    "normalized_date": ent.attrs['normalized_date'],
                    "source": "tint",
                    },
                "linking": {
                    "skip": True, # we already have normalized date
                }})
        else:
            entity_set.add(ent.begin, ent.end, ent.type_, {
                "ner": {
                    "type": ent.type_,
                    "score": 1.0,
                    "source": "tint",
                }})

    if not 'pipeline' in doc.features:
        doc.features['pipeline'] = []
    doc.features['pipeline'].append('tintner')

    return doc.to_dict()

def nlp_tint(text):
    global args

    # TODO async
    # tint_async = pool.apply_async(tint, (x, args.tint))
    # res_tint = tint_async.get()

    if not args.tint:
        return []

    ents, res = tint(text, baseurl=args.tint)

    if res.ok:
        ents = EntityMention.group_from_tint(ents, '', False, doc=text)
    else:
        # tint error # TODO
        return []

    return ents

def tint(text, format_='json', baseurl='http://127.0.0.1:8012/tint'):
    if len(text) > 0:
        payload = {
            'text': text,
            'format': format_
        }
        res = requests.post(baseurl, data=payload)
        if res.ok:
            # success
            return json.loads(res.text), res
        else:
            return None, res
    else:
        print('WARNING: Tint Server Wrapper got asked to call tint with empty text.', file=sys.stderr)
        return None, None

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--host", type=str, default="127.0.0.1", help="host to listen at",
    )
    parser.add_argument(
        "--port", type=int, default="30304", help="port to listen at",
    )
    parser.add_argument(
        "--tint", type=str, default=None, help="tint URL",
    )
    parser.add_argument(
        "--tag", type=str, default=DEFAULT_TAG, help="AnnotationSet tag",
    )

    # pool to run tint in parallel # TODO
    #pool = Pool(1)

    args = parser.parse_args()

    uvicorn.run(app, host = args.host, port = args.port)
