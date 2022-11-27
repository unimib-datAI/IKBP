import uvicorn
import argparse
from fastapi import FastAPI, Body
import json

app = FastAPI()

@app.post('/api/postprocess/doc')
async def run_api_doc(doc: dict = Body(...)):
    ### anns
    for i, annset in doc['annotation_sets'].items():
        if i.startswith('entities'):
            new_annotations = []
            for annotation in annset['annotations']:
                try:
                    del annotation['features']['linking']['encoding']
                except:
                    pass
                if annotation['type'] in LABELS_MAPPING:
                    annotation['type'] = LABELS_MAPPING[annotation['type']]
                    try:
                        _types = set([ LABELS_MAPPING[t] for t in annotation['features']['types']])
                        _types = _types - set([annotation['type']])
                        annotation['features']['types'] = list(_types)
                    except:
                        pass
                    new_annotations.append(annotation)
                    #print(annotation['type'])
            doc['annotation_sets'][i]['annotations'] = new_annotations

    ### clusters
    for annset, clusters in doc['features']['clusters'].items():
        new_clusters = []
        for i, cluster in enumerate(clusters):
            try:
                del cluster['center']
            except:
                pass
            if cluster['type'] in LABELS_MAPPING:
                #print(cluster['type'], '--->', LABELS_MAPPING.get(cluster['type'], cluster['type'].lower()))
                doc['features']['clusters'][annset][i]['type'] = LABELS_MAPPING.get(cluster['type'], cluster['type'].lower())
                new_clusters.append(cluster)
        doc['features']['clusters'][annset] = new_clusters
    return doc

if __name__ == '__main__':
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--host", type=str, default="127.0.0.1", help="host to listen at",
    )
    parser.add_argument(
        "--port", type=int, default="30310", help="port to listen at",
    )
    parser.add_argument(
        "--types-mapping", type=str, default=None, dest='types_mapping', help="Path to types mapping",
    )

    args = parser.parse_args()

    print(args.types_mapping)

    with open(args.types_mapping, 'r') as fd:
        LABELS_MAPPING = json.load(fd)

    uvicorn.run(app, host = args.host, port = args.port)
