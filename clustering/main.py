import argparse
from fastapi import FastAPI, Body
import uvicorn
import re
from gatenlp import Document
from utils import make_clusters
import pickle

app = FastAPI()

@app.post('/api/clustering')
async def sectionator(doc: dict = Body(...)):
    
    doc = make_clusters(doc, model)
    return doc.to_dict()

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--host", type=str, default="127.0.0.1", help="host to listen at",
    )
    parser.add_argument(
        "--port", type=int, default="30388", help="port to listen at",
    )
    parser.add_argument(
        "--model", type=str, default="/home/app/models/clustering/xgb_clustering.sav", help="model path",
    )

    args = parser.parse_args()
    model = pickle.load(open(args.model, 'rb'))
    uvicorn.run(app, host = args.host, port = args.port)