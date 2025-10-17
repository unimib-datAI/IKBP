import mongoose, { Schema } from "mongoose";
import { personSchema } from "./person.js";

export const messageSchema = new Schema({
  timestamp: String,
  type: String,
  contenuto: String,
  sender: { type: Schema.Types.ObjectId, ref: "Persons" },
  receiver: { type: Schema.Types.ObjectId, ref: "Persons" },
});
export const Message = mongoose.model("Message", messageSchema, "messages");
export const messageDTO = (message) => {
  return new Message(message);
};
