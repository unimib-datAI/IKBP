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

class Req(BaseModel):
    doc_id: int # doc id
    skip_pipeline: List[str] = [] # to skip components: the component names in the list will be skipped
    rename_set: Dict = {} # to rename annotation sets #TODO

app = FastAPI()

@app.post('/api/pipeline/reannotate')
async def run(req: Req):

    res_doc = requests.get(args.mongo + f'/document/anon/{req.doc_id}')
    assert res_doc.ok

    doc = res_doc.json()
    doc = Document.from_dict(doc)

    doc.features['pipeline'] = req.skip_pipeline

    doc.features['save'] = False
    doc.features['reannotate'] = True
    doc.features['rename_set'] = req.rename_set

    return run(doc, req.doc_id)


@app.post('/api/pipeline')
async def run_pipeline(doc: dict = Body(...)):
    doc = Document.from_dict(doc)
    return run(doc)

def run(doc, doc_id = None):
    if not 'pipeline' in doc.features:
        doc.features['pipeline'] = []

    if 'sectionator' in doc.features['pipeline']:
        print('Skipping sectionator: already done')
    else:
        res_ner = requests.post(args.sectionator, json=doc.to_dict())
        if not res_ner.ok:
            raise Exception('sectionator error')
        doc = Document.from_dict(res_ner.json())

    if 'spacyner' in doc.features['pipeline']:
        print('Skipping spacyner: already done')
    else:
        res_ner = requests.post(args.spacyner, json=doc.to_dict())
        if not res_ner.ok:
            raise Exception('spacyNER error')
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

    # # if top_candidate is not NIL, then set its type as NER type #TODO study if ner is the correct place for the type
    # for annset_name in doc.annset_names():
    #     if not annset_name.startswith('entities'):
    #         # considering only annotation sets of entities
    #         continue
    #     for annotation in doc.annset(annset_name):
    #         if annotation.features['linking'].get('skip'):
    #             continue
    #         if annotation.features['linking']['top_candidate'].get('type_'):
    #             # TODO check hierarchy or combine as a different annotation
    #             if annotation.type != annotation.features['linking']['top_candidate']['type_']:
    #                 if not annotation.features.get('types'):
    #                     annotation.features['types'] = []
    #                 annotation.features['types'].append(annotation.type)
    #                 annotation._type = annotation.features['linking']['top_candidate']['type_']
    # # TODO ensure consistency between types

    if 'nilclustering' in doc.features['pipeline']:
        print('Skipping nilclustering: already done')
    else:
        res_clustering = requests.post(args.nilcluster, json=doc.to_dict())
        if not res_clustering.ok:
            raise Exception('Clustering error')
        doc = Document.from_dict(res_clustering.json())

    if 'postprocess' in doc.features['pipeline']:
        print('Skipping postprocess: already done')
    else:
        res_postprocess = requests.post(args.postprocess, json=doc.to_dict())
        if not res_postprocess.ok:
            raise Exception('postprocess error')
        doc = Document.from_dict(res_postprocess.json())

    if doc.features.get('populate', False):
        # get clusters
        res_populate = requests.post(args.indexer_add, json=doc.to_dict())
        if not res_populate.ok:
            raise Exception('Population error')
        doc = Document.from_dict(res_populate.json())

    if doc.features.get('reannotate', False):
        dict_to_save = doc.to_dict()
        # remove encodings before saving to db
        for annset in dict_to_save['annotation_sets'].values():
            for anno in annset['annotations']:
                if 'features' in anno and 'linking' in anno['features'] \
                        and 'encoding' in anno['features']['linking']:
                    del anno['features']['linking']['encoding']

        # rename annotation sets
        new_dict_to_save = dict_to_save.copy()
        del new_dict_to_save['annotation_sets']
        new_dict_to_save['annotation_sets'] = {}
        for annset_name, annset in dict_to_save['annotation_sets'].items():
            # if in rename --> rename; otherwise --> old annset_name
            new_name = dict_to_save['features'].get('rename_set', {}).get(annset_name, annset_name)

            annset['name'] = new_name

            new_dict_to_save['annotation_sets'][new_name] = annset

        dict_to_save = new_dict_to_save

        res_save = requests.post(args.mongo + f'/document/{doc_id}', json=dict_to_save)
        if not res_save.ok:
            raise Exception('Reannotate error')

    if doc.features.get('save', False):
        dict_to_save = doc.to_dict()
        # remove encodings before saving to db
        for annset in dict_to_save['annotation_sets'].values():
            for anno in annset['annotations']:
                if 'features' in anno and 'linking' in anno['features'] \
                        and 'encoding' in anno['features']['linking']:
                    del anno['features']['linking']['encoding']
        res_save = requests.post(args.mongo + '/document', json=dict_to_save)
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
        "--api-sectionator", type=str, default=None, help="sectionator URL", dest='sectionator', required=False
    )
    parser.add_argument(
        "--api-spacyner", type=str, default=None, help="spacyner URL", dest='spacyner', required=False
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
        "--api-postprocess", type=str, default=None, help="postprocess URL", dest='postprocess', required=False
    )
    parser.add_argument(
        "--api-mongo", type=str, default=None, help="mongo URL", dest='mongo', required=False
    )

    args = parser.parse_args()

    if args.sectionator is None:
        args.sectionator = args.baseurl + '/api/sectionator'
    if args.spacyner is None:
        args.spacyner = args.baseurl + '/api/spacyner'
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
    if args.postprocess is None:
        args.postprocess = args.baseurl + '/api/postprocess/doc'
    if args.mongo is None:
        args.mongo = args.baseurl + '/api/mongo'

    uvicorn.run(app, host = args.host, port = args.port)
