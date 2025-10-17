import { HTTP_ERROR_CODES, HTTPError } from '../utils/http-error';


export const AnnotationController = {
  insertOne: async (annotation) => {
    const doc = await annotation.save();
    return doc;
  },
}