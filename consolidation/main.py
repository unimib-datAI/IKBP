import argparse
from fastapi import FastAPI, Body
import uvicorn
from utils import consolidation
import json # debug

app = FastAPI()

@app.post('/api/consolidation')
async def sectionator(doc: dict = Body(...)):
    
    doc = consolidation(doc)

    return doc

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--host", type=str, default="127.0.0.1", help="host to listen at",
    )
    parser.add_argument(
        "--port", type=int, default="30388", help="port to listen at",
    )

    args = parser.parse_args()
    uvicorn.run(app, host = args.host, port = args.port)