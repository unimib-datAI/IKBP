import { HTTPError, HTTP_ERROR_CODES } from "../utils/http-error";

export const authMiddleware = (req, res, next) => {
  if (process.env.ENABLE_AUTH === 'true') {
    if (!req.headers.authorization || req.headers.authorization !== process.env.API_KEY) {
      throw new HTTPError({
        code: HTTP_ERROR_CODES.FORBIDDEN,
        message: 'Invalid authorization header.'
      })
    }
  }
  next();
}