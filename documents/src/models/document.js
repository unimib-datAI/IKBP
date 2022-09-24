import mongoose, { Schema } from 'mongoose';
import Inc from "mongoose-sequence";
import paginate from 'mongoose-paginate-v2';

const schema = new mongoose.Schema({
  name: String,
  preview: String,
  text: String,
  features: Object,
  offset_type: String, // "p" for python style
});

// add field for auto increment id
const AutoIncrement = Inc(mongoose);
schema.plugin(AutoIncrement, { inc_field: 'id' });
// add pagination for this schema
schema.plugin(paginate);
export const Document = mongoose.model('Document', schema, 'documents');

export const documentDTO = (body) => {
  const text = body.text;
  const preview = body.preview || body.text.slice(0, 400);
  const name = body.name || body.text.split(' ').slice(0, 3).join(' ');
  const features = body.features;
  const offset_type = body.offset_type || "p";
  return new Document({ name, preview, text, features, offset_type });
}