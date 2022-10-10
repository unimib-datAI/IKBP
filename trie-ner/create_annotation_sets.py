from TrieNER import TrieNER
import requests
from tqdm import tqdm

BASE_URL = 'http://10.0.2.29'
ANN_SET_NAME = 'entities_trie_ner_v1.1.0'

tner = TrieNER('./kb')

documents = requests.get(BASE_URL + '/api/mongo/document?limit=99999')
documents = documents.json()['docs']


for doc in tqdm(documents):
  doc_id = doc['id']
  full_doc = requests.get(BASE_URL + '/api/mongo/document/' + str(doc_id))
  full_doc = full_doc.json()
  text = full_doc['text']

  
  annotations = tner.find_matches(text)
  ann_set = {
    'name': ANN_SET_NAME,
    'next_annid': len(annotations) + 1,
    'annotations': annotations
  }
  full_doc['annotation_sets'][ANN_SET_NAME] = ann_set
  annotation_sets = full_doc['annotation_sets']
  body = {
    'docId': doc_id,
    'annotationSets': annotation_sets
  }
  saved = requests.post(BASE_URL + '/api/mongo/save/', json=body)
  

