from sqlalchemy.orm import declarative_base
from database.database import mapper_registry

# Base = declarative_base()
Base = mapper_registry.generate_base()
