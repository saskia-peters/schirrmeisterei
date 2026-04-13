from slowapi import Limiter
from slowapi.util import get_remote_address

from app.core.config import settings

# SCALE-UP (S-5): Set RATE_LIMIT_STORAGE_URI=redis://redis:6379/1 at Tier-3
# (100+ users / multi-replica) so counters are shared across all replicas.
# In-memory Storage is per-process — limits are not enforced across replicas.
# See SCALING.md § 3.2.
limiter = Limiter(
    key_func=get_remote_address,
    storage_uri=settings.RATE_LIMIT_STORAGE_URI,
)
