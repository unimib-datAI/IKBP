from fastapi import HTTPException, Request
from settings import Settings
from starlette.middleware.base import BaseHTTPMiddleware



class AuthMiddleware(BaseHTTPMiddleware):
    def __init__(
            self,
            app
    ):
        super().__init__(app)
        self.settings = Settings()

    async def dispatch(self, request: Request, call_next):
      authorization = request.headers.get('Authorization')
      if not authorization:
        raise HTTPException(status_code=401, detail="Authorization token is required!")
      
      api_token = authorization.split(' ')[1]

      if api_token != self.settings.api_key:
        raise HTTPException(status_code=401, detail="Invalid api token!")
      
      response = await call_next(request)
      return response