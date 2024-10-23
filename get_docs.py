import requests
import json
import os

docs_res = requests.get('http://10.0.0.113:10880/api/mongo/document?q=&page=1&limit=5000')
if not docs_res.ok:
    print('fail list')

doc_list = docs_res.json()['docs']

os.mkdir('data/docs_davedemosett23_50')
for doc in doc_list:
    res = requests.get('http://10.0.0.113:10880/api/mongo/document/anon/{}'.format(doc['id']))
    if not res.ok:
        print('error', doc['id'])
    jdoc = res.json()
    with open('data/docs_davedemosett23_50/doc_{}.json'.format(doc['id']), 'w') as fd:
        json.dump(jdoc, fd)

