# tap-dbf

Singer tap for the [dBase file format](https://en.wikipedia.org/wiki/.dbf).

## Configuration

| Setting                 | Required | Default | Description |
|:------------------------|:--------:|:-------:|:------------|
| path                    | True     | None    | Glob expression where the files are located. Stream names will be extracted from the file name. |
| fs_root                 | False    | file:// | The root of the filesystem to read from. |
| ignore_missing_memofile | False    |       0 | Whether to proceed reading the file even if the [memofile] is not present. |
| s3                      | False    | None    | S3 configuration. |
| gcs                     | False    | None    | GCS configuration. |
| stream_maps             | False    | None    | Config object for stream maps capability. For more information check out [Stream Maps](https://sdk.meltano.com/en/latest/stream_maps.html). |
| stream_map_config       | False    | None    | User-defined config values to be used within map expressions. |
| faker_config            | False    | None    | Config for the [`Faker`](https://faker.readthedocs.io/en/master/) instance variable `fake` used within map expressions. Only applicable if the plugin specifies `faker` as an addtional dependency (through the `singer-sdk` `faker` extra or directly). |
| flattening_enabled      | False    | None    | 'True' to enable schema flattening and automatically expand nested properties. |
| flattening_max_depth    | False    | None    | The max depth to flatten schemas. |
| batch_config            | False    | None    |             |

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

### Google Cloud Storage

You need to install the package with the `gcs` extra:

```shell
pip install 'tap-dbf[gcs]'
```

Example configuration:

```json
{
  "path": "/*.dbf",
  "fs_root": "gcs://files",
  "ignore_missing_memofile": true,
  "gcs": {
    "token": "cloud"
  }
}
```

See https://gcsfs.readthedocs.io/en/latest/#credentials for more information about the `token` key.

## Roadmap

- Google Drive filesystem
- Dropbox filesystem

[memofile]: https://en.wikipedia.org/wiki/.dbf#Memo_fields_and_the_.DBT_file
