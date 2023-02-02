import { Router } from 'express';
import document from './document';
import save from './save';
import review from './review';

/**
 * Export all defined routes
 */
export default () => {
  const app = Router();
  document(app);
  save(app);
  review(app);

  return app
}