from datetime import date, datetime, timedelta, timezone as datetime_timezone

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import TestCase
from django.utils import timezone

from api.features.applications.models import Application


class ApplicationPaginationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        User = get_user_model()
        cls.user = User.objects.create_user(username="customer")
        cls.other_user = User.objects.create_user(username="other")
        cls.admin = User.objects.create_user(username="admin")
        cls.admin.groups.add(Group.objects.create(name="admin"))

        for index in range(25):
            Application.objects.create(
                id=f"application-{index:02}",
                owner=cls.user,
                project_title=f"Application {index}",
                company_no="123",
                incorporation_date=date(2020, 1, 1),
                contact_person="Contact",
                telephone="123",
                business_nature="Business",
                business_location="Location",
                loan_amount=100,
                email="test@example.com",
            )
        Application.objects.create(
            id="other-application",
            owner=cls.other_user,
            project_title="Other application",
            company_no="123",
            incorporation_date=date(2020, 1, 1),
            contact_person="Contact",
            telephone="123",
            business_nature="Business",
            business_location="Location",
            loan_amount=100,
            email="test@example.com",
        )
        Application.objects.update(created_at=timezone.now())

    def test_consecutive_pages_apply_skip_once(self):
        self.client.force_login(self.user)
        first = self.client.get("/api/applications/", {"skip": 0, "take": 10})
        second = self.client.get("/api/applications/", {"skip": 10, "take": 10})
        third = self.client.get("/api/applications/", {"skip": 20, "take": 10})

        expected = [f"application-{index:02}" for index in reversed(range(25))]
        for response, page in zip(
            (first, second, third), (expected[:10], expected[10:20], expected[20:])
        ):
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json()["total"], 25)
            self.assertEqual([item["id"] for item in response.json()["data"]], page)

    def test_defaults_and_boundaries(self):
        self.client.force_login(self.user)
        self.assertEqual(len(self.client.get("/api/applications/").json()["data"]), 25)
        response = self.client.get("/api/applications/", {"skip": 10})
        self.assertEqual(len(response.json()["data"]), 15)
        response = self.client.get("/api/applications/", {"take": 0})
        self.assertEqual(response.json()["data"], [])
        response = self.client.get("/api/applications/", {"skip": 100, "take": 10})
        self.assertEqual(response.json()["data"], [])
        for params in ({"skip": -1}, {"take": -1}, {"skip": "abc"}, {"take": "abc"}):
            self.assertEqual(self.client.get("/api/applications/", params).status_code, 422)

    def test_newest_applications_are_first(self):
        Application.objects.filter(id="application-00").update(
            created_at=timezone.now() + timedelta(days=1)
        )
        self.client.force_login(self.user)
        response = self.client.get("/api/applications/", {"take": 1})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["data"][0]["id"], "application-00")

    def test_admin_total_and_pagination_include_other_users(self):
        self.client.force_login(self.admin)
        response = self.client.get("/api/applications/", {"skip": 0, "take": 1})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["total"], 26)
        self.assertEqual(
            [item["id"] for item in response.json()["data"]], ["other-application"]
        )


class ApplicationFilterTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        User = get_user_model()
        cls.user = User.objects.create_user(username="filter-customer")
        cls.other_user = User.objects.create_user(username="filter-other")
        cls.admin = User.objects.create_user(username="filter-admin")
        cls.admin.groups.add(Group.objects.create(name="admin"))

        for index, owner in enumerate((cls.user, cls.user, cls.user, cls.other_user)):
            app = Application.objects.create(
                id=f"filter-{index}",
                owner=owner,
                project_title=("Solar project" if index == 0 else f"Project {index}"),
                company_no=("CO-SOLAR" if index == 1 else f"CO-{index}"),
                incorporation_date=date(2020 + index, 1, 1),
                contact_person="Contact",
                telephone="123",
                business_nature="Business",
                business_location="Location",
                loan_amount=100 * (index + 1),
                email="solar@example.com" if index == 2 else f"user{index}@example.com",
            )
            Application.objects.filter(pk=app.pk).update(
                state=("draft", "submitted", "screening", "submitted")[index],
                created_at=datetime(2023, 1, index + 1, 12, tzinfo=datetime_timezone.utc),
                updated_at=datetime(2024, 1, index + 1, 12, tzinfo=datetime_timezone.utc),
            )
    def setUp(self):
        self.client.force_login(self.user)

    def assert_filter(self, params, expected):
        response = self.client.get("/api/applications/", params)
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.json()["total"], len(expected))
        self.assertEqual({item["id"] for item in response.json()["data"]}, set(expected))

    def test_search_across_fields_is_case_insensitive_and_respects_owner(self):
        self.assert_filter({"search": "SoLaR"}, ["filter-0", "filter-1", "filter-2"])
        self.assert_filter({"search": "co-solar"}, ["filter-1"])
        self.assert_filter({"search": "solar@example"}, ["filter-2"])
        self.assert_filter({"search": "user3"}, [])
        self.client.force_login(self.admin)
        self.assert_filter({"search": "user3"}, ["filter-3"])

    def test_status_membership_and_exclusion(self):
        self.assert_filter(
            {"status_in": ["draft", "submitted"]}, ["filter-0", "filter-1"]
        )
        self.assert_filter(
            {"status_not_in": ["draft", "submitted"]}, ["filter-2"]
        )
        self.assert_filter(
            {"status_in": ["draft", "submitted"], "status_not_in": ["draft"]},
            ["filter-1"],
        )

    def test_date_and_amount_comparisons(self):
        for field, first, second in (
            ("created_at", "2023-01-01", "2023-01-02"),
            ("updated_at", "2024-01-01", "2024-01-02"),
            ("incorporation_date", "2020-01-01", "2021-01-01"),
            ("loan_amount", "100", "200"),
        ):
            for suffix, value, expected in (
                ("eq", second, ["filter-1"]),
                ("gt", second, ["filter-2"]),
                ("gte", second, ["filter-1", "filter-2"]),
                ("lt", second, ["filter-0"]),
                ("lte", second, ["filter-0", "filter-1"]),
            ):
                with self.subTest(field=field, operator=suffix):
                    self.assert_filter({f"{field}_{suffix}": value}, expected)
            with self.subTest(field=field, operator="between"):
                self.assert_filter(
                    {f"{field}_gte": first, f"{field}_lte": second},
                    ["filter-0", "filter-1"],
                )

    def test_combined_filters_precede_count_and_pagination(self):
        response = self.client.get(
            "/api/applications/",
            {
                "search": "project",
                "status_in": ["submitted", "screening"],
                "loan_amount_gte": "200",
                "skip": 1,
                "take": 1,
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["total"], 2)
        self.assertEqual([item["id"] for item in response.json()["data"]], ["filter-1"])

    def test_invalid_filter_values_are_rejected(self):
        for params in (
            {"created_at_gte": "not-a-date"},
            {"incorporation_date_lt": "2023-02-30"},
            {"loan_amount_gte": "not-a-number"},
            {"loan_amount_lte": "NaN"},
        ):
            with self.subTest(params=params):
                response = self.client.get("/api/applications/", params)
                self.assertEqual(response.status_code, 422)
