import { Router } from 'express';
import { asyncRoute } from '../utils/async-route';
import { AnnotationSet } from '../models/annotationSet';
import { DocumentController } from '../controllers/document';



const route = Router();

export default (app) => {
  // route base root
  app.use('/save', route);

  /**
   * Save entity annotation set
   */
  route.post('/', asyncRoute(async (req, res) => {
    const { docId, annotationSets } = req.body;
    // const id = entitiesAnnotations._id;
    const resUpdate = await DocumentController.updateEntitiesAnnotationSet(docId, annotationSets);
    return res.json(resUpdate)
  }));
};