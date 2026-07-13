from fastapi import HTTPException

from api.services.engines.base import CalculationEngine
from api.services.engines.base_distribution import BaseDistributionEngine
from api.services.engines.equal import EqualDistributionEngine
from api.services.engines.portfolio_based import PortfolioBasedEngine
from api.services.engines.previous_cycle import PreviousCycleEngine

ENGINES: dict[str, CalculationEngine] = {
    "base_distribution": BaseDistributionEngine(),
    "portfolio": PortfolioBasedEngine(),
    "equal": EqualDistributionEngine(),
    "previous_cycle": PreviousCycleEngine(),
}


def get_engine(name: str) -> CalculationEngine:
    engine = ENGINES.get(name)
    if not engine:
        available = ", ".join(ENGINES.keys())
        raise HTTPException(
            status_code=400,
            detail=f"Motor '{name}' nao encontrado. Disponiveis: {available}",
        )
    return engine


def list_engines() -> list[dict[str, str]]:
    return [
        {"key": key, "name": engine.display_name, "description": engine.description}
        for key, engine in ENGINES.items()
    ]
