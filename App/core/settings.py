"""
Load system configuration from specific environment files.
"""

# python libraries
from pydantic_settings import BaseSettings, SettingsConfigDict


# define environment and choose environment file to load based in ENVIRONMENT variable.
# ENVIRONMENT = 'local'

# if ENVIRONMENT == 'local':
#     _env = ".env.local"


# Class Settings to generate the configuration of the backend application
class Settings(BaseSettings):
    # API BASE URL
    api_base_url: str
    api_base_description: str
    # ENVIRONMENT IN WHICH PASSWORD RECOVERY IS REQUESTED
    environment_base_url : dict
    # SWAGGER AUTH
    swagger_username: str
    swagger_password: str
    skip_setup: bool
    secret_key: str
    # TOKEN CONFIGURATION
    jwt_secret: str
    jwt_secret_renew: str
    jwt_token_expiration: int
    jwt_renew_expiration: int
    algorithm: str
    # LOG CONFIGURATION
    log_route: str
    log_level: str
    log_file_size: int
    log_backup_count: int
    log_nomenclature: str
    # DATABASE CONFIGURATION
    db_server: str
    db_server_port: str
    db_user: str
    db_password: str
    db_database: str
    # REDIS CONFIGURATION
    redis_host: str
    redis_port: str
    redis_db: int
    redis_exp: int
    #SMTP CONFIGURATION
    smtp_server:str
    smtp_port:int
    smtp_user:str
    smtp_password:str
    # VERIFICATION CODE EXPIRATION IN MINUTES
    vcode_exp_min:int
    # MAGIC LINK EXPIRATION IN MINUTES
    ml_exp_min : int
    
    create_configuration: bool
    # BLOCKCHAIN CONFIGURATION
    rpc_url: str 
    chain_id: int 
    api_private_key: str 
    contract_abi_dir: str 
    agronest_contract_address: str
    usdc_contract_address: str
    # GOOGLE GEMINI AI CONFIGURATION
    gemini_api_key: str
    # ETHERFUSE CONFIGURATION
    etherfuse_api_key: str
    etherfuse_base_url: str
    # RARE PROTOCOL CONFIGURATION
    rare_contract_address: str
    rare_network: str
    # This generates the mapping to Settings object from .env file
    model_config = SettingsConfigDict(env_file=".env")
    # Dictionary containing the password reset environment

# Todo: Verify if this line settings=Settings() is necessary
settings = Settings()

