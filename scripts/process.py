import requests
from tqdm import tqdm
import sys

base_url = sys.argv[1]

documents = requests.get(base_url + '/api/mongo/document/?limit=10000')
assert documents.ok
#
documents = documents.json()['docs']
# documents = [{'id': 54}]

def pipeline(jdoc):
    text = jdoc['text']
    # call pipeline
    body = {
        'text': text,
        'features': {
            'pipeline': [
                    'biencoder',
                    'indexer',
                    'nilprediction',
                    'nilclustering'
                ]
            }
        }
    res = requests.post(base_url + '/api/pipeline', json=body)
    if not res.ok:
        print('Error', doc_id)
        return
    body = {
            'docId': current_doc.json()['id'],
            'annotationSets': res.json()['annotation_sets']
            }
    saved = requests.post(base_url + '/api/mongo/save/', json=body)
    if not saved.ok:
        print('Error save', doc_id)


def clustering(jdoc, doc_id):
    #getting encodings with biencoder
    try:
        if 'clustering' in jdoc['features']['pipeline']:
            return
        biencoder = base_url + '/api/blink/biencoder/mention/doc'
        jdoc['features']['pipeline'] = [i for i in jdoc['features']['pipeline'] if i != 'biencoder']
        resbi = requests.post(biencoder, json=jdoc)
        assert resbi.ok
        jdoc = resbi.json()
        api = base_url + '/api/clustering'
        res = requests.post(api, json = jdoc)
        assert res.ok
        jdoc = res.json()

        for anno in jdoc['annotation_sets']['entities_merged']['annotations']:
            if 'features' in anno and 'linking' in anno['features'] \
                    and 'encoding' in anno['features']['linking']:
                del anno['features']['linking']['encoding']

        #import pdb
        #pdb.set_trace()

        mongo = base_url + f'/api/mongo/document/{doc_id}'
        res_save = requests.post(mongo, json=jdoc)
        assert res_save.ok
    except:
        print('fail', doc_id)
        pass

for doc in tqdm(documents):
    doc_id = doc['id']
    #print(doc_id)
    current_doc = requests.get(base_url + '/api/mongo/document/' + str(doc['id']))
    if not current_doc.ok:
        print('Skipped', doc_id)
        continue

    jdoc = current_doc.json()
    clustering(jdoc, doc_id)

