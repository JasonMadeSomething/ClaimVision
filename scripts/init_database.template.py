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
    return f"postgresql://{username}:{password}@{host}:5432/{name}"
    
    # Fall back to the full DATABASE_URL if available
    return os.getenv("DATABASE_URL", "postgresql://user:password@localhost:5432/testdb")

def drop_tables(engine):
    """Drop all tables in the database."""
    print("Dropping all database tables...")
    Base.metadata.drop_all(engine)
    print("Tables dropped successfully.")

def create_tables(engine):
    """Create all tables defined in the models."""
    print("Creating database tables...")
    Base.metadata.create_all(engine)
    print("Tables created successfully.")

def seed_vocab(session) -> None:
    vocab_data = {
        GroupType: [
            {"id": "household", "label": "Household", "description": "A residential group or policyholder"},
            {"id": "firm", "label": "Firm", "description": "Public adjusting or restoration company"},
            {"id": "partner", "label": "Partner", "description": "Integration or business partner"},
            {"id": "other", "label": "Other", "description": "Miscellaneous group type"},
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
            {"id": "claim", "label": "Claim"},
            {"id": "file", "label": "File"},
            {"id": "item", "label": "Item"},
            {"id": "label", "label": "Label"},
            {"id": "room", "label": "Room"},
            {"id": "report", "label": "Report"},
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
