import { Router } from "express";
import { DocumentController } from "../controllers/document";
import { asyncRoute } from "../utils/async-route";
import { Document, documentDTO } from "../models/document";
import { validateRequest } from "zod-express-middleware";
import { z } from "zod";
import { AnnotationSet, annotationSetDTO } from "../models/annotationSet";
import { AnnotationSetController } from "../controllers/annotationSet";
import { Annotation, annotationDTO } from "../models/annotation";

const route = Router();

const deleteDoc = async (req, res, next) => {
  const { docId } = req.params;
  // delete document and return deleted document
  const deletedDoc = await Document.findOneAndDelete({ id: docId });
  // get all annotation sets to delete
  const annotationSets = await AnnotationSet.find({ docId });
  await Promise.all(
    annotationSets.map(async (annSet) => {
      // delete annotations for each annotation set
      await Annotation.deleteMany({ annotationSetId: annSet._id });
    })
  );
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
  app.use("/document", route);

  /**
   * Get all documents
   */
  route.get(
    "/",
    validateRequest({
      req: {
        query: z.object({
          // query to find by name
          q: z.string().optional(),
          // page
          page: z.number().optional(),
          // n. of documents to return for each page
          limit: z.number().optional(),
        }),
      },
    }),
    asyncRoute(async (req, res) => {
      const { q, limit, page } = req.query;
      const documentsPage = await DocumentController.findAll(q, limit, page);
      return res.json(documentsPage).status(200);
    })
  );

  /**
   * Get document helper function
   *
   * anonymous: delete any reference to the database (they may be useful for updating the doc)
   */
  async function getDocumentById(id, anonymous = false, clusters = false) {
    const document = await DocumentController.findOne(id);
    console.log("doc found");
    // convert annotation_sets from list to object
    var new_sets = {};
    for (const annset of document.annotation_sets) {
      // delete annset._id;

      // deduplicate sections
      if (annset.name === "Sections") {
        const new_anns = [];
        let prev_ann = {};

        annset.annotations.sort((a, b) => a.start - b.start);

        annset.annotations.forEach((ann) => {
          if (ann.type === prev_ann.type) {
            // found duplicate
            if (ann.end >= prev_ann.end) {
              new_anns.push(ann);
            } else {
              new_anns.push(prev_ann);
            }
          } else if (Object.keys(prev_ann).length !== 0) {
            new_anns.push(prev_ann);
          }
          prev_ann = ann;
        });
        // possible outcomes: 1) prev_ann is a duplicated and a better ann has been already added
        // 2) prev_ann is not a duplicated and the last ann is of a different type
        if (new_anns[new_anns.length - 1].type !== prev_ann.type) {
          // in case of 2)
          new_anns.push(prev_ann);
        }

        annset.annotations = new_anns;
      }

      // add mention to annotations features
      if (annset.name.startsWith("entities")) {
        for (const annot of annset.annotations) {
          if (!("features" in annot)) {
            annot.features = {};
          }
          if (!("mention" in annot.features)) {
            annot.features.mention = document.text.substring(
              annot.start,
              annot.end
            );
          }
          // workaround for issue 1 // TODO remove
          if (typeof annot.id === "string" || annot.id instanceof String) {
            annot.id = parseInt(annot.id);
          }
        }
      }

      // WORKAROUND anonymize preview TODO resolve
      if (annset.name.startsWith("entities_consolidated")) {
        for (const annot of annset.annotations) {
          if (
            ["persona", "parte", "controparte", "luogo", "altro"].includes(
              annot.type
            ) &&
            annot.start < document.preview.length
          ) {
            var end = 0;
            if (annot.end >= document.preview.length) {
              end = document.preview.length - 1;
            } else {
              end = annot.end;
            }
            document.preview =
              document.preview.substring(0, annot.start) +
              "*".repeat(end - annot.start) +
              document.preview.substring(end);
          }
        }
      }
      // WORKAROUND codici fiscali
      const regexPattern = /[A-Za-z0-9]{16}/;

      document.preview = document.preview.replace(regexPattern, (match) =>
        "*".repeat(match.length)
      );

      for (const annot of annset.annotations) {
        // workaround for issue 1 // TODO remove
        if (typeof annot.id === "string" || annot.id instanceof String) {
          annot.id = parseInt(annot.id);
        }
      }

      if (anonymous) {
        delete annset["_id"];
        delete annset["__v"];
        delete annset["docId"];
        for (const annot of annset.annotations) {
          // remove references to db
          delete annot["_id"];
          delete annot["__v"];
          delete annot["annotationSetId"];
        }
      }

      // ensure annset is sorted
      annset.annotations.sort((a, b) => a.start - b.start);

      new_sets[annset.name] = annset;
    }
    document.annotation_sets = new_sets;

    if (anonymous) {
      delete document["_id"];
      delete document["__v"];
      delete document["id"];
      if ("features" in document) {
        if ("save" in document["features"]) {
          delete document["features"]["save"];
        }
        if ("reannotate" in document["features"]) {
          delete document["features"]["reannotate"];
        }
      }
    }

    if (!clusters && document.features && document.features.clusters) {
      for (const [annset_name, annset_clusters] of Object.entries(
        document.features.clusters
      )) {
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
  route.get(
    "/:id",
    asyncRoute(async (req, res, next) => {
      const { id } = req.params;
      console.log("doc id", id);
      const document = await getDocumentById(id);
      console.log("doc", document);
      return res.json(document).status(200);
    })
  );
  route.post(
    "/:id/move-entities",
    validateRequest({
      req: {
        body: z.object({
          entities: z.array(z.number()),
          annotationSet: z.string(),
          sourceCluster: z.number(),
          destinationCluster: z.number(),
        }),
      },
    }),
    asyncRoute(async (req, res, next) => {
      const { id } = req.params;
      console.log("doc id", id);
      const document = await getDocumentById(id);

      const { entities, annotationSet, sourceCluster, destinationCluster } =
        req.body;

      //find and delete source and destination clusters
      let source = document.features.clusters[annotationSet].find(
        (cluster) => cluster.id === sourceCluster
      );
      document.features.clusters[annotationSet] = document.features.clusters[
        annotationSet
      ].filter((cluster) => cluster.id !== sourceCluster);
      let dest = document.features.clusters[annotationSet].find(
        (cluster) => cluster.id === destinationCluster
      );
      document.features.clusters[annotationSet] = document.features.clusters[
        annotationSet
      ].filter((cluster) => cluster.id !== destinationCluster);
      //move entities
      let entObjects = source.mentions.filter((mention) =>
        entities.includes(mention.id)
      );
      source.mentions = source.mentions.filter(
        (mention) => !entities.includes(mention.id)
      );
      dest.mentions = dest.mentions.concat(entObjects);
      let clusters = [
        ...document.features.clusters[annotationSet],
        source,
        dest,
      ];
      let result = await DocumentController.updateClusters(
        id,
        annotationSet,
        clusters
      );
      
      let doc = await getDocumentById(id);
      console.log("doc", doc.features.clusters[annotationSet]);
      return res.json(doc).status(200);
      //   let entObjects = [];
      //   for(let i=0; i<entities.length; i++){
    })
  );

  async function moveEntities() {}
  /**
   * Get document by id anonymous
   */
  route.get(
    "/anon/:id",
    asyncRoute(async (req, res, next) => {
      const { id } = req.params;

      const document = await getDocumentById(id, true);

      return res.json(document).status(200);
    })
  );

  /**
   * Get document by id anonymous
   */
  route.get(
    "/clusters/:id",
    asyncRoute(async (req, res, next) => {
      const { id } = req.params;

      const document = await getDocumentById(id, false, true);

      return res.json(document).status(200);
    })
  );

  /**
   * Update a document
   */
  route.post(
    "/:id",
    validateRequest({
      req: {
        body: z.object({
          text: z.string(),
          annotation_sets: z.object(),
          preview: z.string().optional(),
          name: z.string().optional(),
          features: z.object().optional(),
          offset_type: z.string().optional(),
        }),
      },
    }),
    asyncRoute(async (req, res, next) => {
      // delete document // TODO ROLLBACK on Failure
      const { id } = req.params;
      const deleteResults = await deleteDoc(
        { params: { docId: id } },
        null,
        next
      );
      // new document object
      const pre_doc = req.body;
      pre_doc["id"] = id;
      const newDoc = documentDTO(req.body);
      console.log("newDoc", newDoc);
      const doc = await DocumentController.insertOne(newDoc);
      // insert each annnotation set
      await Promise.all(
        Object.values(req.body.annotation_sets).map(async (set) => {
          const { annotations: newAnnotations, ...rest } = set;
          const newAnnSet = annotationSetDTO({ docId: doc.id, ...rest });
          const annSet = await AnnotationSetController.insertOne(newAnnSet);
          // insert all annotations for a set
          const newAnnotationsDTOs = newAnnotations.map((ann) =>
            annotationDTO({ annotationSetId: annSet._id, ...ann })
          );
          await Annotation.insertMany(newAnnotationsDTOs);

          return annSet;
        })
      );

      return res.json(doc).status(200);
    })
  );

  /**
   * Create a new document
   */
  route.post(
    "/",
    validateRequest({
      req: {
        body: z.object({
          text: z.string(),
          annotation_sets: z.object(),
          preview: z.string().optional(),
          name: z.string().optional(),
          features: z.object().optional(),
          offset_type: z.string().optional(),
        }),
      },
    }),
    asyncRoute(async (req, res, next) => {
      // new document object
      const newDoc = documentDTO(req.body);
      const doc = await DocumentController.insertOne(newDoc);
      // insert each annnotation set
      await Promise.all(
        Object.values(req.body.annotation_sets).map(async (set) => {
          const { annotations: newAnnotations, ...rest } = set;
          const newAnnSet = annotationSetDTO({ docId: doc.id, ...rest });
          const annSet = await AnnotationSetController.insertOne(newAnnSet);
          // insert all annotations for a set
          const newAnnotationsDTOs = newAnnotations.map((ann) =>
            annotationDTO({ annotationSetId: annSet._id, ...ann })
          );
          await Annotation.insertMany(newAnnotationsDTOs);

          return annSet;
        })
      );

      return res.json(doc).status(200);
    })
  );

  route.delete("/:docId", asyncRoute(deleteDoc));

  route.delete(
    "/:docId/annotation-set/:annotationSetId",
    asyncRoute(async (req, res, next) => {
      const { docId, annotationSetId } = req.params;

      const result = await AnnotationSet.deleteOne({ _id: annotationSetId });
      await Annotation.deleteMany({ annotationSetId });
      return res.json(result);
    })
  );
};
