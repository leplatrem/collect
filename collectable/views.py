from django.db.models import Count, Q
from django.http import Http404
from django.shortcuts import render
from taggit.models import Tag

from collectable.models import Collectable


def index(request):
    tag_list = Tag.objects.annotate(ncollectable=Count("collectable")).order_by(
        "-ncollectable"
    )
    qs = (
        Collectable.objects.annotate(
            nwanted=Count("possessions", filter=Q(possession__wants=True))
        )
        .annotate(nliked=Count("possessions", filter=Q(possession__likes=True)))
        .annotate(nowned=Count("possessions", filter=Q(possession__owns=True)))
    )
    context = {
        "most_wanted": qs.order_by("-nwanted").filter(nwanted__gt=0)[:3],
        "most_liked": qs.order_by("-nliked").filter(nliked__gt=0)[:3],
        "most_owned": qs.order_by("-nowned").filter(nowned__gt=0)[:3],
        "tag_list": tag_list,
    }
    return render(request, "collectable/index.html", context)


def details(request, id):
    qs = Collectable.objects.filter(id=id)
    if not qs.exists():
        raise Http404("No collectable matches the given query.")

    qs = (
        qs.annotate(nwanted=Count("possessions", filter=Q(possession__wants=True)))
        .annotate(nliked=Count("possessions", filter=Q(possession__likes=True)))
        .annotate(nowned=Count("possessions", filter=Q(possession__owns=True)))
    )
    collectable = qs[0]
    context = {
        "collectable": collectable,
    }
    return render(request, "collectable/details.html", context)


def by_tags(request, slugs):
    slugs = slugs.split(",")
    tag_list = list(
        Tag.objects.filter(slug__in=slugs).annotate(ncollectable=Count("collectable"))
    )

    collectable_list = (
        Collectable.objects.annotate(
            nwanted=Count("possessions", filter=Q(possession__wants=True))
        )
        .annotate(nliked=Count("possessions", filter=Q(possession__likes=True)))
        .annotate(nowned=Count("possessions", filter=Q(possession__owns=True)))
    )

    for slug in slugs:
        collectable_list = collectable_list.filter(tags__slug=slug)

    known_tag_slugs = [t.slug for t in tag_list]
    for slug in slugs:
        if slug not in known_tag_slugs:
            tag_list.append(Tag(name=slug, slug=slug))  # Don't save.

    subtag_list = (
        Tag.objects.filter(
            collectable__id__in=collectable_list.values_list("id", flat=True)
        )
        .exclude(slug__in=slugs)
        .annotate(ncollectable=Count("collectable"))
        .order_by("-ncollectable")
    )

    context = {
        "slugs": slugs,
        "collectable_list": collectable_list,
        "tag_list": tag_list,
        "subtag_list": subtag_list,
    }
    return render(request, "collectable/by_tags.html", context)
