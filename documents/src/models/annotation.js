import mongoose, { Schema } from 'mongoose';

// const annotationSchema = new Schema({
//   type: String,
//   start: Number,
//   end: Number,
//   id: Number,
//   features: Object
// })

const annotationSchema = new Schema({
  annotationSetId: mongoose.Types.ObjectId,
  id: Number,
  type: String,
  start: Number,
  end: Number,
  features: Object
});
export const Annotation = mongoose.model('Annotation', annotationSchema, 'annotations');

export const annotationDTO = (annotation) => {
  return new Annotation(annotation);
}