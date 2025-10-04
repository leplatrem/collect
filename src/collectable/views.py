from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Count
from django.db.models.query import QuerySet
from django.forms import widgets as django_widgets
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.translation import gettext_lazy as _
from django.views.decorators.http import require_http_methods
from django.views.generic import ListView
from taggit.models import Tag

from collect.utils import paginate
from collectable.forms import CollectableForm, DuplicateReportForm, PossessionForm
from collectable.models import Collectable, DuplicateReport, Possession


def index(request):
    tag_list = (
        Tag.objects.annotate(ncollectable=Count("collectable"))
        .order_by("-ncollectable")
        .filter(ncollectable__gt=0)
    )
    qs = Collectable.objects.with_counts_and_possessions(request.user)

    context = {
        "total_collectables": len(qs),
        "latest": qs.order_by("-created_at")[: settings.HOME_LIST_COUNT],
        "most_liked": qs.order_by("-nlikes").filter(nlikes__gt=0)[
            : settings.HOME_LIST_COUNT
        ],
        "most_wanted": qs.order_by("-nwants").filter(nwants__gt=0)[
            : settings.HOME_LIST_COUNT
        ],
        "most_owned": qs.order_by("-nowns").filter(nowns__gt=0)[
            : settings.HOME_LIST_COUNT
        ],
        "tag_list": tag_list,
    }
    return render(request, "collectable/index.html", context)


class CollectableListView(ListView):
    model = Collectable
    kind = "latest"
    paginate_by = settings.DEFAULT_PAGE_SIZE

    def get_queryset(self) -> QuerySet[Collectable]:
        sort_by = {
            "latest": "-created_at",
            "search": "-created_at",
            "most_liked": "-nlikes",
            "most_wanted": "-nwants",
            "most_owned": "-nowns",
        }[self.kind]
        qs = self.model.objects.with_counts_and_possessions(self.request.user).order_by(
            sort_by, "-created_at"
        )

        if self.kind == "most_liked":
            qs = qs.filter(nlikes__gt=0)
        elif self.kind == "most_wanted":
            qs = qs.filter(nwants__gt=0)
        elif self.kind == "most_owned":
            qs = qs.filter(nowns__gt=0)

        # Search in description insentitive, and in tags.
        for q in self.search_keywords().split(" "):
            qs = qs.filter(tags__name__in=[q]) | qs.filter(description__icontains=q)
        qs = qs.distinct()

        return qs

    def search_keywords(self) -> str:
        if self.kind == "search" and (q := self.request.GET.get("q")):
            return q
        return ""

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = {
            "latest": _("Latest collectables"),
            "search": _("Search results for '%(q)s'") % {"q": self.search_keywords()},
            "most_liked": _("Most liked collectables"),
            "most_wanted": _("Most wanted collectables"),
            "most_owned": _("Most owned collectables"),
        }[self.kind]
        context["empty_msg"] = {
            "latest": _("No collectable in database."),
            "search": _("No collectable found."),
            "most_liked": _("No liked collectable"),
            "most_wanted": _("No wanted collectable"),
            "most_owned": _("No owned collectable"),
        }[self.kind]
        return context


@require_http_methods(["GET", "POST"])
@login_required
def create(request):
    if request.method == "POST":
        form = CollectableForm(request.POST, request.FILES)
        if form.is_valid():
            collectable = form.save()
            Possession.objects.create(
                user=request.user, collectable=collectable, owns=True
            )
            messages.info(request, _("Collectable created successfully."))
            return redirect(collectable)
        else:
            messages.warning(request, _("Invalid fields, please correct them."))
    else:
        form = CollectableForm()
    context = {
        "form": form,
    }
    return render(request, "collectable/create.html", context)


@require_http_methods(["GET", "POST"])
def details(request, id):
    # Note: hidden collectable will be 404.
    collectable = get_object_or_404(
        Collectable.objects.with_counts_and_possessions(request.user), id=id
    )

    # If this collectable has been reported as duplicate, show that page instead.
    if (
        request.method == "GET"
        and "_skip_duplicate" not in request.GET
        and collectable.is_duplicate()
    ):
        return redirect("collectable:duplicate", id=collectable.id)

    # Simple details page and form.
    if request.method == "POST":
        if not request.user.is_authenticated:
            return HttpResponse(_("Unauthorized"), status=401)
        form = CollectableForm(request.POST, request.FILES, instance=collectable)
        backup_photo = collectable.photo
        if form.is_valid():
            collectable = form.save()
            messages.info(request, _("Collectable updated successfully."))
        else:
            messages.warning(request, _("Invalid fields, please correct them."))
            # Why `is_valid()` is altering `collectable.photo`??
            collectable.photo = backup_photo
    else:
        form = CollectableForm(instance=collectable)

    related_tags = collectable.related_tags()
    related_collectables = collectable.related_collectables(request.user)
    duplicates = collectable.duplicates(request.user)

    duplicate_form = DuplicateReportForm()

    context = {
        "collectable": collectable,
        "form_edit": form,
        "duplicate_form": duplicate_form,
        "related_tags": related_tags,
        "related_collectables": related_collectables,
        "duplicates": duplicates,
    }

    return render(request, "collectable/details.html", context)


