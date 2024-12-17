import mongoose, { Schema } from 'mongoose';

// const annotationSchema = new Schema({
//   type: String,
//   start: Number,
//   end: Number,
//   id: Number,
//   features: Object
// })

const annotationSetSchema = new Schema({
  docId: String,
  name: String, // always the same as the identifier ?
  // annotations: [annotationSchema],
  // annotations: [Object],

  next_annid: Number
});
export const AnnotationSet = mongoose.model('AnnotationSet', annotationSetSchema, 'annotationSets');

export const annotationSetDTO = (annset) => {
  return new AnnotationSet(annset);
}