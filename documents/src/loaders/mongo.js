import mongoose from "mongoose";

export const mongoLoader = async () => {
  try {
    console.log("Setup mongodb...");
    await mongoose.connect(process.env.MONGO, {
      useNewUrlParser: true,
      useUnifiedTopology: true,
    });
  } catch (err) {
    throw new Error("Couldn't not connecto to DB.");
  }
};
