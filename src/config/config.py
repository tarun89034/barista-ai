from pydantic import BaseSettings, validator
from typing import Optional, List


class ConfigSettings(BaseSettings):
    openai_api_key: str
    anthropic_api_key: str
    financial_data_api_keys: List[str]
    vector_database_settings: str
    risk_analysis_parameters: str
    rebalancing_parameters: str
    market_monitor_settings: str
    memory_agent_settings: str
    portfolio_settings: str
    api_server_settings: str
    logging_settings: str
    feature_flags: str

    class Config:
        env_file = ".env"

    @validator('financial_data_api_keys', pre=True)
    def split_financial_data_api_keys(cls, value):
        if isinstance(value, str):
            return value.split(',')
        return value

    # Additional validation methods can be added here


# Instantiate the settings
settings = ConfigSettings()