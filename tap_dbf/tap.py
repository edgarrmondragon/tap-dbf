"""Singer SDK classes."""

from __future__ import annotations

import builtins
import typing as t
from pathlib import Path
from urllib.parse import parse_qsl, urlparse, urlunparse

import fsspec
import singer_sdk.typing as th
from singer_sdk import Stream, Tap

from tap_dbf.client import FilesystemDBF

if t.TYPE_CHECKING:
    import sys
    from os import PathLike
    from types import TracebackType

    from dbfread.dbf import DBFField
    from fsspec import AbstractFileSystem

    if sys.version_info >= (3, 11):
        from typing import Self
    else:
        from typing_extensions import Self

    OpenFunc = t.Callable[[PathLike, str], t.BinaryIO]
    RawRecord = t.Dict[str, t.Any]


def dbf_field_to_jsonschema(field: DBFField) -> dict[str, t.Any]:
    """Map a .dbf data type to a JSON schema.

    Args:
        field: The field to map.

    Returns:
        A JSON schema.
    """
    d: dict[str, t.Any] = {"type": ["null"]}
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

    def __init__(self: PatchOpen, fs: AbstractFileSystem) -> None:
        """Patch builtins.open with a custom open function.

        Args:
            fs: The filesystem instance to use.
        """
        self.old_impl = _patch_open(fs.open)

    def __enter__(self: Self) -> Self:
        """Create a context for the patched function.

        Returns:
            The PatchOpen context.
        """
        return self

    def __exit__(
        self: PatchOpen,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
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


class DBFStream(Stream):
    """A dBase file stream."""

    def __init__(
        self: DBFStream,
        tap: Tap,
        filepath: str,
        filesystem: AbstractFileSystem,
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

        self._table: FilesystemDBF = FilesystemDBF(
            filepath,
            ignorecase=False,
            ignore_missing_memofile=ignore_missing_memofile,
            filesystem=filesystem,
        )

        self._fields = list(self._table.fields)
        schema: dict[str, t.Any] = {"properties": {}}
        self.primary_keys = []

        for field in self._fields:
            schema["properties"][field.name] = dbf_field_to_jsonschema(field)
            if field.type == "+":
                self.primary_keys.append(field.name)

        schema["properties"]["_sdc_filepath"] = {"type": ["string"]}
        schema["properties"]["_sdc_row_index"] = {"type": ["integer"]}

        super().__init__(tap, schema=schema, name=name)

    def get_records(self: DBFStream, _: dict | None = None) -> t.Iterable[RawRecord]:
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
    config_jsonschema = th.PropertiesList(
        th.Property("path", th.StringType, required=True),
        th.Property("fs_root", th.StringType, default="file://"),
        th.Property("ignore_missing_memofile", th.BooleanType, default=False),
        th.Property(
            "s3",
            th.ObjectType(
                th.Property("key", th.StringType, secret=True),
                th.Property("secret", th.StringType, secret=True),
                th.Property("endpoint_url", th.StringType),
            ),
        ),
    ).to_dict()

    def discover_streams(self: TapDBF) -> list[DBFStream]:
        """Discover .DBF files in the path.

        Returns:
            A list of streams.
        """
        streams = []

        fs_root: str = self.config["fs_root"]
        url = urlparse(fs_root)
        protocol = url.scheme

        storage_options = {
            **dict(parse_qsl(url.query)),
            **self.config.get(protocol, {}),
        }

        fs: AbstractFileSystem = fsspec.filesystem(url.scheme, **storage_options)

        full_path = urlunparse(
            url._replace(
                query="",
                netloc=url.hostname or "",
                path=url.path + self.config["path"],
            ),
        )
        for match in fs.glob(full_path):
            stream = DBFStream(
                tap=self,
                filepath=match,
                filesystem=fs,
                ignore_missing_memofile=self.config["ignore_missing_memofile"],
            )

            streams.append(stream)

        return streams


cli = TapDBF.cli
