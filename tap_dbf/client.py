"""DBF reader."""

from __future__ import annotations

import collections
import datetime
import typing as t
from pathlib import Path

from dbfread import DBF
from dbfread.dbf import expand_year, ifind
from dbfread.exceptions import DBFNotFound
from dbfread.field_parser import FieldParser

if t.TYPE_CHECKING:
    from fsspec import AbstractFileSystem


class FilesystemDBF(DBF):
    """A DBF implementation that can open files in arbitrary filesystems."""

    def __init__(  # noqa: PLR0913
        self,
        filename: str,
        filesystem: AbstractFileSystem,
        *,
        encoding: str | None = None,
        ignorecase: bool = True,
        lowernames: bool = False,
        parserclass: type[FieldParser] = FieldParser,
        recfactory: type[dict] = collections.OrderedDict,
        load: bool = False,
        raw: bool = False,
        ignore_missing_memofile: bool = False,
        char_decode_errors: str = "strict",
    ) -> None:
        """Create a new DBF reader."""
        self.filesystem = filesystem
        self.encoding = encoding
        self.ignorecase = ignorecase
        self.lowernames = lowernames
        self.parserclass = parserclass
        self.raw = raw
        self.ignore_missing_memofile = ignore_missing_memofile
        self.char_decode_errors = char_decode_errors

        self.date: datetime.date | None

        self.recfactory = (lambda items: items) if recfactory is None else recfactory

        # Name part before .dbf is the table name
        self.name = Path(filename).stem
        self._records = None
        self._deleted = None

        if ignorecase:
            self.filename = ifind(filename)
            if not self.filename:
                msg = f"could not find file {filename!r}"
                raise DBFNotFound(msg)
        else:
            self.filename = filename

        # Filled in by self._read_headers()
        self.memofilename = None
        self.header: t.Any | None = None
        self.fields: list[t.Any] = []  # namedtuples
        self.field_names: list[str] = []  # strings

        with self.filesystem.open(self.filename, mode="rb") as infile:
            self._read_header(infile)
            self._read_field_headers(infile)
            self._check_headers()

            try:
                self.date = datetime.date(
                    expand_year(self.header.year),  # type: ignore[attr-defined]
                    self.header.month,  # type: ignore[attr-defined]
                    self.header.day,  # type: ignore[attr-defined]
                )
            except ValueError:
                # Invalid date or '\x00\x00\x00'.
                self.date = None

        self.memofilename = self._get_memofilename()

        if load:
            self.load()

    def _count_records(self, record_type: bytes = b" ") -> int:
        """Count records in the table.

        Args:
            record_type: The record type to count.

        Returns:
            The number of records.
        """
        count = 0

        with self.filesystem.open(self.filename, "rb") as infile:
            # Skip to first record.
            infile.seek(self.header.headerlen, 0)  # type: ignore[union-attr]

            while True:
                sep = infile.read(1)
                if sep == record_type:
                    count += 1
                    self._skip_record(infile)
                elif sep in (b"\x1a", b""):
                    # End of records.
                    break
                else:
                    self._skip_record(infile)

        return count

    def _iter_records(
        self,
        record_type: bytes = b" ",
    ) -> t.Generator[dict, None, None]:
        """Iterate over records in the table.

        Args:
            record_type: The record type to iterate over.

        Yields:
            A record.
        """
        with self.filesystem.open(
            self.filename,
            "rb",
        ) as infile, self._open_memofile() as memofile:
            # Skip to first record.
            infile.seek(self.header.headerlen, 0)  # type: ignore[union-attr]

            if not self.raw:
                field_parser = self.parserclass(self, memofile)
                parse = field_parser.parse

            # Shortcuts for speed.
            skip_record = self._skip_record
            read = infile.read

            while True:
                sep = read(1)

                if sep == record_type:
                    if self.raw:
                        items = [
                            (field.name, read(field.length)) for field in self.fields
                        ]
                    else:
                        items = [
                            (field.name, parse(field, read(field.length)))
                            for field in self.fields
                        ]

                    yield self.recfactory(items)

                elif sep in (b"\x1a", b""):
                    # End of records.
                    break
                else:
                    skip_record(infile)
