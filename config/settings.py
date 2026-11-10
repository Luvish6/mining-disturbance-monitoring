"""Configuration and season definitions. Seasons cross calendar years."""
from dataclasses import dataclass
import os
from dotenv import load_dotenv

load_dotenv()

@dataclass(frozen=True)
class Season:
    name: str
    start: str  # inclusive
    end: str    # exclusive

BEFORE = Season('2023-24', '2023-11-01', '2024-04-01')
AFTER = Season('2024-25', '2024-11-01', '2025-04-01')
DISTRICTS = ('East Jaintia Hills', 'West Jaintia Hills')

def project_id() -> str:
    value = os.getenv('GEE_PROJECT_ID', '').strip()
    if not value or value == 'your-cloud-project-id':
        raise ValueError('Set GEE_PROJECT_ID in .env to your registered Google Cloud project ID.')
    return value
