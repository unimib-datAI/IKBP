import * as dotenv from 'dotenv'
dotenv.config()
import Fastify from 'fastify';
import fetch from 'node-fetch';

const server = Fastify({ logger: true })

const processAnnotations = (text, annotations = []) => {
  return annotations.map((ann) => {
    const { type } = ann.features.ner;
    return {
      ...ann,
      type,
      features: {
        ...ann.features,
        mention: text.slice(ann.start, ann.end)
      }
    }
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
  const doc = await (await fetch(`${process.env.API_STATALE}/doc_id/${docId}/sorgente/${source}`)).json();
  return processStataleDocument(doc, docId);
})

// Run the server!
const start = async () => {
  try {
    await server.listen({ port: 3002 })
  } catch (err) {
    server.log.error(err)
    process.exit(1)
  }
}
start()