from fastapi import FastAPI

from backend.app.api.routes import router

app = FastAPI(title="Boom Picks Paper Trading Platform")
app.include_router(router)
