import argparse
from fastapi import FastAPI
from pydantic import BaseModel
import uvicorn
import blink.ner as NER
from typing import Union, List
from blink.main_dense import _annotate

class Item(BaseModel):
    text: Union[List[str], str]

app = FastAPI()

@app.post('/api/ner')
async def encode_mention(item: Item):
    if isinstance(item.text, str):
        texts = [item.text]
    else:
        texts = item.text
    samples = _annotate(ner_model, texts)
    return samples

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--host", type=str, default="127.0.0.1", help="host to listen at",
    )
    parser.add_argument(
        "--port", type=int, default="30304", help="port to listen at",
    )

    args = parser.parse_args()

    print('Loading NER model...')
    # Load NER model
    ner_model = NER.get_model()
    print('Loading complete.')

    uvicorn.run(app, host = args.host, port = args.port)
