"""MARS v1.1 routes mounted onto the commercial mars-api app."""
from fastapi import HTTPException, Request

import mars_reason


def mount_mars(app):
    @app.post("/api/reason")
    async def api_reason(request: Request):
        data = await request.json()
        query = data.get("query") or data.get("task") or ""
        if not query:
            raise HTTPException(status_code=422, detail="query required")
        return mars_reason.reason(
            query, route=data.get("route"), max_tokens=data.get("max_tokens")
        )

    @app.get("/api/mars/status")
    def api_mars_status():
        return mars_reason.status()
