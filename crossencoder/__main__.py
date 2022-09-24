import argparse
from fastapi import FastAPI
from pydantic import BaseModel
import uvicorn
from blink.main_dense import load_crossencoder, prepare_crossencoder_data, _process_crossencoder_dataloader, _run_crossencoder
from blink.crossencoder.train_cross import modify
from typing import List, Optional
import json
import psycopg
import pandas as pd

class TupleDict(object):
    def __init__(self):
        self.dict = {}
    def __getitem__(self, arg):
        try:
            return self.dict[arg[1]][arg[0]]
        except KeyError:
            return None
    def add(self, id, index_id, data):
        if index_id not in self.dict:
            self.dict[index_id] = {}
        self.dict[index_id][id] = data

def get_id2title_id2text(dbconnection, candidates):

    candidates = [c for arr in candidates for c in arr]

    cand_df = pd.DataFrame(candidates, columns=['id', 'indexer'])
    indexes = cand_df['indexer'].unique()

    def flatten(x):
        flattened = []
        for k in x:
            for i in k:
                flattened.append(i)
        return flattened

    id2title = TupleDict()
    id2text = TupleDict()

    for indexid in indexes:
        with dbconnection.cursor() as cur:
            cur.execute("""
                SELECT
                    id, indexer, title, descr
                FROM
                    entities
                WHERE
                    id in ({}) AND
                    indexer = %s;
                """.format(','.join(list(cand_df.query('indexer == {}'.format(indexid))['id'].astype(str).values))), (int(indexid),))
            id2info = cur.fetchall()

        for x in id2info:
            id2title.add(x[0], x[1], x[2])
            descr = x[3]
            if descr is None:
                descr = ''
            id2text.add(x[0], x[1], descr)

    return id2title, id2text

class Mention(BaseModel):
    label:Optional[str]
    label_id:Optional[int]
    context_left: str
    context_right:str
    mention: str
    start_pos:Optional[int]
    end_pos: Optional[int]
    sent_idx:Optional[int]

class Candidate(BaseModel):
    id: int
    title: Optional[str]
    url: Optional[str]
    indexer: int
    score: Optional[float]
    bi_score: Optional[float]
    raw_score: Optional[float]
    is_cross: Optional[bool]
    wikipedia_id: Optional[int]
    type_: Optional[str]
    norm_score: Optional[float]

class Item(BaseModel):
    samples: List[Mention]
    candidates: List[List[Candidate]]
    top_k: int

app = FastAPI()

@app.post('/api/blink/crossencoder')
async def run(item: Item):
    samples = item.samples
    samples = [dict(s) for s in samples]

    candidates = item.candidates

    top_k = item.top_k

    # converting candidates in tuples
    nns = []
    for cands in candidates:
        nn = []
        for _cand in cands:
            nn.append((_cand.id, _cand.indexer))
            # save bi score
            if _cand.score:
                _cand.bi_score = _cand.score
            # reset score
            _cand.score = -100.0
        while len(nn) < top_k:
            # all samples should have the same amount of cands
            nn.append((_cand.id, _cand.indexer))
        nns.append(nn)

    labels = [-1] * len(samples)
    keep_all = True
    logger = None

    global dbconnection
    id2title, id2text = get_id2title_id2text(dbconnection, nns)

    # prepare crossencoder data
    context_input, candidate_input, label_input = prepare_crossencoder_data(
        crossencoder.tokenizer, samples, labels, nns, id2title, id2text, keep_all,
    )

    context_input = modify(
        context_input, candidate_input, crossencoder_params["max_seq_length"]
    )

    dataloader = _process_crossencoder_dataloader(
        context_input, label_input, crossencoder_params
    )

    # run crossencoder and get accuracy
    _, index_array, unsorted_scores = _run_crossencoder(
        crossencoder,
        dataloader,
        logger,
        context_len=crossencoder_params["max_context_length"],
        device = 'cpu' if crossencoder_params["no_cuda"] else 'cuda'
    )

    for sample, _candidates, _nns, _scores in zip(samples, candidates, nns, unsorted_scores):
        for _cand, _nn, _score in zip(_candidates, _nns, _scores):
            assert _cand.id == _nn[0]
            assert _cand.indexer == _nn[1]
            _cand.score = float(_score)
            _cand.is_cross = True

        _candidates.sort(key=lambda x: x.score, reverse=True)

    return candidates

def load_models(args):
    # load crossencoder model
    with open(args.crossencoder_config) as json_file:
        crossencoder_params = json.load(json_file)
        crossencoder_params["path_to_model"] = args.crossencoder_model
    crossencoder = load_crossencoder(crossencoder_params)
    return crossencoder, crossencoder_params

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    # crossencoder
    parser.add_argument(
        "--crossencoder_model",
        dest="crossencoder_model",
        type=str,
        default="models/crossencoder_wiki_large.bin",
        help="Path to the crossencoder model.",
    )
    parser.add_argument(
        "--crossencoder_config",
        dest="crossencoder_config",
        type=str,
        default="models/crossencoder_wiki_large.json",
        help="Path to the crossencoder configuration.",
    )
    parser.add_argument(
        "--host", type=str, default="127.0.0.1", help="host to listen at",
    )
    parser.add_argument(
        "--port", type=int, default="30302", help="port to listen at",
    )
    parser.add_argument(
        "--postgres", type=str, default=None, help="postgres url (e.g. postgres://user:password@localhost:5432/database)",
    )

    args = parser.parse_args()

    assert args.postgres is not None, 'Error. postgres url is required.'
    dbconnection = psycopg.connect(args.postgres)

    print('Loading crossencoder...')
    crossencoder, crossencoder_params = load_models(args)
    print('Loading complete.')

    uvicorn.run(app, host = args.host, port = args.port)
