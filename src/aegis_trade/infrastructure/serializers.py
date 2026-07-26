import json
import pyarrow as pa
from typing import Any, Sequence, Mapping

from aegis_trade.core.storage import Serializer

class MetadataSerializer(Serializer):
    """Serializes metadata dictionaries to JSON bytes or strings."""
    def serialize(self, obj: Mapping[str, Any]) -> str:
        return json.dumps(obj, indent=2)

    def deserialize(self, data: str) -> Mapping[str, Any]:
        return json.loads(data)


class HashSerializer(Serializer):
    """Serializes core structures to a predictable format for hashing."""
    def serialize(self, obj: Any) -> bytes:
        # Standardize for hashing: sorted keys, compact representation
        if isinstance(obj, dict):
            return json.dumps(obj, sort_keys=True, separators=(',', ':')).encode('utf-8')
        elif isinstance(obj, str):
            return obj.encode('utf-8')
        raise ValueError(f"Cannot hash-serialize type {type(obj)}")

    def deserialize(self, data: bytes) -> Any:
        return json.loads(data.decode('utf-8'))


import pyarrow.parquet as pq

class ArrowSerializer:
    """
    Generic PyArrow serializer for columnar data.
    Does not depend on Domain concepts.
    """
    def serialize(self, columns: dict[str, Sequence[Any]], metadata: dict[bytes, bytes] | None = None) -> bytes:
        """
        Converts a dictionary of columns to Parquet bytes.
        `columns` format: {"column_name": [val1, val2, ...], ...}
        """
        arrays = []
        names = []
        for col_name, col_data in columns.items():
            names.append(col_name)
            arrays.append(pa.array(col_data))
        table = pa.table(arrays, names=names)
        
        if metadata:
            existing = table.schema.metadata or {}
            table = table.replace_schema_metadata({**existing, **metadata})
        
        sink = pa.BufferOutputStream()
        pq.write_table(table, sink)
        return sink.getvalue().to_pybytes()

    def deserialize(self, data: bytes) -> tuple[dict[str, list[Any]], dict[bytes, bytes] | None]:
        """
        Converts Parquet bytes back to a dictionary of columns and metadata.
        """
        reader = pa.BufferReader(data)
        table = pq.read_table(reader)
        
        result = {}
        for i, name in enumerate(table.column_names):
            result[name] = table.column(i).to_pylist()
            
        return result, table.schema.metadata
