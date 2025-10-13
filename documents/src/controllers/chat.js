import { Document } from "../models/document";
import { AnnotationSet } from "../models/annotationSet";
import { HTTPError, HTTP_ERROR_CODES } from "../utils/http-error";
import { annotationSetDTO } from "../models/annotationSet";
import { AnnotationSetController } from "./annotationSet";
import { Annotation, annotationDTO } from "../models/annotation";
import { ChatRating } from "../models/chatRating.js";

export const ChatController = {
  saveRating: async (rate, chatState) => {
    try {
      let result = await ChatRating.create({ rating: rate, chatState });
      return result;
    } catch (error) {
      throw new HTTPError({
        code: HTTP_ERROR_CODES.INTERNAL_SERVER_ERROR,
        message: `Could not save rating. ${err}`,
      });
    }
  },
};
