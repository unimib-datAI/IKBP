import requests
import re
from tqdm import tqdm
from TrieNER import TrieNER

tner = TrieNER()

base_url = 'http://localhost:40080/api/mongo'

def get_documents(limit = 20):
  documents = requests.get(base_url + '/document?limit=' + str(limit))
  documents = documents.json()['docs']
  return documents

def get_document(doc_id):
  doc = requests.get(base_url + '/document/' + str(doc_id))

def get_doc_metadata(doc):
  return {
    'nomegiudice': doc['features']['nomegiudice'].rstrip(),
    'parte': doc['features']['parte'].rstrip(),
    'controparte': doc['features']['controparte'].rstrip()
  }


if __name__ == "__main__":
  docs = get_documents(999)

  persons = []
  orgs = []

  for doc in tqdm(docs):
    doc_id = doc['id']
    current_doc = requests.get(base_url + '/document/' + str(doc_id))

    if not current_doc.ok:
      continue
    current_doc = current_doc.json()

    metadata = get_doc_metadata(current_doc)
    
    # nomegiudice
    persons.append(metadata['nomegiudice'])

    # if controparte is a person
    if len(metadata['controparte'].split()) < 6 and (metadata['controparte'].replace(" ", "").isalpha() or re.sub("'", '', metadata['controparte'].replace(" ", "")).isalpha()):
      persons.append(metadata['controparte'])
    else:
      orgs.append(metadata['controparte'])
    
    # if parte is a person
    if len(metadata['parte'].split()) < 6 and (metadata['parte'].replace(" ", "").isalpha() or re.sub("'", '', metadata['parte'].replace(" ", "")).isalpha()):
      persons.append(metadata['parte'])
    else:
      orgs.append(metadata['parte'])
  
  # add persons
  tner.add_entities(persons, 'PER')
  # add orgs
  tner.add_entities(orgs, 'ORG', False)
  
  tner.save()

