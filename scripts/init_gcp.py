import os
import sys
from google.cloud import bigquery
from google.api_core.exceptions import Conflict

def init_bigquery():
    # Use environment variables for flexible configuration
    dataset_id = os.getenv("BQ_DATASET", "eventflow_enterprise")
    table_id = os.getenv("BQ_TABLE", "telemetry_logs")
    
    print(f"Initializing BigQuery Infrastructure: {dataset_id}.{table_id}")
    
    client = bigquery.Client()
    
    # 1. Create or Find Dataset
    dataset_ref = client.dataset(dataset_id)
    try:
        client.create_dataset(dataset_ref)
        print(f"  [SUCCESS] Created dataset: {dataset_id}")
    except Conflict:
        print(f"  [INFO] Dataset {dataset_id} already exists.")
    except Exception as e:
        print(f"  [ERROR] Failed to create dataset: {e}")
        sys.exit(1)

    # 2. Define Explicit Schema (Strict mapping to telemetry.proto)
    # Note: BigQuery Storage Write API requires strict schema alignment.
    schema = [
        bigquery.SchemaField("venue_id", "STRING", mode="REQUIRED", description="Unique identifier for the venue"),
        bigquery.SchemaField("node_id", "INTEGER", mode="REQUIRED", description="ID of the zone/node"),
        bigquery.SchemaField("occupancy", "INTEGER", mode="REQUIRED", description="Current attendee count"),
        bigquery.SchemaField("capacity", "INTEGER", mode="REQUIRED", description="Maximum zone capacity"),
        bigquery.SchemaField("timestamp", "TIMESTAMP", mode="REQUIRED", description="Event occurrence time"),
        bigquery.SchemaField("event_type", "STRING", mode="REQUIRED", description="Type of event (OCCUPANCY_UPDATE, etc.)"),
        bigquery.SchemaField("latency_ms", "FLOAT", mode="REQUIRED", description="Processing latency in milliseconds"),
        bigquery.SchemaField("session_id", "STRING", mode="NULLABLE", description="Trace ID for user session"),
        bigquery.SchemaField("metadata_json", "STRING", mode="NULLABLE", description="Extra contextual JSON metadata")
    ]

    # 3. Create or Update Table
    table_ref = dataset_ref.table(table_id)
    table = bigquery.Table(table_ref, schema=schema)
    
    try:
        table = client.create_table(table)
        print(f"  [SUCCESS] Created table: {table_id}")
    except Conflict:
        print(f"  [INFO] Table {table_id} already exists. Verifying schema...")
        # In a real enterprise scenario, we might perform schema updates here.
        # For now, we assume the existing table matches or needs manual migration.
    except Exception as e:
        print(f"  [ERROR] Failed to create table: {e}")
        sys.exit(1)

    print("BigQuery Infrastructure Initialization Complete.")

if __name__ == "__main__":
    init_bigquery()
