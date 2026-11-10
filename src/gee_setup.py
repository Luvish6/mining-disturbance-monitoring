"""Initialize Earth Engine with explicit billing/quota project."""
import ee
from config.settings import project_id

def initialize(authenticate: bool = False) -> None:
    project = project_id()
    if authenticate:
        ee.Authenticate()
    try:
        ee.Initialize(project=project)
    except Exception as exc:
        raise RuntimeError(
            'Earth Engine initialization failed. Run `earthengine authenticate` '
            'in your terminal, confirm GEE_PROJECT_ID and Earth Engine project access, '
            'then retry.'
        ) from exc
