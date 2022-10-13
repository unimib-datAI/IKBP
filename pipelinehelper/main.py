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

app = FastAPI()

@app.post('/api/pipeline')
async def run(doc: dict = Body(...)):
    doc = Document.from_dict(doc)

    if not 'pipeline' in doc.features:
        doc.features['pipeline'] = []

    if 'spacyner' in doc.features['pipeline']:
        print('Skipping spacyner: already done')
    else:
        res_ner = requests.post(args.spacyner, json=doc.to_dict())
        if not res_ner.ok:
            raise Exception('spacyNER error')
        doc = Document.from_dict(res_ner.json())

    if 'tintner' in doc.features['pipeline']:
        print('Skipping tintner: already done')
    else:
        res_ner = requests.post(args.tintner, json=doc.to_dict())
        if not res_ner.ok:
            raise Exception('tintNER error')
        doc = Document.from_dict(res_ner.json())

    if 'triener' in doc.features['pipeline']:
        print('Skipping triener: already done')
    else:
        res_ner = requests.post(args.triener, json=doc.to_dict())
        if not res_ner.ok:
            raise Exception('trieNER error')
        doc = Document.from_dict(res_ner.json())

    if 'mergener' in doc.features['pipeline']:
        print('Skipping mergener: already done')
    else:
        res_ner = requests.post(args.mergener, json=doc.to_dict())
        if not res_ner.ok:
            raise Exception('mergeNER error')
        doc = Document.from_dict(res_ner.json())

    if 'biencoder' in doc.features['pipeline']:
        print('Skipping biencoder: already done')
    else:
        res_biencoder = requests.post(args.biencoder_mention, json=doc.to_dict())
        if not res_biencoder.ok:
            raise Exception('Biencoder errror')
        doc = Document.from_dict(res_biencoder.json())

    if 'indexer' in doc.features['pipeline']:
        print('Skipping indexer: already done')
    else:
        res_indexer = requests.post(args.indexer_search, json=doc.to_dict())
        if not res_indexer.ok:
            raise Exception('Indexer error')
        doc = Document.from_dict(res_indexer.json())

    if 'nilprediction' in doc.features['pipeline']:
        print('Skipping nilprediction: already done')
    else:
        res_nilprediction = requests.post(args.nilpredictor, json=doc.to_dict())
        if not res_nilprediction.ok:
            raise Exception('NIL prediction error')
        doc = Document.from_dict(res_nilprediction.json())

    # if top_candidate is not NIL, then set its type as NER type #TODO study if ner is the correct place for the type
    for annset_name in doc.annset_names():
        if not annset_name.startswith('entities'):
            # considering only annotation sets of entities
            continue
        for annotation in doc.annset(annset_name):
            if annotation.features['linking'].get('skip'):
                continue
            if annotation.features['linking']['top_candidate'].get('type_'):
                # TODO check hierarchy or combine as a different annotation
                if annotation.type != annotation.features['linking']['top_candidate']['type_']:
                    if not annotation.features.get('types'):
                        annotation.features['types'] = []
                    annotation.features['types'].append(annotation.type)
                    annotation._type = annotation.features['linking']['top_candidate']['type_']
    # TODO ensure consistency between types

    if 'nilclustering' in doc.features['pipeline']:
        print('Skipping nilclustering: already done')
    else:
        res_clustering = requests.post(args.nilcluster, json=doc.to_dict())
        if not res_clustering.ok:
            raise Exception('Clustering error')
        doc = Document.from_dict(res_clustering.json())

    if doc.features.get('populate', False):
        # get clusters
        res_populate = requests.post(args.indexer_add, json=doc.to_dict())
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
        res_save = requests.post(args.mongo, json=dict_to_save)
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
    parser.add_argument(
        "--api-spacyner", type=str, default=None, help="spacyner URL", dest='spacyner', required=False
    )
    parser.add_argument(
        "--api-tintner", type=str, default=None, help="tintner URL", dest='tintner', required=False
    )
    parser.add_argument(
        "--api-triener", type=str, default=None, help="triener URL", dest='triener', required=False
    )
    parser.add_argument(
        "--api-mergener", type=str, default=None, help="mergener URL", dest='mergener', required=False
    )
    parser.add_argument(
        "--api-biencoder-mention", type=str, default=None, help="biencoder_mention URL", dest='biencoder_mention', required=False
    )
    parser.add_argument(
        "--api-biencoder-entity", type=str, default=None, help="biencoder_entity URL", dest='biencoder_entity', required=False
    )
    parser.add_argument(
        "--api-crossencoder", type=str, default=None, help="crossencoder URL", dest='crossencoder', required=False
    )
    parser.add_argument(
        "--api-indexer-search", type=str, default=None, help="indexer_search URL", dest='indexer_search', required=False
    )
    parser.add_argument(
        "--api-indexer-add", type=str, default=None, help="indexer_add URL", dest='indexer_add', required=False
    )
    parser.add_argument(
        "--api-indexer-reset", type=str, default=None, help="indexer_reset URL", dest='indexer_reset', required=False
    )
    parser.add_argument(
        "--api-nilpredictor", type=str, default=None, help="nilpredictor URL", dest='nilpredictor', required=False
    )
    parser.add_argument(
        "--api-nilcluster", type=str, default=None, help="nilcluster URL", dest='nilcluster', required=False
    )
    parser.add_argument(
        "--api-mongo", type=str, default=None, help="mongo URL", dest='mongo', required=False
    )

    args = parser.parse_args()

    if args.spacyner is None:
        args.spacyner = args.baseurl + '/api/spacyner'
    if args.tintner is None:
        args.tintner = args.baseurl + '/api/tintner'
    if args.triener is None:
        args.triener = args.baseurl + '/api/triener'
    if args.mergener is None:
        args.mergener = args.baseurl + '/api/mergesets/doc'
    if args.biencoder_mention is None:
        args.biencoder_mention = args.baseurl + '/api/blink/biencoder/mention/doc'
    if args.biencoder_entity is None:
        args.biencoder_entity = args.baseurl + '/api/blink/biencoder/entity'
    if args.crossencoder is None:
        args.crossencoder = args.baseurl + '/api/blink/crossencoder'
    if args.indexer_search is None:
        args.indexer_search = args.baseurl + '/api/indexer/search/doc'
    if args.indexer_add is None:
        args.indexer_add = args.baseurl + '/api/indexer/add/doc'
    if args.indexer_reset is None:
        args.indexer_reset = args.baseurl + '/api/indexer/reset/rw'
    if args.nilpredictor is None:
        args.nilpredictor = args.baseurl + '/api/nilprediction/doc'
    if args.nilcluster is None:
        args.nilcluster = args.baseurl + '/api/nilcluster/doc'
    if args.mongo is None:
        args.mongo = args.baseurl + '/api/mongo/document'

    uvicorn.run(app, host = args.host, port = args.port)
