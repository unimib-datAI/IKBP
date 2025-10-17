import mongoose, { Schema } from "mongoose";

export const personSchema = new Schema({
  name: String,
  phone: String,
});
export const Persons = mongoose.model("Persons", personSchema, "persons");
export const personDTO = (person) => {
  return new Persons(person);
};
