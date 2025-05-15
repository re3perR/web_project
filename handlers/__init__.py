from .core         import router as core_router
from .catalog      import router as catalog_router
from .files        import router as files_router
from db.db_save      import router as db_save_router

all_routers = (
    db_save_router,
    core_router,
    catalog_router,
    files_router,
)
