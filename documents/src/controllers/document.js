import { Document } from "../models/document";
import { AnnotationSet } from "../models/annotationSet";
import { HTTPError, HTTP_ERROR_CODES } from "../utils/http-error";
import { annotationSetDTO } from "../models/annotationSet";
import { AnnotationSetController } from "./annotationSet";
import { Annotation, annotationDTO } from "../models/annotation";
import { Message } from "../models/message.js";
import { Persons } from "../models/person.js";

export const DocumentController = {
  updateClusters: async (docId, annSet, clusters) => {
    try {
      const query = { id: docId };
      const update = {
        $set: {
          [`features.clusters.${annSet}`]: clusters, // Replace 'nestedField.subField' with the actual path and 'newValue' with the new value
        },
      };
      const result = await Document.findOneAndUpdate(query, update, {
        new: true,
      });
      console.log("update result", result);
      return result;
    } catch (error) {
      throw new HTTPError({
        code: HTTP_ERROR_CODES.INTERNAL_SERVER_ERROR,
        message: `Could not update document. ${err}`,
      });
    }
  },
  insertOne: async (document) => {
    try {
      const doc = await document.save().then((doc) => {
        if (doc.id === undefined) {
          doc.id = doc.inc_id;
        }
        return doc.save();
      });
      return doc;
    } catch (err) {
      throw new HTTPError({
        code: HTTP_ERROR_CODES.INTERNAL_SERVER_ERROR,
        message: `Could not save document to DB. ${err}`,
      });
    }
  },
  findAll: async (q = "", limit = 20, page = 1) => {
    const query = {
      ...(q && {
        name: { $regex: q, $options: "i" },
      }),
    };

    const options = {
      select: ["_id", "id", "name", "preview"],
      page,
      limit,
    };

    return Document.paginate(query, options);
  },
  findOne: async (id) => {
    const doc = await Document.findOne({ id }).lean();
    if (!doc) {
      throw new HTTPError({
        code: HTTP_ERROR_CODES.NOT_FOUND,
        message: `Document with id '${id}' was not found.`,
      });
    }
    let messages = [];
    console.log("messages", messages[0]);
    let text = doc.intro;
    if (doc.messages) {
      messages = await Message.find({ _id: { $in: doc.messages } })
        .sort({
          sequence_number: 1,
        })
        .lean();
      let persons = [];
      let firstMessage = messages[0];
      let person1 = await Persons.findOne({
        _id: messages[0].sender["_id"],
      }).lean();
      let person2 = await Persons.findOne({
        _id: messages[0].receiver["_id"],
      }).lean();
      persons.push(person1);
      persons.push(person2);
      console.log("messages", messages.length);
      for (let i = 0; i < messages.length; i++) {
        let sender = persons.find((person) => {
          return person._id.equals(messages[i].sender);
        });
        let receiver = persons.find((person) => {
          return person._id.equals(messages[i].receiver);
        });
        if (messages.length === 156) {
          console.log("messages", messages[i]);
        }
        messages[i].sender = sender;
        messages[i].receiver = receiver;

        text += "-----------------------------\n";
        text += `${sender.name}\n`;
        text += `Timestamp: ${messages[i].timestamp}\n`;
        if (messages[i].type === "Allegato") {
          text += `Allegato: ${messages[i].path}\n`;
          text += `Contenuto:\n${messages[i].contenuto?.trim()}\n`;
        } else {
          text += `Messaggio: \n${messages[i].contenuto?.trim()}\n`;
        }
      }
      doc.text = text;
    }

    const annotationSets = await AnnotationSet.find({ docId: id }).lean();

    const annotationSetsWithAnnotations = await Promise.all(
      annotationSets.map(async (annSet) => {
        const annotations = await Annotation.find({
          annotationSetId: annSet._id,
        }).lean();
        return {
          ...annSet,
          annotations,
        };
      })
    );

    return {
      ...doc,
      annotation_sets: annotationSetsWithAnnotations,
    };
  },
  updateEntitiesAnnotationSet: async (docId, annotationSets) => {
    const update = async (annotationSet) => {
      const {
        annotations: newAnnotations,
        _id: annotationSetId,
        ...set
      } = annotationSet;
      // add new annotation set
      const newAnnotationSet = annotationSetDTO({ ...set, docId });
      const annSet = await newAnnotationSet.save();
      // add annoations for this set
      const annotationsDTOs = newAnnotations.map(({ _id, ...ann }) =>
        annotationDTO({ ...ann, annotationSetId: annSet._id })
      );
      const annotations = await Annotation.insertMany(annotationsDTOs);

      return {
        ...annSet.toObject(),
        annotations,
      };
    };

    const oldAnnotationSets = await AnnotationSet.find({ docId });
    await AnnotationSet.deleteMany({ docId });
    // delete annotations for each annotation set
    for (const annSet of oldAnnotationSets) {
      await Annotation.deleteMany({ annotationSetId: annSet._id });
    }
    // update with new annotation sets
    const updaters = Object.values(annotationSets).map((set) => update(set));
    return Promise.all(updaters);
  },
};
function formatTimestamp(timestamp) {
  const date = new Date(timestamp); // Create a Date object from the timestamp

  // Extract components
  const day = String(date.getUTCDate()).padStart(2, "0"); // Get day and pad with zero if needed
  const month = String(date.getUTCMonth() + 1).padStart(2, "0"); // Get month (0-indexed) and pad
  const year = date.getUTCFullYear(); // Get full year
  const hours = String(date.getUTCHours()).padStart(2, "0"); // Get hours in UTC and pad
  const minutes = String(date.getUTCMinutes()).padStart(2, "0"); // Get minutes in UTC and pad
  const seconds = String(date.getUTCSeconds()).padStart(2, "0"); // Get seconds in UTC and pad

  // Format the final string
  return `${month}/${day}/${year} ${hours}:${minutes}:${seconds} +0000`;
}
