"""Singer SDK classes."""

import builtins
from os import PathLike
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from dbfread import DBF  # type: ignore
from dbfread.dbf import DBFField  # type: ignore
from fs.base import FS
from fs.opener import parse, registry
from singer_sdk import Stream, Tap  # type: ignore
from singer_sdk.typing import (  # type: ignore
    BooleanType,
    PropertiesList,
    Property,
    StringType,
)

RawRecord = Dict[str, Any]


def dbf_field_to_jsonschema(field: DBFField) -> Dict[str, Any]:
    """Map a .dbf data type to a JSON schema."""
    d: Dict[str, Any] = {}
    d["type"] = ["null"]

    if field.type == "N":
        if field.decimal_count == 0:
            d["type"].append("integer")
        else:
            d["type"].append("number")
    elif field.type in {"+", "I"}:
        d["type"].append("integer")
    elif field.type in {"B", "F", "O", "Y"}:
        d["type"].append("number")
    elif field.type == "L":
        d["type"].append("boolean")
    elif field.type == "D":
        d["type"].append("string")
        d["format"] = "date-time"
    elif field.type in {"@", "T"}:
        d["type"].append("string")
        d["format"] = "time"
    else:
        d["type"].append("string")

    return d


class patch_open:
    """Context helper to patch the builtin open function."""

    def __init__(self, fs: FS):
        """Patch builtins.open with a custom open function."""
        self.old_impl = _patch_open(fs.open)

    def __enter__(self):
        """Create a context for the patched function."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit context and revert patch."""
        _patch_open(self.old_impl)


def _patch_open(func):
    """Patch `builtins.open` with `func`."""
    old_impl = builtins.open
    builtins.open = func
    return old_impl


class DBFStream(Stream):
    """A dBase file stream."""

    primary_keys = ["_sdc_filepath", "_sdc_row_index"]

    def __init__(
        self,
        tap: Tap,
        filepath: PathLike,
        filesystem: FS,
        ignore_missing_memofile: bool = False,
    ):
        """Create a new .DBF file stream."""
        self.filepath = filepath
        self.filesystem = filesystem
        name = Path(filepath).stem

        with patch_open(filesystem):
            self._table = DBF(
                filepath,
                ignorecase=False,
                load=False,
                ignore_missing_memofile=ignore_missing_memofile,
            )

        self._fields = list(self._table.fields)
        schema = {
            "properties": {
                field.name: dbf_field_to_jsonschema(field) for field in self._fields
            },
        }
        schema["properties"]["_sdc_filepath"] = {"type": ["string"]}
        schema["properties"]["_sdc_row_index"] = {"type": ["integer"]}

        super().__init__(tap, schema=schema, name=name)

    def get_records(self, context: Optional[dict] = None) -> Iterable[RawRecord]:
        """Get .DBF rows."""
        with patch_open(self.filesystem):
            for index, row in enumerate(self._table):
                row["_sdc_filepath"] = self.filepath
                row["_sdc_row_index"] = index
                yield row


class TapDBF(Tap):
    """A singer tap for .DBF files."""

    name = "tap-dbf"
    config_jsonschema = PropertiesList(
        Property("path", StringType, required=True),
        Property("fs_root", StringType, default="file://"),
        Property("ignore_missing_memofile", BooleanType, default=False),
    ).to_dict()

    def discover_streams(self) -> List[DBFStream]:
        """Discover .DBF files in the path."""
        streams = []

        root = self.config["fs_root"]
        parse_result = parse(root)
        opener = registry.get_opener(parse_result.protocol)
        filesystem = opener.open_fs(root, parse_result, False, False, "")

        for match in filesystem.glob(self.config["path"]):
            path = match.path
            stream = DBFStream(
                tap=self,
                filepath=path,
                filesystem=filesystem,
                ignore_missing_memofile=self.config["ignore_missing_memofile"],
            )

            streams.append(stream)

        return streams


cli = TapDBF.cli
