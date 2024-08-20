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

> Warning: the `loadfolder` command has some limitations when running it multiple times on the same folder.
> Since the path relative to the specified folder will be used as the collectable identifier, if a
> file is moved from a folder to another between two executions, it will be duplicated instead of updated.


## License

* BSD 3-Clause License
