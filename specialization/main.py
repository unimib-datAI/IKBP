import argparse
from fastapi import FastAPI, Body
import uvicorn
from gatenlp import Document
from fakeCandidates import fake_candidates
import requests
from pydantic import BaseModel
from typing import List
from verbalizer import VERBALIZER, ANCESTOR_MAP

import os
from dotenv import load_dotenv

from specialization.utils_prompt import Prompting, VanillaClf, get_annotated_example

load_dotenv()

PIPELINE_ADDRESS = os.getenv('PIPELINE_ADDRESS')
API_GET_DOCUMENT = f'{PIPELINE_ADDRESS}/api/mongo/document'

class FewShotInput(BaseModel):
    type_id: str

class ZeroShotInput(BaseModel):
    type_id: str
    verbalizer: List[str]

app = FastAPI()

# NOTE: serve solo per la demo
@app.post('/api/specialization/few')
async def get_few(body: FewShotInput):
    type_id = body.type_id
    annotation_set = 'PoC_test_fewshot'
    # get all documents
    documents = requests.get(f'{API_GET_DOCUMENT}?limit=9999').json()['docs']
    examples = []
    # filter by annotation_set
    for doc in documents:
        # get complete document
        doc_id = doc["id"]
        doc = requests.get(f'{API_GET_DOCUMENT}/{str(doc_id)}')
        doc = doc.json()
        annotation_sets = doc["annotation_sets"]
        if annotation_set in annotation_sets:
            example, _ = get_annotated_example(doc, annotation_set, type_id=type_id, span=50,  doc_id=int(doc_id))
            examples.extend(example)

    return examples

@app.post('/api/specialization/zero')
async def get_zero(body: ZeroShotInput):
    type_id = body.type_id
    original_type = ANCESTOR_MAP[type_id]
    verbalizer = body.verbalizer
    annotation_set = 'PoC_specialization_template' # TODO: rendere dinamico dopo la PoC
    # get all documents
    documents = requests.get(f'{API_GET_DOCUMENT}?limit=9999').json()['docs']
    examples = []
    # filter by annotation_set and type_id
    for doc in documents:
        # get complete document
        doc_id = doc["id"]
        doc = requests.get(f'{API_GET_DOCUMENT}/{str(doc_id)}')
        doc = doc.json()
        ann_names = doc.annset_names()
        if annotation_set in ann_names:
            example, _ = get_annotated_example(doc, annotation_set, type_id=original_type, span=50,  doc_id=int(doc_id))
            examples.extend(example)
    # prepare types and verbalizer for prompting
    spec_type = type_id
    original_keywords = VERBALIZER[original_type]
    spec_keywords = verbalizer
    # remove keywords from original verbalizer if they are in specialization verbalizer
    original_keywords = list(set(original_keywords) - set(spec_keywords))
    # masked language prediction
    template = 'Il {mention} è un [MASK].'
    X = prompt_model.examples_prediction(examples, template)
    # build verbalizer
    verb_spec = {original_type:original_keywords, spec_type:spec_keywords}
    # Zero Shot prediction
    zs_clf = VanillaClf()
    # compute posterior for original_other and specialization type
    pred_proba_zs = zs_clf.predict_proba(X=X, verbalizer=verb_spec, tokenizer=prompt_model.tokenizer)
    proba_spec = pred_proba_zs[spec_type].to_numpy()
    # predicted class with zero shot
    pred_zs = pred_proba_zs.idxmax(axis=1).to_numpy()
    # add zero shot informations and reorder examples
    for i, example in enumerate(examples):
        example['predict_proba'] = float(proba_spec[i])
        example['predict_type'] = pred_zs[i]
    idx_order = (-proba_spec).argsort()
    reorder_example = [examples[i] for i in idx_order]
    return reorder_example

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--host", type=str, default="127.0.0.1", help="host to listen at",
    )
    parser.add_argument(
        "--port", type=int, default="30311", help="port to listen at",
    )
    
    args = parser.parse_args()

    # setup model
    model_name = "dlicari/Italian-Legal-BERT"
    prompt_model = Prompting(model_name)

    uvicorn.run(app, host = args.host, port = args.port)