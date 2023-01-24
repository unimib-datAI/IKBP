import * as dotenv from 'dotenv'
dotenv.config()
import Fastify from 'fastify';
import fetch from 'node-fetch';
import fs from 'fs';
import { readFile } from 'fs/promises';

const server = Fastify({ logger: true })

const getIsNil = (ann) => {
  if (ann.features.is_nil === undefined) {
    if (ann.features.linking && ann.features.linking.is_nil !== undefined) {
      return ann.features.linking.is_nil;
    }
  }

  return false;
}

const processAnnotations = (text, annotations = []) => {
  return annotations.map((ann) => {
    const { type } = ann.features.ner;
    return {
      ...ann,
      type,
      features: {
        ...ann.features,
        is_nil: getIsNil(ann),
        mention: text.slice(ann.start, ann.end)
      }
    }
  })
}

const processAnnotationsUnimib = (annotations = []) => {
  return annotations.map((ann) => {
    ann.type = ann.type.toLowerCase();
    return ann;
  })
}

const processAnnotationSets = (text, annotation_sets) => {
  return Object.values(annotation_sets).reduce((acc, ann_set) => {
    if (!ann_set.name.startsWith('entities_') && !['sentences', 'sections', 'Sections'].includes(ann_set.name)) {
      const annSetName = `entities_${ann_set.name}`;
      acc[annSetName] = {
        ...ann_set,
        name: annSetName,
        annotations: processAnnotations(text, ann_set.annotations)
      }
    } else {
      ann_set.annotations = processAnnotationsUnimib(ann_set.annotations);
      acc[ann_set.name] = ann_set;
    }

    if (ann_set.name === 'sections') {
      const annSetName = 'Sections';
      acc[annSetName] = {
        ...ann_set,
        name: annSetName,
      }
    }

    return acc;
  }, {});
}

const processStataleDocument = (doc, docId) => {
  const { annotation_sets, text, name, ...rest } = doc;
  return {
    ...rest,
    name: name || docId,
    text,
    annotation_sets: processAnnotationSets(text, annotation_sets)
  }
}

// Declare a route
server.get('/mongo/document/:id', async (request, reply) => {
  const { id } = request.params;
  const [source, docId] = id.split(/_(.*)/s);
  let doc;

  try {
    if (fs.existsSync(`/app/docs/${docId}.json`)) {
      console.log('chiamata a file');
      //file exists
      doc = JSON.parse(await readFile(`/app/docs/${docId}.json`));
    } else {
      throw 'Doc not existing';
    }
  } catch (err) {
    console.log('chiamata a unimi');
    doc = await (await fetch(`${process.env.API_STATALE}/doc_id/${docId}/sorgente/${source}`)).json();
    doc = processStataleDocument(doc, docId);
  }
  return doc;
})

server.post('/mongo/save', async (request, reply) => {
  const { docId, doc } = request.body;
  const [source, id] = docId.split(/_(.*)/s);

  const res = await (await fetch(`${process.env.API_STATALE_SAVE}/pygiustizia/update/doc/`, {
    method: 'POST',
    body: JSON.stringify({
      doc_id: id,
      doc_gatenlp: doc
    })
  })).json();

  return res;
})

// Run the server!
const start = async () => {
  try {
    await server.listen({ port: 3002, host: '0.0.0.0' })
  } catch (err) {
    server.log.error(err)
    process.exit(1)
  }
}
start()