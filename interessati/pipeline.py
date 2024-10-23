import requests
from utils import rulebased_interessati
from gatenlp import Document
import json

with open('doc_1.json','r') as f:
    doc = Document.from_dict(json.load(f))

doc = {'text': doc.text, 'features':{'id':doc.features['id']}}

# ner
res = requests.post('http://10.0.0.113:10880/api/pipeline', json = doc)
doc = res.json()
# with open("doc_1_processed.json", "w") as outfile:
#     outfile.write(json.dumps(doc))
doc['annotation_sets'].pop('entities_consolidated')
doc['features']['clusters'].pop('entities_consolidated')
res = requests.post('http://10.0.0.113:10880/api/consolidation', json = doc)
doc = res.json()
doc = rulebased_interessati(doc, annset_name='entities_consolidated')
doc = doc.to_dict()
x = 0