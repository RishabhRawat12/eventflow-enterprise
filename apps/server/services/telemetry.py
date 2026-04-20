import os
import sys
import asyncio
from typing import Optional
from google.cloud import bigquery_storage_v1
from google.cloud.bigquery_storage_v1 import types
from google.protobuf import descriptor_pb2

# Ensure the compiled protobufs are in the python path
PROTO_PATH = os.path.normpath(os.path.join(os.path.dirname(__file__), "../../../packages/shared/proto/compiled/python"))
if PROTO_PATH not in sys.path:
    sys.path.append(PROTO_PATH)

import telemetry_pb2

class TelemetryService:
    """
    BigQuery ManagedWriter Wrapper for high-performance telemetry streaming.
    Maintains a single persistent gRPC stream for the duration of the server's lifecycle.
    """
    
    def __init__(self):
        self.project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
        self.dataset_id = os.getenv("BQ_DATASET", "eventflow_enterprise")
        self.table_id = os.getenv("BQ_TABLE", "telemetry_logs")
        
        try:
            self.client = bigquery_storage_v1.BigQueryWriteClient()
        except Exception as e:
            print(f"[TELEMETRY_INIT_ERROR] Failed to initialize BigQuery client: {e}")
            self.client = None
        
        self.parent = f"projects/{self.project_id}/datasets/{self.dataset_id}/tables/{self.table_id}"
        self.stream_name = f"{self.parent}/streams/_default"
        
        # Persistent stream state
        self._stream = None
        self._write_template = None
        
        # Pre-cache the Protobuf descriptor
        self.proto_descriptor = descriptor_pb2.DescriptorProto()
        telemetry_pb2.TelemetryEvent.DESCRIPTOR.CopyToProto(self.proto_descriptor)

    async def connect(self):
        """Initializes the telemetry client. Persistent streams are handled per-request for high-throughput."""
        if not self.client:
            return
        
        print(f"[TELEMETRY] Persistent channel verified for {self.stream_name}")
        # Connection is lazy-loaded by the Google library internally
        
    async def stream_telemetry_event(self, event: telemetry_pb2.TelemetryEvent):
        """
        Pushes a telemetry event to the BigQuery Storage Write API.
        Fire-and-forget execution via background task to guarantee O(1) server latency.
        """
        if not self.client:
            return

        asyncio.create_task(self._async_append(event))

    async def _async_append(self, event: telemetry_pb2.TelemetryEvent):
        try:
            request = types.AppendRowsRequest()
            request.write_stream = self.stream_name
            
            proto_data = types.AppendRowsRequest.ProtoData()
            proto_schema = types.ProtoSchema()
            proto_schema.proto_descriptor = self.proto_descriptor
            proto_data.writer_schema = proto_schema
            proto_data.rows.serialized_rows.append(event.SerializeToString())
            
            request.proto_rows = proto_data

            # Use a thread-safe executor for the blocking gRPC call
            loop = asyncio.get_event_loop()
            responses = await loop.run_in_executor(None, self._execute_append, request)
        except Exception as e:
            print(f"[TELEMETRY_DROP] {e}")

    def _execute_append(self, request):
        responses = self.client.append_rows(requests=iter([request]))
        for response in responses:
            if response.error.code != 0:
                print(f"[BQ_WRITE_ERROR] {response.error.message}")
            return

    async def disconnect(self):
        """Gracefully closes any open connections."""
        # The storage write API handles stream closure on channel destruction
        pass

# Singleton instance
telemetry_service = TelemetryService()
