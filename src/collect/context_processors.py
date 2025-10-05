from django.conf import settings


def constants(request):
    return {
        "COLLECTABLE_PHOTO_MAX_SIZE": settings.COLLECTABLE_PHOTO_MAX_SIZE,
        "COLLECTABLE_THUMBNAIL_SIZE": settings.COLLECTABLE_THUMBNAIL_SIZE,
        "RELATED_COLLECTABLES_LIST_COUNT": settings.RELATED_COLLECTABLES_LIST_COUNT,
    }


def view_name_classlist(request):
    view_name = request.resolver_match.view_name if request.resolver_match else ""
    return {
        "view_name_classlist": view_name.replace(":", " "),
    }
