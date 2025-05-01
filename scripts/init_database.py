#!/usr/bin/env python
"""
Database initialization script for ClaimVision.

This script creates all the necessary database tables and populates them with initial data.
"""

import os
import sys
import uuid
from datetime import datetime, timezone

# Add the src directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from models import Base
from models.group_types import GroupType
from models.group_identities import GroupIdentity
from models.group_roles import GroupRole
from models.membership_statuses import MembershipStatus
from models.resource_types import ResourceType
from models.room import Room


def get_database_url():
    """
    Construct the database URL from environment variables.
    
    Returns
    -------
    str
        The database URL.
    """
    # Try to get individual components first
    username = os.getenv("DB_USERNAME")
    password = os.getenv("DB_PASSWORD")
    host = os.getenv("DB_HOST")
    name = os.getenv("DB_NAME", "claimvision")
    # If all components are available, construct the URL
    return f"postgresql://testuser:YourStrongPassword123!@claimvision-dev.czzwxwpwmndx.us-east-1.rds.amazonaws.com:5432/claimvision"

def drop_tables(engine):
    """Drop all tables in the database."""
    print("Dropping all database tables...")
    ###Base.metadata.drop_all(engine)
    with engine.connect() as conn:
        conn.execute(text("DROP SCHEMA public CASCADE; CREATE SCHEMA public;"))
    print("Tables dropped successfully.")

def create_tables(engine):
    """Create all tables defined in the models."""
    print("Creating database tables...")
    print(f"Tables to be created: {Base.metadata.tables.keys()}")
    Base.metadata.create_all(engine)
    print("Tables created successfully.")

def seed_vocab(session) -> None:
    vocab_data = {
        GroupType: [
            {"id": "household", "name": "Household", "description": "A residential group or policyholder"},
            {"id": "firm", "name": "Firm", "description": "Public adjusting or restoration company"},
            {"id": "partner", "name": "Partner", "description": "Integration or business partner"},
            {"id": "other", "name": "Other", "description": "Miscellaneous group type"},
        ],
        GroupIdentity: [
            {"id": "homeowner", "label": "Homeowner"},
            {"id": "adjuster", "label": "Adjuster"},
            {"id": "contractor", "label": "Contractor"},
            {"id": "other", "label": "Other"},
        ],
        GroupRole: [
            {"id": "owner", "label": "Owner"},
            {"id": "editor", "label": "Editor"},
            {"id": "viewer", "label": "Viewer"},
        ],
        MembershipStatus: [
            {"id": "invited", "label": "Invited"},
            {"id": "active", "label": "Active"},
            {"id": "revoked", "label": "Revoked"},
        ],
        ResourceType: [
            {"id": "claim", "label": "Claim", "description": "Insurance claim", "is_active": True},
            {"id": "file", "label": "File", "description": "File attachment", "is_active": True},
            {"id": "item", "label": "Item", "description": "Claim item", "is_active": True},
            {"id": "label", "label": "Label", "description": "Item label", "is_active": True},
            {"id": "room", "label": "Room", "description": "Room in a property", "is_active": True},
            {"id": "report", "label": "Report", "description": "Generated report", "is_active": True},
        ],
    }

    for model, rows in vocab_data.items():
        for row in rows:
            existing = session.get(model, row["id"])
            if not existing:
                session.add(model(**row))

    room_names = [
        "Attic", "Auto", "Basement", "Bathroom", "Bedroom", "Closet", "Dining Room", "Entry", "Exterior",
        "Family Room", "Foyer", "Game Room", "Garage", "Hall", "Kitchen", "Laundry Room", "Living Room",
        "Primary Bathroom", "Primary Bedroom", "Mud Room", "Nursery", "Office", "Pantry", "Patio",
        "Play Room", "Pool", "Porch", "Shop", "Storage", "Theater", "Utility Room", "Workout Room"
    ]

    for i, name in enumerate(room_names, start=1):
        existing = session.query(Room).filter_by(name=name).first()
        if not existing:
            session.add(Room(name=name, sort_order=i, is_active=True))


def create_default_data(session):
    """Create default data for the application."""
    print("Creating default data...")
    print("Seeding rooms...")
    seed_vocab(session)

    session.flush()  # Flush to get the ID
    
    # Commit changes
    session.commit()
    print("Default data created successfully.")

def main():
    """Main function to initialize the database."""
    # Get environment variables
    database_url = get_database_url()
    
    # Create engine and session
    engine = create_engine(database_url)
    Session = sessionmaker(bind=engine)
    session = Session()
    
    try:
        # Check if the database is accessible
        session.execute(text("SELECT 1"))
        print("Database connection successful.")
        
        # Drop existing tables
        drop_tables(engine)
        
        # Create tables
        create_tables(engine)
        
        # Create default data
        create_default_data(session)
        
        print("Database initialization completed successfully.")
    except Exception as e:
        print(f"Error initializing database: {str(e)}")
        sys.exit(1)
    finally:
        session.close()

if __name__ == "__main__":
    main()
