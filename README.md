# Collect

Publish and track your collectables.

## Features

- Build collections using tags (eg. #stickers, #badges, #corp, #2024)
- Browse collections and sub-collections
- Track the items you own, like, or want
- Discover how much of the collections you own
- Turn folders of images files into collections (see below)

## Get started

### Run locally

```
make start
```

### Create users

Users can sign-up using a secret word. See ``SIGNUP_SECRETS_WORDS`` in your ``.env`` file.

To create an admin super-user:
```
poetry run python manage.py createsuperuser
```
You can then access to http://localhost:8000/admin/


### Import collectables from folder

Specify a `username` for the creator of the imported collectables, and a `folder` to import from.

The sub-folders will be used as tags, and additional tags can be specified.

If all collectables belong to the same owner, specify the username with `--owner`.

Example:
```
poetry run python ./manage.py loadfolder user ~/stickaz/ --owner=user --tags=tag1 --tags=tag2
```

The command can be executed multiple times with the same folder, and only new files will be added.

> Note: the `loadfolder` command relies on EXIF tags (`Date` of shot and camera `Model`) to uniquely
> identify pictures, so that files can be moved into folders and not be duplicated.


## License

* BSD 3-Clause License
