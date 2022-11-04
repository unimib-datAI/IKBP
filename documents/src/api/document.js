import { Router } from 'express';
import { DocumentController } from '../controllers/document';
import { asyncRoute } from '../utils/async-route';
import { Document, documentDTO } from '../models/document';
import { validateRequest } from 'zod-express-middleware';
import { z } from 'zod';
import { AnnotationSet, annotationSetDTO } from '../models/annotationSet';
import { AnnotationSetController } from '../controllers/annotationSet';
import { Annotation, annotationDTO } from '../models/annotation';


const route = Router();

const deleteDoc = async (req, res, next) => {
  const { docId } = req.params;
  // delete document and return deleted document
  const deletedDoc = await Document.findOneAndDelete({ id: docId });
  // get all annotation sets to delete
  const annotationSets = await AnnotationSet.find({ docId });
  await Promise.all(annotationSets.map(async (annSet) => {
    // delete annotations for each annotation set
    await Annotation.deleteMany({ annotationSetId: annSet._id });
  }))
  // delete annotation sets for the document
  await AnnotationSet.deleteMany({ docId });

  if (res) {
    return res.json(deletedDoc);
  } else {
    return deletedDoc;
  }

};

export default (app) => {
  // route base root
  app.use('/document', route);

  /**
   * Get all documents
   */
  route.get('/',
    validateRequest(
      {
        req: {
          query: z.object({
            // query to find by name
            q: z.string().optional(),
            // page
            page: z.number().optional(),
            // n. of documents to return for each page
            limit: z.number().optional(),
          })
        }
      }
    ), asyncRoute(async (req, res) => {
      const { q, limit, page } = req.query;
      const documentsPage = await DocumentController.findAll(q, limit, page);
      return res.json(documentsPage).status(200);
    }));

  /**
   * Get document helper function
   *
   * anonymous: delete any reference to the database (they may be useful for updating the doc)
   */
  async function getDocumentById(id, anonymous = false, clusters = false) {
    const document = await DocumentController.findOne(id);
    // convert annotation_sets from list to object
    var new_sets = {}
    for (const annset of document.annotation_sets) {
      // delete annset._id;

      // add mention to annotations features
      if (annset.name.startsWith('entities')) {
        for (const annot of annset.annotations) {
          if (!('mention' in annot.features)) {
            annot.features.mention = document.text.substring(annot.start, annot.end);
          }
          // workaround for issue 1 // TODO remove
          if (typeof annot.id === 'string' || annot.id instanceof String) {
            annot.id = parseInt(annot.id);
          }
        }
      }

      for (const annot of annset.annotations) {
        // workaround for issue 1 // TODO remove
        if (typeof annot.id === 'string' || annot.id instanceof String) {
          annot.id = parseInt(annot.id);
        }
      }

      if (anonymous) {
        delete annset['_id'];
        delete annset['__v'];
        delete annset['docId'];
        for (const annot of annset.annotations) {
          // remove references to db
          delete annot['_id'];
          delete annot['__v'];
          delete annot['annotationSetId'];
        }
      }

      // ensure annset is sorted
      annset.annotations.sort((a, b) => a.start - b.start)

      new_sets[annset.name] = annset;
    }
    document.annotation_sets = new_sets;

    if (anonymous) {
      delete document['_id'];
      delete document['__v'];
      delete document['id'];
    }

    if (!clusters && document.features && document.features.clusters) {
      for (const [annset_name, annset_clusters] of Object.entries(document.features.clusters)) {
        for (let i = 0; i < annset_clusters.length; i++) {
          delete annset_clusters[i]["center"];
        }
      }
    }
    return document;
  }

  /**
   * Get document by id
   */
  route.get('/:id', asyncRoute(async (req, res, next) => {
    const { id } = req.params;

    const document = await getDocumentById(id);

    return res.json(document).status(200);
  }));

  /**
   * Get document by id anonymous
   */
   route.get('/anon/:id', asyncRoute(async (req, res, next) => {
    const { id } = req.params;

    const document = await getDocumentById(id, true);

    return res.json(document).status(200);
  }));

  /**
   * Get document by id anonymous
   */
   route.get('/clusters/:id', asyncRoute(async (req, res, next) => {
    const { id } = req.params;

    const document = await getDocumentById(id, false, true);

    return res.json(document).status(200);
  }));

/**
   * Update a document
   */
 route.post('/:id',
 validateRequest(
   {
     req: {
       body: z.object({
         text: z.string(),
         annotation_sets: z.object(),
         preview: z.string().optional(),
         name: z.string().optional(),
         features: z.object().optional(),
         offset_type: z.string().optional()
       })
     }
   }
 ),
 asyncRoute(async (req, res, next) => {
   // delete document // TODO ROLLBACK on Failure
   const { id } = req.params;
   const deleteResults = await deleteDoc({params: {docId: id}}, null, next);
   // new document object
   const pre_doc = req.body;
   pre_doc["id"] = id
   const newDoc = documentDTO(req.body);

   const doc = await DocumentController.insertOne(newDoc);
   // insert each annnotation set
   await Promise.all(Object.values(req.body.annotation_sets).map(async (set) => {
     const { annotations: newAnnotations, ...rest } = set;
     const newAnnSet = annotationSetDTO({ docId: doc.id, ...rest });
     const annSet = await AnnotationSetController.insertOne(newAnnSet);
     // insert all annotations for a set
     const newAnnotationsDTOs = newAnnotations.map((ann) => annotationDTO({ annotationSetId: annSet._id, ...ann }));
     await Annotation.insertMany(newAnnotationsDTOs);

     return annSet;
   }));

   return res.json(doc).status(200);
 }));


  /**
   * Create a new document
   */
  route.post('/',
    validateRequest(
      {
        req: {
          body: z.object({
            text: z.string(),
            annotation_sets: z.object(),
            preview: z.string().optional(),
            name: z.string().optional(),
            features: z.object().optional(),
            offset_type: z.string().optional()
          })
        }
      }
    ),
    asyncRoute(async (req, res, next) => {
      // new document object
      const newDoc = documentDTO(req.body);
      const doc = await DocumentController.insertOne(newDoc);
      // insert each annnotation set
      await Promise.all(Object.values(req.body.annotation_sets).map(async (set) => {
        const { annotations: newAnnotations, ...rest } = set;
        const newAnnSet = annotationSetDTO({ docId: doc.id, ...rest });
        const annSet = await AnnotationSetController.insertOne(newAnnSet);
        // insert all annotations for a set
        const newAnnotationsDTOs = newAnnotations.map((ann) => annotationDTO({ annotationSetId: annSet._id, ...ann }));
        await Annotation.insertMany(newAnnotationsDTOs);

        return annSet;
      }));

      return res.json(doc).status(200);
    }));

  route.delete('/:docId',
    asyncRoute(deleteDoc));

  route.delete('/:docId/annotation-set/:annotationSetId',
    asyncRoute(async (req, res, next) => {
      const { docId, annotationSetId } = req.params;

      const result = await AnnotationSet.deleteOne({ _id: annotationSetId })
      await Annotation.deleteMany({ annotationSetId });
      return res.json(result);
    }));
};
