# tap-dbf

Singer tap for the [dBase file format](https://en.wikipedia.org/wiki/.dbf).

## Configuration

| Key                       | Description                                                                                     | Type    | Required | Default |
|---------------------------|-------------------------------------------------------------------------------------------------|---------|----------|---------|
| `path`                    | Glob expression where the files are located. Stream names will be extracted from the file name. | string  | yes      |         |
| `ignore_missing_memofile` | Whether to proceed reading the file even if the [memofile] is not present                       | boolean | no       | false   |

### JSON example

```json
{
  "path": "tests/data/files/*.dbf",
  "ignore_missing_memofile": true
}
```

## Filesystems

### Local

Example configuration:

```json
{
  "path": "/files/*.dbf",
  "fs_root": "file://data",
  "ignore_missing_memofile": true
}
```

The `fs_root` key is optional and defaults to the current working directory:

```json
{
  "path": "data/files/*.dbf",
  "ignore_missing_memofile": true
}
```

### S3

You need to install the package with the `s3` extra:

```shell
pip install 'tap-dbf[s3]'
```

Example configuration:

```json
{
  "path": "/*.dbf",
  "fs_root": "s3://files",
  "ignore_missing_memofile": true,
  "s3": {
    "key": "someKey",
    "secret": "someSecret",
    "endpoint_url": "http://localhost:9000"
  }
}
```

## Roadmap

- Google Drive filesystem
- Dropbox filesystem

[memofile]: https://en.wikipedia.org/wiki/.dbf#Memo_fields_and_the_.DBT_file
