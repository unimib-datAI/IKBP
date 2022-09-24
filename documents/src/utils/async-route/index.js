/**
 * Higher order function which catche thrown error in routes and forwards them to error middleware
 * 
 * @example
 * 
 * route.get('/', asyncRoute(async (req, res, next) => ...))
 */
export const asyncRoute = fn => (...args) => {
  const fnReturn = fn(...args);
  const next = args[args.length - 1];
  return Promise.resolve(fnReturn).catch(next);
};
