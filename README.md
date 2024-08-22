# Collect

Publish and track your collectables.

## Get started

### Run locally

Default configuration:
```
cp env.local .env
```

Install dependencies
```
poetry install
```

Initialize database:
```
poetry run python manage.py migrate
```

Create admin user:
```
python manage.py createsuperuser
```

Start server:
```
python manage.py runserver
```

### Import collectables from folder

Specify a `username` for the creator of the imported collectables, and a `folder` to import from.

The sub-folders will be used as tags, and additional tags can be specified.

If all collectables belong to the same owner, specify their username with `--owner`

```
poetry run python ./manage.py loadfolder user ~/stickaz/ --owner=user --tags=tag1 --tags=tag2
```

> Note: the `loadfolder` command relies on EXIF tags (`Date` of shot and camera `Model`) to uniquely
> identify pictures, so that pictures can be moved into folders and not be duplicated.


## License

* BSD 3-Clause License
