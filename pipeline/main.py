from fastapi import FastAPI, Body
import requests
from gatenlp import Document
import yaml
import datetime
import os
import traceback

app = FastAPI()

config = {}

from dataclasses import dataclass

@dataclass
class PipeException(Exception):
    message: str = "This is a custom exception"

    def __str__(self):
        return f"{self.message}"

@app.post('/api/pipeline')
async def api_pipeline(doc: dict = Body(...)):
    gDoc = Document.from_dict(doc)
    return run_pipeline(gDoc).to_dict()

def call_pipe(pipe_config, gDoc):
    # TODO debug levels
    print('Calling', pipe_config['name'], flush=True)
    response = requests.post(pipe_config['url'], json=gDoc.to_dict())
    if not response.ok:
        raise PipeException(response.content)
    doc = response.json()
    doc['features']['pipelineV2'][pipe_config['name']]['result'] = 'ok'
    return Document.from_dict(doc)

def run_pipeline(gDoc):
    global config
    if 'pipelineV2' not in gDoc.features:
        gDoc.features['pipelineV2'] = {}
    gDoc.features['pipelineV2']['pipeline'] = {
        'time': datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S UTC"),
        'result': 'pending',
    }
    for pipe in config['pipeline']:
        # TODO check if pipe already done ??
        gDoc.features['pipelineV2'][pipe['name']] = {
            # 'name': pipe['name'],
            'url': pipe['url'],
            'time': datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S UTC"),
            'result': 'pending',
        }
        try:
            gDoc = call_pipe(pipe, gDoc)
        except PipeException as exc_obj:
            # TODO debug levels
            pipeline_tb = ''.join(traceback.format_exception(exc_obj))
            print(pipeline_tb, flush=True)
            gDoc.features['pipelineV2']['pipeline']['result'] = 'error'
            gDoc.features['pipelineV2']['pipeline']['traceback'] = pipeline_tb
            return gDoc

    gDoc.features['pipelineV2']['pipeline']['result'] = 'ok'
    return gDoc

def load_config(config_path):
    global config
    with open(config_path, 'r') as fd:
        config = yaml.safe_load(fd)
    assert 'pipeline' in config

load_config(os.environ.get('CONFIG_PATH', './config.yml'))

print('Started', flush=True)