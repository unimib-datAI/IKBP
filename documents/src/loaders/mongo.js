import mongoose from "mongoose";

export const mongoLoader = async () => {
  try {
    console.log("Setup mongodb...",process.env.MONGO);
    await mongoose.connect(process.env.MONGO, {
      useNewUrlParser: true,
      useUnifiedTopology: true,
    });
  } catch (err) {
    console.error(err);
    throw new Error("Couldn't not connecto to DB.");
  }
};
