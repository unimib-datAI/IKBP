import { expressLoader } from "./express";
import { mongoLoader } from "./mongo";

export const startServer = async (callback) => {
  const PORT = process.env.DOCS_PORT;
  // setup express routes
  const app = expressLoader();
  // setup mongodb
  await mongoLoader();

  // start server
  const server = app.listen(PORT, () => callback({ PORT }));

  return server;
};
