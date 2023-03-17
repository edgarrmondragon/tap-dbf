"""Singer SDK classes."""

from __future__ import annotations

import builtins
from pathlib import Path
from typing import TYPE_CHECKING, Any, BinaryIO, Callable, Dict, Generator, Iterable

from dbfread import DBF
from fs.opener import parse, registry
from singer_sdk import Stream, Tap
from singer_sdk.typing import BooleanType, PropertiesList, Property, StringType

if TYPE_CHECKING:
    from os import PathLike
    from types import TracebackType

    from dbfread.dbf import DBFField
    from fs.base import FS

    OpenFunc = Callable[[PathLike, str], BinaryIO]
    RawRecord = Dict[str, Any]


def dbf_field_to_jsonschema(field: DBFField) -> dict[str, Any]:
    """Map a .dbf data type to a JSON schema.

    Args:
        field: The field to map.

    Returns:
        A JSON schema.
    """
    d: dict[str, Any] = {}
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
        d["maxLength"] = field.length

    return d


class PatchOpen:
    """Context helper to patch the builtin open function."""

    def __init__(self: PatchOpen, fs: FS) -> None:
        """Patch builtins.open with a custom open function.

        Args:
            fs: The filesystem instance to use.
        """
        self.old_impl = _patch_open(fs.open)

    def __enter__(self: PatchOpen) -> PatchOpen:
        """Create a context for the patched function.

        Returns:
            The PatchOpen context.
        """
        return self

    def __exit__(
        self: PatchOpen,
        exc_type: type[Exception],
        exc_val: Exception,
        exc_tb: TracebackType,
    ) -> None:
        """Exit context and revert patch.

        Args:
            exc_type: The exception type.
            exc_val: The exception value.
            exc_tb: The exception traceback.
        """
        _patch_open(self.old_impl)


def _patch_open(func: OpenFunc) -> OpenFunc:
    """Patch `builtins.open` with `func`.

    Args:
        func: The function to patch `builtins.open` with.

    Returns:
        The original `builtins.open` function.
    """
    old_impl = builtins.open
    builtins.open = func  # type: ignore[assignment]
    return old_impl  # type: ignore[return-value]


class FilesystemDBF(DBF):
    """A DBF implementation that can open files in arbitrary filesystems."""

    def __init__(
        self,
        *args: Any,
        opener: OpenFunc = open,  # type: ignore[assignment]
        **kwargs: Any,
    ) -> None:
        """Create a new DBF instance.

        Args:
            *args: Positional arguments to pass to the DBF constructor.
            opener: The file opener to use.
            **kwargs: Keyword arguments to pass to the DBF constructor.
        """
        self.opener = opener

        with PatchOpen(opener):
            super().__init__(*args, **kwargs)

    def _count_records(self, record_type: bytes = b" ") -> int:
        """Count records in the table.

        Args:
            record_type: The record type to count.

        Returns:
            The number of records.
        """
        with PatchOpen(self.opener):
            return super()._count_records(record_type)

    def _iter_records(
        self,
        record_type: bytes = b" ",
    ) -> Generator[dict[str, Any], None, None]:
        """Iterate over records in the table.

        Args:
            record_type: The record type to iterate over.

        Yields:
            A record.
        """
        with PatchOpen(self.opener):
            yield from super()._iter_records(record_type)


class DBFStream(Stream):
    """A dBase file stream."""

    def __init__(
        self: DBFStream,
        tap: Tap,
        filepath: PathLike,
        filesystem: FS,
        *,
        ignore_missing_memofile: bool = False,
    ) -> None:
        """Create a new .DBF file stream.

        Args:
            tap: The tap instance.
            filepath: The path to the .DBF file.
            filesystem: The filesystem instance to use.
            ignore_missing_memofile: Whether to ignore missing .DBT files.
        """
        self.filepath = filepath
        self.filesystem = filesystem
        name = Path(filepath).stem

        self._table = FilesystemDBF(
            filepath,
            ignorecase=False,
            ignore_missing_memofile=ignore_missing_memofile,
            opener=filesystem,
        )

        self._fields = list(self._table.fields)
        schema: dict[str, Any] = {"properties": {}}
        self.primary_keys = []

        for field in self._fields:
            schema["properties"][field.name] = dbf_field_to_jsonschema(field)
            if field.type == "+":
                self.primary_keys.append(field.name)

        schema["properties"]["_sdc_filepath"] = {"type": ["string"]}
        schema["properties"]["_sdc_row_index"] = {"type": ["integer"]}

        super().__init__(tap, schema=schema, name=name)

    def get_records(self: DBFStream, _: dict | None = None) -> Iterable[RawRecord]:
        """Get .DBF rows.

        Yields:
            A row of data.
        """
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

    def discover_streams(self: TapDBF) -> list[DBFStream]:
        """Discover .DBF files in the path.

        Returns:
            A list of streams.
        """
        streams = []

        root = self.config["fs_root"]
        parse_result = parse(root)
        opener = registry.get_opener(parse_result.protocol)
        filesystem = opener.open_fs(
            root,
            parse_result,
            writeable=False,
            create=False,
            cwd="",
        )

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
