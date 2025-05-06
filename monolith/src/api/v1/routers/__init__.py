# Import all routers here for easier organization
from src.api.v1.routers.auth import router as auth
from src.api.v1.routers.identity import router as identity
from src.api.v1.routers.courses import router as courses
from src.api.v1.routers.videos import router as videos
from src.api.v1.routers.assessments import router as assessments
from src.api.v1.routers.learning_paths import router as learning_paths
from src.api.v1.routers.user_progress import router as user_progress
from src.api.v1.routers.search import router as search
from src.api.v1.routers.recommendations import router as recommendations
from src.api.v1.routers.discussions import router as discussions
from src.api.v1.routers.subscriptions import router as subscriptions
from src.api.v1.routers.billing import router as billing
from src.api.v1.routers.notifications import router as notifications
from src.api.v1.routers.progress import router as progress
