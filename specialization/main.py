import argparse
from fastapi import FastAPI, Body
import uvicorn
from gatenlp import Document
from fakeCandidates import fake_candidates
import requests

import os
from dotenv import load_dotenv

load_dotenv('../.env')

PIPELINE_ADDRESS = os.getenv('PIPELINE_ADDRESS')
API_GET_DOCUMENT = '/api/mongo/document'


app = FastAPI()

# NOTE: serve solo per la demo
@app.get('/api/specialization/few-shot-examples')
async def get_few_shot_examples(type_info: dict = Body(...)):
    type_id = type_info['key']
    annotation_set = 'PoC_test_fewshot'
    # get all documents
    documents = requests.get(f'{API_GET_DOCUMENT}?limit=9999').json()['docs']
    documents_filtered = []
    # filter by annotation_set
    for doc in documents:
        # get complete document
        doc_id = doc["id"]
        doc = requests.get(f'{API_GET_DOCUMENT}/{str(doc_id)}')
        doc = doc.json()
        annotation_sets = doc["annotation_sets"]
        if annotation_set in annotation_sets:
            documents_filtered.append(doc)
    # TODO: ricostruire stesso formato di zero-shot-candidates 
    # prendere annotazioni da documents_filtered filtrando per tipo
    examples = fake_candidates
    return examples

@app.get('/api/specialization/zero-shot-candidates')
async def get_zero_shot_candidates(type_info: dict = Body(...)):
    type_id = type_info['key']
    verbalizer = type_info['verbalizer']
    print(type_id)
    print(verbalizer)

    annotation_set = 'PoC_specialization_template' # TODO: rendere dinamico dopo la PoC
    # TODO: metodo riccardo che usa modello istanziato e ritorna i candidati nel formato corretto
    candidates = fake_candidates
    return candidates



if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--host", type=str, default="127.0.0.1", help="host to listen at",
    )
    parser.add_argument(
        "--port", type=int, default="30311", help="port to listen at",
    )
    
    args = parser.parse_args()

    uvicorn.run(app, host = args.host, port = args.port)