from django.conf import settings


def constants(request):
    return {
        "COLLECTABLE_PHOTO_MAX_SIZE": settings.COLLECTABLE_PHOTO_MAX_SIZE,
        "COLLECTABLE_THUMBNAIL_SIZE": settings.COLLECTABLE_THUMBNAIL_SIZE,
    }