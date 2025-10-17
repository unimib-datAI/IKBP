import express from 'express';
import api from '../api';
import { authMiddleware } from '../middlewares/auth';
import { HTTPError, HTTP_ERROR_CODES, transformHTTPError } from '../utils/http-error';
import logger from 'morgan';

export const expressLoader = () => {
  const app = express();

  app.use(express.urlencoded({ limit: "200mb", extended: true, parameterLimit: 1000000 }))
  app.use(express.json({ limit: "200mb" }))

  app.use(logger('dev'))

  /**
   * All api endpoints are exposed under /api
   */
  app.use('/api', authMiddleware, api());

  /**
   * Error handler
   */
  app.use((error, req, res, next) => {
    console.log(error);

    if (!(error instanceof HTTPError)) {
      // exception not thrown manually, just trhow INTERNAL_SERVER_ERROR
      const err = new HTTPError({
        code: HTTP_ERROR_CODES.INTERNAL_SERVER_ERROR,
        message: 'Something went wrong when processing the request.'
      })
      return res.status(err.code).json({
        ...transformHTTPError(err)
      })
    }
    res.status(error.code).json({ ...transformHTTPError(error) })
  })

  console.log('Setup express... done');

  return app;
}