import uvicorn
import argparse
import pandas as pd
from fastapi import FastAPI, Body
from pydantic import BaseModel
from typing import List, Optional, Dict
from pathlib import Path
from datetime import datetime
from gatenlp import Document
from merge_sets import create_best_NER_annset

app = FastAPI()

MAXIMUM_PER_PARTS = 6
MAXIMUM_PARTS = 10

def get_annset_exclusion_list(doc, annset_priority):
  exclusion_list = []
  for annset_key in doc['annotation_sets']:
    if annset_key not in annset_priority:
      exclusion_list.append(annset_key)
  return exclusion_list

def get_annset_priority(doc, annset_priority):
  if annset_priority is None:
    annset_priority = dict()
    for annset_key in doc['annotation_sets']:
      annset_priority[annset_key] = 1
  return annset_priority

class Body(BaseModel):
    doc: dict
    merged_name: str
    annset_priority: dict = None

@app.post('/api/merge-sets')
async def run(body: Body):
  doc = body.doc
  merged_name = body.merged_name
  annset_priority = get_annset_priority(doc, body.annset_priority)
  exclusion_list = get_annset_exclusion_list(doc, annset_priority)
  doc = Document.from_dict(doc)
  type_relation_df = pd.read_csv(args.path_to_type_relation_csv)
  annset_name = 'entities_' + merged_name
  
  doc = create_best_NER_annset(doc, exclusion_list, annset_name, type_relation_df, annset_priority, MAXIMUM_PER_PARTS, MAXIMUM_PARTS)

  return doc.to_dict()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--host", type=str, default="127.0.0.1", help="host to listen at",
    )
    parser.add_argument(
        "--port", type=int, default="30310", help="port to listen at",
    )
    parser.add_argument(
        "--path-to-type-relation-csv", type=int, default=None, dest='path_to_type_relation_csv', help="Path to type realtion csv",
    )

    args = parser.parse_args()

    if args.path_to_type_relation_csv is None:
        args.path_to_type_relation_csv = './data/type_relation_df.csv'

    uvicorn.run(app, host = args.host, port = args.port)