"""views package (split from the original monolithic views.py).

Submodules are re-exported here so `from . import views; views.X`
and `from <app>.views import X` keep working unchanged.
"""
from .helpers import *  # noqa: F401,F403
from .dashboard import *  # noqa: F401,F403
from .locations import *  # noqa: F401,F403
from .customers import *  # noqa: F401,F403
from .users_roles import *  # noqa: F401,F403
from .equipment_settings import *  # noqa: F401,F403
from .branding_css import *  # noqa: F401,F403
from .health import *  # noqa: F401,F403
from .docker_logs import *  # noqa: F401,F403
from .debug_data import *  # noqa: F401,F403
from .version import *  # noqa: F401,F403
from .webhooks import *  # noqa: F401,F403
from .profile_settings import *  # noqa: F401,F403
