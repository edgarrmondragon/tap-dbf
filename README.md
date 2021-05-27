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

[memofile]: https://en.wikipedia.org/wiki/.dbf#Memo_fields_and_the_.DBT_file
