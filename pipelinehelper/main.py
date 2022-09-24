import pandas as pd
from fastapi import FastAPI, Body
from pydantic import BaseModel
import uvicorn
from typing import List, Optional, Dict
import argparse
import requests
import numpy as np
import os
from gatenlp import Document

###
spacyner = '/api/spacyner'
tintner = '/api/tintner'
biencoder = '/api/blink/biencoder' # mention # entity
biencoder_mention = f'{biencoder}/mention/doc'
biencoder_entity = f'{biencoder}/entity'
crossencoder = '/api/blink/crossencoder'
indexer = '/api/indexer' # search # add
indexer_search = f'{indexer}/search/doc'
indexer_add = f'{indexer}/add/doc'
indexer_reset = f'{indexer}/reset/rw'
nilpredictor = '/api/nilprediction/doc'
nilcluster = '/api/nilcluster/doc'
mongo = '/api/mongo/document'
###

app = FastAPI()

@app.post('/api/pipeline')
async def run(doc: dict = Body(...)):
    doc = Document.from_dict(doc)

    if not 'pipeline' in doc.features:
        doc.features['pipeline'] = []

    if 'spacyner' in doc.features['pipeline']:
        print('Skipping spacyner: already done')
    else:
        res_ner = requests.post(args.baseurl + spacyner, json=doc.to_dict())
        if not res_ner.ok:
            raise Exception('spacyNER error')
        doc = Document.from_dict(res_ner.json())

    if 'tintner' in doc.features['pipeline']:
        print('Skipping tintner: already done')
    else:
        res_ner = requests.post(args.baseurl + tintner, json=doc.to_dict())
        if not res_ner.ok:
            raise Exception('tintNER error')
        doc = Document.from_dict(res_ner.json())

    if 'biencoder' in doc.features['pipeline']:
        print('Skipping biencoder: already done')
    else:
        res_biencoder = requests.post(args.baseurl + biencoder_mention, json=doc.to_dict())
        if not res_biencoder.ok:
            raise Exception('Biencoder errror')
        doc = Document.from_dict(res_biencoder.json())

    if 'indexer' in doc.features['pipeline']:
        print('Skipping indexer: already done')
    else:
        res_indexer = requests.post(args.baseurl + indexer_search, json=doc.to_dict())
        if not res_indexer.ok:
            raise Exception('Indexer error')
        doc = Document.from_dict(res_indexer.json())

    if 'nilprediction' in doc.features['pipeline']:
        print('Skipping nilprediction: already done')
    else:
        res_nilprediction = requests.post(args.baseurl + nilpredictor, json=doc.to_dict())
        if not res_nilprediction.ok:
            raise Exception('NIL prediction error')
        doc = Document.from_dict(res_nilprediction.json())

    if 'nilclustering' in doc.features['pipeline']:
        print('Skipping nilclustering: already done')
    else:
        res_clustering = requests.post(args.baseurl + nilcluster, json=doc.to_dict())
        if not res_clustering.ok:
            raise Exception('Clustering error')
        doc = Document.from_dict(res_clustering.json())

    if doc.features.get('populate', False):
        # get clusters
        res_populate = requests.post(args.baseurl + indexer_add, json=doc.to_dict())
        if not res_populate.ok:
            raise Exception('Population error')
        doc = Document.from_dict(res_populate.json())

    if doc.features.get('save', False):
        dict_to_save = doc.to_dict()
        # remove encodings before saving to db
        for annset in dict_to_save['annotation_sets'].values():
            for anno in annset['annotations']:
                if 'features' in anno and 'linking' in anno['features'] \
                        and 'encoding' in anno['features']['linking']:
                    del anno['features']['linking']['encoding']
        res_save = requests.post(args.baseurl + mongo, json=dict_to_save)
        if not res_save.ok:
            raise Exception('Save error')

    if not 'pipeline' in doc.features:
        doc.features['pipeline'] = []
    doc.features['pipeline'].append('pipeline')

    return doc.to_dict()

if __name__ == '__main__':

    user = os.environ.get('AUTH_USER', None)
    password = os.environ.get('AUTH_PASSWORD', None)

    if user:
        auth =(user, password)
    else:
        auth = None

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--host", type=str, default="127.0.0.1", help="host to listen at",
    )

    parser.add_argument(
        "--port", type=int, default="30310", help="port to listen at",
    )

    parser.add_argument(
        "--api-baseurl", type=str, default=None, help="Baseurl to call all the APIs", dest='baseurl', required=True
    )
    args = parser.parse_args()

    uvicorn.run(app, host = args.host, port = args.port)