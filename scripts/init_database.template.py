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
from models import Base, Household, Label

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

def create_default_data(session):
    """Create default data for the application."""
    print("Creating default data...")
    
    # Create default labels
    default_labels = [
        Label(label_text="Damaged", is_ai_generated=False),
        Label(label_text="Destroyed", is_ai_generated=False),
        Label(label_text="Repairable", is_ai_generated=False),
        Label(label_text="Replacement Needed", is_ai_generated=False),
        Label(label_text="High Value", is_ai_generated=False),
        Label(label_text="Sentimental", is_ai_generated=False),
        Label(label_text="Electronics", is_ai_generated=False),
        Label(label_text="Furniture", is_ai_generated=False),
        Label(label_text="Clothing", is_ai_generated=False),
        Label(label_text="Jewelry", is_ai_generated=False),
        Label(label_text="Appliance", is_ai_generated=False),
        Label(label_text="Art", is_ai_generated=False),
        Label(label_text="Antique", is_ai_generated=False),
        Label(label_text="Collectible", is_ai_generated=False),
        Label(label_text="Document", is_ai_generated=False),
        Label(label_text="Receipt", is_ai_generated=False),
        Label(label_text="Warranty", is_ai_generated=False),
        Label(label_text="Insurance", is_ai_generated=False),
        Label(label_text="Photo", is_ai_generated=False),
        Label(label_text="Video", is_ai_generated=False)
    ]
    
    # Create a default household for the labels
    default_household = Household(
        id=uuid.uuid4(),
        name="Default Household"
    )
    session.add(default_household)
    session.flush()  # Flush to get the ID
    
    # Add labels to session
    for label in default_labels:
        existing_label = session.query(Label).filter_by(label_text=label.label_text).first()
        if not existing_label:
            label.household_id = default_household.id
            session.add(label)
    
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