@require_http_methods(["GET", "POST"])
def duplicate(request, id):
    """
    This collectable has been reported as a duplicate of another one.

    If POST, user is reporting this collectable as a duplicate of another one.
    If GET, show the original collectable it is a duplicate of.
    """
    # Note: hidden collectable won't be 404.
    collectable = get_object_or_404(Collectable, id=id)

    if request.method == "GET":
        # Check that this collectable is indeed reported as duplicate.
        if duplicate_report := collectable.reports_as_duplicate.first():
            # If this collectable was hidden, then redirect to the original.
            # If the original is hidden, then it will redirect in chain.
            if collectable.hidden:
                messages.info(
                    request,
                    _(
                        "This collectable has been hidden as it was reported as a duplicate. "
                        "You are being redirected to the original."
                    ),
                )
                return redirect(
                    "collectable:duplicate", id=duplicate_report.original.id
                )
        else:
            messages.info(
                request, _("This collectable has not been reported as duplicate.")
            )
            return redirect("collectable:details", id=collectable.id)

    headers = {}

    # Handle duplicate report (or confirmation).
    if request.method == "POST":
        if not request.user.is_authenticated:
            return HttpResponse(_("Unauthorized"), status=401)

        # Original is posted in form.
        form = DuplicateReportForm(request.POST)
        form.instance.duplicate = collectable
        form.instance.reporter = request.user

        if not form.is_valid():
            messages.warning(request, _("Invalid fields, please correct them."))
            # Show invalid form.
            return render(
                request,
                "collectable/details_duplicate.html",
                {"collectable": collectable, "form": form},
            )

        # Save the report!
        form.save()
        messages.info(request, _("Duplicate reported! Thank you!"))
        # On success, we fill the page with the duplicate details.
        headers["HX-Retarget"] = "main"
        headers["HX-Reselect"] = "main"

    # Show the first original. Form was valid, and saved. There is
    # at least the one we just created.
    duplicate_report = collectable.reports_as_duplicate.first()
    assert duplicate_report is not None
    # We show the thumbnail with the possession form.
    original = Collectable.objects.with_counts_and_possessions(request.user).get(
        id=duplicate_report.original.id
    )

    # The confirmation form will have the original pre-selected.
    form = DuplicateReportForm(initial={"original": original})
    form.fields["original_input"].widget = django_widgets.HiddenInput()

    # Show details of who reported and when.
    reports = DuplicateReport.objects.filter(
        original=original, duplicate=collectable
    ).select_related("reporter")
    already_reported = request.user.is_authenticated and request.user.username in {
        r.reporter.username for r in reports
    }

    context = {
        "form": form,
        "already_reported": already_reported,
        "collectable": collectable,
        "original": original,
        "reports": reports,
        "missing_confirmations": settings.DUPLICATE_CONFIRMATION_THRESHOLD
        - (len(reports) - 1),
    }
    response = render(request, "collectable/details_duplicate.html", context)
    for k, v in headers.items():
        response.headers[k] = v
    return response


@require_http_methods(["POST"])
@login_required
def possession(request, id):
    collectable = get_object_or_404(Collectable, id=id)
    possession, _created = Possession.objects.get_or_create(
        user=request.user, collectable=collectable
    )
    possession_form = PossessionForm(request.POST, instance=possession)
    if possession_form.is_valid():
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

    collectable_list = Collectable.objects.with_counts_and_possessions(
        request.user
    ).order_by("-created_at")

    for slug in slugs:
        collectable_list = collectable_list.filter(tags__slug=slug)

    # Count how many are owned by the current user, taking advantage of prefetched
    # data from above.
    total_owned = sum(
        1
        for c in collectable_list
        if getattr(c, "possession_set_list", []) and c.possession_set_list[0].owns
    )

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
        .filter(ncollectable__gt=1)
    )

    context = {
        "slugs": slugs,
        "collectable_list": collectable_list,
        "page_obj": paginate(request, qs=collectable_list),
        "tag_list": tag_list,
        "reltag_list": reltag_list,
        "total_owned": total_owned,
        "percent_owned": 100 * total_owned / max(len(collectable_list), 1),
    }
    return render(request, "collectable/collection.html", context)


@login_required
def profile(request):
    qs = Collectable.objects.with_counts_and_possessions(request.user)
    context = {
        "collectable_liked": qs.liked_by(request.user),
        "collectable_wanted": qs.wanted_by(request.user),
        "collectable_owned": qs.owned_by(request.user),
    }
    return render(request, "collectable/profile.html", context)
