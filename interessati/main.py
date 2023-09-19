import argparse
from fastapi import FastAPI, Body
import uvicorn
from utils import rulebased_interessati

app = FastAPI()

@app.post('/api/interessati/rulebased')
async def rulebased(doc: dict = Body(...)):
    doc = rulebased_interessati(doc, annset_name=annset_name)
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
        "--annset", type=str, default="entities_consolidated", help="annset name",
    )

    args = parser.parse_args()
    annset_name =args.annset
    uvicorn.run(app, host = args.host, port = args.port)