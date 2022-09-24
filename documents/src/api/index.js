import { Router } from 'express';
import document from './document';
import save from './save';

/**
 * Export all defined routes
 */
export default () => {
  const app = Router();
  document(app);
  save(app);

  return app
}