from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


from api.models.accounts import User  # noqa: E402, F401
from api.models.catalog import Product, ProductCategory  # noqa: E402, F401
from api.models.goals import (  # noqa: E402, F401
    Distribution,
    GoalClientTarget,
    GoalCycle,
    SellerGoal,
    SellerSubstitution,
)
from api.models.hierarchy import (  # noqa: E402, F401
    HierarchyEvent,
    HierarchyLevel,
    HierarchyNode,
)
from api.models.calendar import Holiday, WorkingDaysConfig  # noqa: E402, F401
from api.models.portfolio import (  # noqa: E402, F401
    Accumulated,
    BaseDistribution,
    Client,
)
