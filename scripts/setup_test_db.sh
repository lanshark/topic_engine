#!/bin/bash

# Drop template if exists
sudo -u postgres dropdb --if-exists template_postgis

# Create template database
sudo -u postgres createdb template_postgis

# Enable PostGIS on template
sudo -u postgres psql -d template_postgis -c "CREATE EXTENSION IF NOT EXISTS postgis;"

# Mark as template
sudo -u postgres psql -d postgres -c "UPDATE pg_database SET datistemplate = TRUE WHERE datname = 'template_postgis';"

# Set permissions on template
sudo -u postgres psql -d template_postgis -c "GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO andrew;"
sudo -u postgres psql -d template_postgis -c "GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO andrew;"
sudo -u postgres psql -d template_postgis -c "GRANT ALL PRIVILEGES ON ALL FUNCTIONS IN SCHEMA public TO andrew;"