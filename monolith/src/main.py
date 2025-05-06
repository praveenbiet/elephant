from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi

from src.common.config import get_settings
from src.common.database import init_db, close_db
from src.common.logger import setup_logging
from src.api.v1.routers import (
    auth, identity, courses, videos, assessments, learning_paths,
    user_progress, search, recommendations, discussions,
    subscriptions, billing, notifications, progress
)
from src.api.v1.routers.admin import dashboard, users, courses as admin_courses, settings as admin_settings

app = FastAPI(
    title="E-Learning Platform API",
    description="Modular monolith API for the E-Learning Platform",
    version="1.0.0"
)

# Setup logging
setup_logging()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=get_settings().CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Event handlers
@app.on_event("startup")
async def startup_event():
    await init_db()

@app.on_event("shutdown")
async def shutdown_event():
    await close_db()

# Include routers
app.include_router(auth.router, prefix="/api/v1", tags=["Authentication"])
app.include_router(identity.router, prefix="/api/v1", tags=["Identity"])
app.include_router(courses.router, prefix="/api/v1", tags=["Courses"])
app.include_router(videos.router, prefix="/api/v1", tags=["Videos"])
app.include_router(assessments.router, prefix="/api/v1", tags=["Assessments"])
app.include_router(learning_paths.router, prefix="/api/v1", tags=["Learning Paths"])
app.include_router(user_progress.router, prefix="/api/v1", tags=["User Progress"])
app.include_router(progress.router, prefix="/api/v1", tags=["Progress Tracking"])
app.include_router(search.router, prefix="/api/v1", tags=["Search"])
app.include_router(recommendations.router, prefix="/api/v1", tags=["Recommendations"])
app.include_router(discussions.router, prefix="/api/v1", tags=["Discussions"])
app.include_router(subscriptions.router, prefix="/api/v1", tags=["Subscriptions"])
app.include_router(billing.router, prefix="/api/v1", tags=["Billing"])
app.include_router(notifications.router, prefix="/api/v1", tags=["Notifications"])

# Admin routes
admin_app = FastAPI(
    title="E-Learning Platform Admin API",
    description="Admin API for the E-Learning Platform",
    version="1.0.0"
)
admin_app.include_router(dashboard.router, tags=["Admin Dashboard"])
admin_app.include_router(users.router, tags=["Admin Users"])
admin_app.include_router(admin_courses.router, tags=["Admin Courses"])
admin_app.include_router(admin_settings.router, tags=["Admin Settings"])

# Mount admin app
app.mount("/api/v1/admin", admin_app)

# Custom OpenAPI schema
def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    openapi_schema = get_openapi(
        title="E-Learning Platform API",
        version="1.0.0",
        description="Modular monolith API for the E-Learning Platform",
        routes=app.routes,
    )
    # Custom modifications to schema here if needed
    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("src.main:app", host="0.0.0.0", port=8000, reload=True)
