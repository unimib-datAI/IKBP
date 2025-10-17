import { Annotation } from '../models/annotation';
import { AnnotationSet } from '../models/annotationSet';
import { Document } from '../models/document';
import { HTTP_ERROR_CODES, HTTPError } from '../utils/http-error';


export const AnnotationSetController = {
  insertOne: async (annotationSet) => {
    const doc = await annotationSet.save();
    return doc;
  },
  deleteOne: async (id) => {
    // const updatedDocument = await Document.updateOne({ id: docId }, {
    //   $pull: {
    //     annotation_sets: annotationSetId,
    //   },
    // });
    await Annotation.deleteMany({ annotationSetId: id })
    return AnnotationSet.deleteOne({ id })
    // delete annotation set document

    // return AnnotationSet.deleteOne({ _id: annotationSetId });
  }
}