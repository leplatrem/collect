from typing import Any

from django.contrib.auth.decorators import login_required
from django.db.models import Count
from django.db.models.query import QuerySet
from django.shortcuts import get_object_or_404, render
from django.utils.translation import gettext_lazy as _
from django.views.decorators.http import require_http_methods
from django.views.generic import ListView
from taggit.models import Tag

from collectable.forms import PossessionForm
from collectable.models import Collectable, Possession


def index(request):
    tag_list = (
        Tag.objects.annotate(ncollectable=Count("collectable"))
        .order_by("-ncollectable")
        .filter(ncollectable__gt=0)
    )
    qs = Collectable.objects.with_counts_and_possessions(request.user)

    context = {
        "latest": qs.order_by("-created_at")[:3],
        "most_liked": qs.order_by("-nlikes").filter(nlikes__gt=0)[:3],
        "most_wanted": qs.order_by("-nwants").filter(nwants__gt=0)[:3],
        "most_owned": qs.order_by("-nowns").filter(nowns__gt=0)[:3],
        "tag_list": tag_list,
    }
    return render(request, "collectable/index.html", context)


class CollectableListView(ListView):
    model = Collectable
    sort_by = "-created_at"

    def get_queryset(self) -> QuerySet[Any]:
        qs = self.model.objects.with_counts_and_possessions(self.request.user).order_by(
            self.sort_by
        )

        if self.sort_by == "-nlikes":
            qs = qs.filter(nlikes__gt=0)
        elif self.sort_by == "-nwants":
            qs = qs.filter(nwants__gt=0)
        elif self.sort_by == "-nowns":
            qs = qs.filter(nowns__gt=0)
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = {
            "-created_at": _("Latest collectables"),
            "-nlikes": _("Most liked collectables"),
            "-nwants": _("Most wanted collectables"),
            "-nowns": _("Most owned collectables"),
        }[self.sort_by]
        context["empty_msg"] = {
            "-created_at": _("No collectable in database."),
            "-nlikes": _("No liked collectable"),
            "-nwants": _("No wanted collectable"),
            "-nowns": _("No owned collectable"),
        }[self.sort_by]
        return context


def details(request, id):
    collectable = get_object_or_404(
        Collectable.objects.with_counts_and_possessions(request.user), id=id
    )

    related_collectables = Collectable.objects.with_counts_and_possessions(request.user)
    for tag in collectable.tags.all():
        related_collectables = related_collectables.filter(tags=tag)

    context = {
        "collectable": collectable,
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
    # Refresh counters
    possession.collectable = Collectable.objects.with_counts_and_possessions(
        request.user
    ).get(id=id)
    return render(
        request,
        "collectable/possession_form.html",
        {"form": possession_form},
    )


def collection(request, slugs):
    slugs = slugs.split(",")
    tag_list = list(
        Tag.objects.filter(slug__in=slugs).annotate(ncollectable=Count("collectable"))
    )

    collectable_list = Collectable.objects.with_counts_and_possessions(request.user)

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
    return render(request, "collectable/collection.html", context)


@login_required
def profile(request):
    qs = Collectable.objects.with_counts_and_possessions(request.user)
    liked = qs.filter(possession__user=request.user, possession__likes=True)
    wanted = qs.filter(possession__user=request.user, possession__wants=True)
    owned = qs.filter(possession__user=request.user, possession__owns=True)
    context = {
        "collectable_liked": liked,
        "collectable_wanted": wanted,
        "collectable_owned": owned,
    }
    return render(request, "collectable/profile.html", context)
