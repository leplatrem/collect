from django.contrib.auth.decorators import login_required
from django.db.models import Count
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_http_methods
from taggit.models import Tag

from collectable.forms import PossessionForm
from collectable.models import Collectable, Possession


def index(request):
    tag_list = Tag.objects.annotate(ncollectable=Count("collectable")).order_by(
        "-ncollectable"
    )
    qs = Collectable.objects.with_counts()
    context = {
        "latest": qs.order_by("-created_at")[:6],
        "most_wanted": qs.order_by("-nwants").filter(nwants__gt=0)[:6],
        "most_liked": qs.order_by("-nlikes").filter(nlikes__gt=0)[:6],
        "most_owned": qs.order_by("-nowns").filter(nowns__gt=0)[:6],
        "tag_list": tag_list,
    }
    return render(request, "collectable/index.html", context)


def details(request, id):
    collectable = get_object_or_404(Collectable.objects.with_counts(), id=id)

    possession = None
    if request.user.is_authenticated:
        possession = Possession.objects.filter(
            user=request.user, collectable=collectable
        ).first()
    if possession is None:
        possession = Possession(
            collectable=collectable, likes=False, wants=False, owns=False
        )
    possession_form = PossessionForm(instance=possession)

    related_collectables = Collectable.objects.with_counts()
    for tag in collectable.tags.all():
        related_collectables = related_collectables.filter(tags=tag)

    context = {
        "collectable": collectable,
        "possession": possession,
        "possession_form": possession_form,
        "related_collectables": related_collectables,
    }

    return render(request, "collectable/details.html", context)


@require_http_methods(["POST"])
@login_required
def possession(request, id):
    collectable = get_object_or_404(Collectable, id=id)
    possession, _created = Possession.objects.get_or_create(
        user=request.user, collectable=collectable
    )
    possession_form = PossessionForm(request.POST, instance=possession)
    possession = possession_form.save()
    return render(
        request,
        "collectable/possession_form.html",
        {
            "form": possession_form,
            "possession": possession,
            "collectable": Collectable.objects.with_counts().get(id=id),
        },
    )


def by_tags(request, slugs):
    slugs = slugs.split(",")
    tag_list = list(
        Tag.objects.filter(slug__in=slugs).annotate(ncollectable=Count("collectable"))
    )

    collectable_list = Collectable.objects.with_counts()

    for slug in slugs:
        collectable_list = collectable_list.filter(tags__slug=slug)

    known_tag_slugs = [t.slug for t in tag_list]
    for slug in slugs:
        if slug not in known_tag_slugs:
            tag_list.append(Tag(name=slug, slug=slug))  # Don't save.

    reltag_list = (
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
        "reltag_list": reltag_list,
    }
    return render(request, "collectable/by_tags.html", context)


@login_required
def profile(request):
    qs = Collectable.objects.with_counts()
    liked = qs.filter(possession__user=request.user, possession__likes=True)
    wanted = qs.filter(possession__user=request.user, possession__wants=True)
    owned = qs.filter(possession__user=request.user, possession__owns=True)
    context = {
        "collectable_liked": liked,
        "collectable_wanted": wanted,
        "collectable_owned": owned,
    }
    return render(request, "collectable/profile.html", context)
