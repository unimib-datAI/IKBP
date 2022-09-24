function getMessageFromUnkownError(
  err,
  fallback,
) {
  if (typeof err === 'string') {
    return err;
  }

  if (err instanceof Error && typeof err.message === 'string') {
    return err.message;
  }
  return fallback;
}

export const transformHTTPError = (error) => {
  return {
    error: {
      message: error.message,
      httpStatus: error.code,
      error: error.cause,
    }
  }
}

export const HTTP_ERROR_CODES = {
  BAD_REQUEST: 400,
  INTERNAL_SERVER_ERROR: 500,
  UNAUTHORIZED: 401,
  FORBIDDEN: 403,
  NOT_FOUND: 404,
  METHOD_NOT_SUPPORTED: 405,
  TIMEOUT: 408,
  CONFLICT: 409,
  PRECONDITION_FAILED: 412,
  PAYLOAD_TOO_LARGE: 413,
  CLIENT_CLOSED_REQUEST: 499
};

/**
 * Class to handle throw of HTTP errors
 * 
 * @example
 * 
 * throw new HTTPError({
 *  code: HTTP_ERROR_CODES.BAD_REQUEST,
 *  message: 'id is of type string'
 * })
 */
export class HTTPError extends Error {

  constructor(opts) {
    const cause = opts.cause;
    const code = opts.code;
    const message = opts.message ?? getMessageFromUnkownError(cause, code);

    super(message, { cause });

    this.code = code;
    this.cause = cause;
    this.name = 'HTTPError';

    Error.captureStackTrace(this, this.constructor);
    Object.setPrototypeOf(this, new.target.prototype);
  }
}