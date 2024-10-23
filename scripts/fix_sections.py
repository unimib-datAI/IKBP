import requests
from tqdm import tqdm
import sys

base_url = sys.argv[1]

documents = requests.get(base_url + '/api/mongo/document/?limit=10000')
assert documents.ok
#
documents = documents.json()['docs']
# documents = [{'id': 54}]

def fix_sections(jdoc, doc_id):
    #getting encodings with biencoder
    try:
        anns = jdoc['annotation_sets']['Sections']['annotations']
        
        new_anns = []
        prev_ann = {}
        for ann in sorted(anns, key=lambda x: x['start']):
            if ann['type'] == prev_ann.get('type'):
                if ann['end'] >= prev_ann.get('end'):
                    new_anns.append(ann)
                else:
                    new_anns.append(prev_ann)
            prev_ann = ann
        
        jdoc['annotation_sets']['Sections']['annotations'] = new_anns
        
        new_annset = jdoc['annotation_sets']['Sections']
        
        body = {
            'docId': doc_id,
            'annotationSets': [new_annset]
        }

        jdoc['annotation_sets']['Sections'] = new_annset

        #import pdb
        #pdb.set_trace()

        #remove old annset

        mongo = base_url + f'/api/mongo/document/{doc_id}'
        #mongo = base_url + f'/api/mongo/save/'
        res_save = requests.post(mongo, json=jdoc)
        #res_save = requests.post(mongo, json=body)
        assert res_save.ok
    except Exception as e:
        print(e)
        print('fail', doc_id)
        pass

for doc in tqdm(documents):
    doc_id = doc['id']
    #print(doc_id)
    current_doc = requests.get(base_url + '/api/mongo/document/anon/' + str(doc['id']))
    if not current_doc.ok:
        print('Skipped', doc_id)
        continue

    jdoc = current_doc.json()
    fix_sections(jdoc, doc_id)

