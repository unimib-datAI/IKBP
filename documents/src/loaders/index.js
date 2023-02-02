import { expressLoader } from "./express";
import { mongoLoader } from "./mongo";

export const startServer = async (callback) => {
  const PORT = process.env.PORT;
  // setup express routes
  const app = expressLoader();

  if (process.env.SKIP_MONGO !== 'true') {
    // setup mongodb
    await mongoLoader();
  }

  // start server
  const server = app.listen(PORT, () => callback({ PORT }));

  return server;
}