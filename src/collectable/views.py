from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Count
from django.db.models.query import QuerySet
from django.forms import widgets as django_widgets
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.views.decorators.http import require_http_methods
from django.views.generic import ListView
from taggit.models import Tag

from collect.utils import paginate
from collectable.forms import CollectableForm, DuplicateReportForm, PossessionForm
from collectable.models import Collectable, DuplicateReport, Possession


def index(request):
    # List of all tags with at least one collectable, ordered by
    # number of collectables.
    tag_list = (
        Tag.objects.annotate(ncollectable=Count("collectable"))
        .order_by("-ncollectable")
        .filter(ncollectable__gt=1)
    )
    # Add a size group for styling. Skip the biggest one.
    max_count = tag_list[1].ncollectable if len(tag_list) > 1 else 1
    group_count = 10
    group_size = max_count // group_count if max_count >= group_count else 1
    for t in tag_list:
        t.size_group = min(t.ncollectable // group_size + 1, group_count)

    # Get all collectables, with tags, possessions counts, and possessions
    # for the current user.
    # Since we use `prefetch_related()` for possessions and tags, we first have
    # to query the IDs of the collectables we want to show.
    # https://docs.djangoproject.com/en/stable/ref/models/querysets/#when-querysets-are-evaluated
    base_qs = Collectable.objects.only("id").with_possession_counts()
    querysets = {
        "latest": base_qs.order_by("-created_at")[: settings.HOME_LIST_COUNT],
        "most_liked": base_qs.order_by("-nlikes").filter(nlikes__gt=0)[
            : settings.HOME_LIST_COUNT
        ],
        "most_wanted": base_qs.order_by("-nwants").filter(nwants__gt=0)[
            : settings.HOME_LIST_COUNT
        ],
        "most_owned": base_qs.order_by("-nowns").filter(nowns__gt=0)[
            : settings.HOME_LIST_COUNT
        ],
    }

    context = {
        "total_collectables": Collectable.objects.count(),
        "latest": Collectable.objects.filter(pk__in=querysets["latest"])
        .with_possession_counts()
        .prefetch_tags_and_possessions(request.user),
        "most_liked": Collectable.objects.filter(pk__in=querysets["most_liked"])
        .with_possession_counts()
        .prefetch_tags_and_possessions(request.user),
        "most_wanted": Collectable.objects.filter(pk__in=querysets["most_wanted"])
        .with_possession_counts()
        .prefetch_tags_and_possessions(request.user),
        "most_owned": Collectable.objects.filter(pk__in=querysets["most_owned"])
        .with_possession_counts()
        .prefetch_tags_and_possessions(request.user),
        "tag_list": tag_list,
    }
    return render(request, "collectable/index.html", context)


class CollectableListView(ListView):
    model = Collectable
    kind = "latest"
    paginate_by = settings.DEFAULT_PAGE_SIZE

    def get_queryset(self) -> QuerySet[Collectable]:
        qs = (
            super()
            .get_queryset()
            .with_possession_counts()
            .prefetch_tags_and_possessions(self.request.user)
        )
        sort_by = {
            "latest": "-created_at",
            "search": "-created_at",
            "most_liked": "-nlikes",
            "most_wanted": "-nwants",
            "most_owned": "-nowns",
        }[self.kind]
        qs = qs.order_by(sort_by, "-created_at")

        if self.kind == "most_liked":
            qs = qs.filter(nlikes__gt=0)
        elif self.kind == "most_wanted":
            qs = qs.filter(nwants__gt=0)
        elif self.kind == "most_owned":
            qs = qs.filter(nowns__gt=0)
        elif self.kind == "search":
            qs = qs.search_keywords(
                self.search_keywords.split(" ")[: settings.MAX_SEARCH_KEYWORDS]
            )

        store_current_list_in_session(self.request, qs)

        return qs

    @property
    def search_keywords(self) -> str:
        return self.request.GET.get("q", "").strip()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = {
            "latest": _("Latest collectables"),
            "search": _("Search results for '%(q)s'") % {"q": self.search_keywords},
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
            messages.success(request, _("Collectable created successfully."))
            return redirect(collectable)
        else:
            messages.warning(request, _("Invalid fields, please correct them."))
    else:
        form = CollectableForm()
    context = {
        "form": form,
    }
    return render(request, "collectable/create.html", context)


def store_current_list_in_session(request, qs: QuerySet[Collectable]):
    """
    Store the current list of collectable IDs in session, for easy navigation
    between previous and next in details view.
    We only store the first 1000 IDs to avoid bloating the session.
    """
    # Store the current list in session, for easy navigation in details view.
    # We store only the IDs, as strings, to be JSON serializable.
    request.session["collectable_list"] = [
        str(id_) for id_ in qs.values_list("id", flat=True)[:1000]
    ]
    request.session.modified = True


def adjacent_in_list(request, collectable):
    """
    Previous and next collectable in list, for easy navigation.
    We use the last viewed list stored in session, if any.
    Otherwise, we use the whole collectables list, sorted by creation date.
    """
    if "collectable_list" in request.session:
        collectable_list = request.session["collectable_list"]
        if len(collectable_list) < 2:
            return None, None
        try:
            index = collectable_list.index(str(collectable.id))
        except ValueError:
            index = None
        if index is not None:
            previous_id = (
                collectable_list[index - 1] if index > 0 else collectable_list[-1]
            )
            next_id = collectable_list[(index + 1) % len(collectable_list)]
            try:
                previous_in_list = Collectable.objects.get(id=previous_id)
                next_in_list = Collectable.objects.get(id=next_id)
                return previous_in_list, next_in_list
            except Collectable.DoesNotExist:
                pass
    # Not found in list, fallback to full list.
    try:
        previous_in_list = collectable.get_previous_by_created_at()
    except Collectable.DoesNotExist:
        previous_in_list = None
    try:
        next_in_list = collectable.get_next_by_created_at()
    except Collectable.DoesNotExist:
        next_in_list = None
    return previous_in_list, next_in_list


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
            messages.success(request, _("Collectable updated successfully."))
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

    previous_in_list, next_in_list = adjacent_in_list(request, collectable)

    context = {
        "collectable": collectable,
        "form_edit": form,
        "duplicate_form": duplicate_form,
        "related_tags": related_tags,
        "related_collectables": related_collectables,
        "duplicates": duplicates,
        "next_in_list": next_in_list,
        "previous_in_list": previous_in_list,
    }

    return render(request, "collectable/details.html", context)


@require_http_methods(["GET", "POST", "DELETE"])
def duplicate(request, id):
    """
    This collectable has been reported as a duplicate of another one.

    If POST, user is reporting this collectable as a duplicate of another one.
    If GET, show the original collectable it is a duplicate of.
    """
    # Note: hidden collectable won't be 404.
    collectable = get_object_or_404(Collectable.all_objects.all(), id=id)

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
    if request.method == "DELETE":
        if not request.user.is_authenticated:
            return HttpResponse(_("Unauthorized"), status=401)
        # User is cancelling their report.
        try:
            report = DuplicateReport.objects.get(
                reporter=request.user, duplicate=collectable
            )
        except DuplicateReport.DoesNotExist:
            messages.warning(request, _("You have not reported this duplicate."))
            return HttpResponse(_("Not Found"), status=404)
        report.delete()
        messages.success(request, _("Your duplicate report has been cancelled."))
        response = HttpResponse(status=204)  # No content
        response["HX-Redirect"] = reverse("collectable:details", args=[collectable.id])
        return response

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
        messages.success(request, _("Duplicate reported! Thank you!"))
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
    form = DuplicateReportForm(initial={"original_input": original.id})
    form.fields["original_input"].widget = django_widgets.HiddenInput()

    # Show details of who reported and when.
    reports = DuplicateReport.objects.filter(
        original=original, duplicate=collectable
    ).select_related("reporter")
    already_reported = request.user.is_authenticated and request.user.username in {
        r.reporter.username for r in reports
    }
    missing_confirmations = settings.DUPLICATE_CONFIRMATION_THRESHOLD - (
        len(reports) - 1
    )

    previous_in_list, next_in_list = adjacent_in_list(request, collectable)

    context = {
        "form": form,
        "already_reported": already_reported,
        "collectable": collectable,
        "original": original,
        "reports": reports,
        "missing_confirmations": missing_confirmations,
        "next_in_list": next_in_list,
        "previous_in_list": previous_in_list,
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

    store_current_list_in_session(request, collectable_list)

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
