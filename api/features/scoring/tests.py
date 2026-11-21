from datetime import date

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import TestCase

from api.features.applications.models import Application
from api.features.scoring.models import ApplicationScoring, ScoringCriterion
from api.features.scoring.services import raw_total, weighted_total


def grant_permissions(user, *codenames):
    user.user_permissions.add(
        *Permission.objects.filter(
            content_type__app_label="scoring", codename__in=codenames
        )
    )


class ScoringCriterionModelTests(TestCase):
    def test_weight_and_max_score_constraints(self):
        from django.core.exceptions import ValidationError

        criterion = ScoringCriterion(name="X", weight=-1, max_score=5)
        with self.assertRaises(ValidationError):
            criterion.full_clean()

        criterion = ScoringCriterion(name="Y", weight=1, max_score=0)
        with self.assertRaises(ValidationError):
            criterion.full_clean()

    def test_boolean_score_validation(self):
        from django.core.exceptions import ValidationError

        criterion = ScoringCriterion.objects.create(
            name="Bool", score_type=ScoringCriterion.ScoreType.BOOLEAN, max_score=5
        )
        scoring = ApplicationScoring.objects.create(
            application=Application.objects.create(
                owner=get_user_model().objects.create_user(username="owner"),
                project_title="App",
                company_no="CO",
                incorporation_date=date(2025, 1, 1),
                contact_person="P",
                telephone="1",
                business_nature="B",
                business_location="L",
                loan_amount=100,
                email="o@example.com",
            ),
            scorer=get_user_model().objects.create_user(username="scorer"),
        )
        from api.features.scoring.models import ApplicationScore

        bad = ApplicationScore(scoring=scoring, criterion=criterion, score=2)
        with self.assertRaises(ValidationError):
            bad.full_clean()

        good = ApplicationScore(scoring=scoring, criterion=criterion, score=5)
        good.full_clean()


class ScoringServiceTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        user_model = get_user_model()
        cls.owner = user_model.objects.create_user(username="owner2")
        cls.scorer = user_model.objects.create_user(username="scorer2")
        cls.application = Application.objects.create(
            owner=cls.owner,
            project_title="App",
            company_no="CO",
            incorporation_date=date(2025, 1, 1),
            contact_person="P",
            telephone="1",
            business_nature="B",
            business_location="L",
            loan_amount=100,
            email="o@example.com",
        )
        cls.criterion = ScoringCriterion.objects.create(
            name="Financial", weight=2, max_score=10
        )
        cls.scoring = ApplicationScoring.objects.create(
            application=cls.application, scorer=cls.scorer
        )
        from api.features.scoring.models import ApplicationScore

        ApplicationScore.objects.create(
            scoring=cls.scoring, criterion=cls.criterion, score=5
        )

    def test_raw_total(self):
        self.assertEqual(raw_total(self.scoring), 5)

    def test_weighted_total(self):
        self.assertEqual(weighted_total(self.scoring), 10)


class ScoringEndpointTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        user_model = get_user_model()
        cls.owner = user_model.objects.create_user(username="owner3")
        cls.scorer = user_model.objects.create_user(username="scorer3")
        grant_permissions(cls.scorer, "score_application", "view_all_scores")
        cls.reviewer = user_model.objects.create_user(username="reviewer3")
        grant_permissions(cls.reviewer, "view_all_scores")
        cls.admin = user_model.objects.create_user(username="criteria-admin")
        grant_permissions(cls.admin, "manage_scoring_criteria", "view_scoringcriterion")
        cls.application = Application.objects.create(
            owner=cls.owner,
            project_title="App",
            company_no="CO",
            incorporation_date=date(2025, 1, 1),
            contact_person="P",
            telephone="1",
            business_nature="B",
            business_location="L",
            loan_amount=100,
            email="o@example.com",
        )
        Application.objects.filter(pk=cls.application.pk).update(state="evaluation")
        cls.application.refresh_from_db()
        cls.criterion = ScoringCriterion.objects.create(
            name="Financial", weight=2, max_score=10, is_required=True
        )
        from api.features.tasks.models import Task, TaskAssignment

        task = Task.objects.create(
            application=cls.application,
            task_type=Task.Type.EVALUATION,
            status=Task.Status.ASSIGNED,
        )
        TaskAssignment.objects.create(task=task, employee=cls.scorer, is_active=True)

    def test_criteria_requires_view_permission(self):
        self.client.force_login(self.owner)
        self.assertEqual(self.client.get("/api/scoring-criteria").status_code, 403)

    def test_criteria_list_with_permission(self):
        self.client.force_login(self.admin)
        response = self.client.get("/api/scoring-criteria")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 1)

    def test_create_criterion_requires_manage(self):
        self.client.force_login(self.scorer)
        response = self.client.post(
            "/api/scoring-criteria",
            data={"name": "New", "max_score": 5},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 403)

    def test_admin_can_create_criterion(self):
        self.client.force_login(self.admin)
        response = self.client.post(
            "/api/scoring-criteria",
            data={"name": "New", "max_score": 5, "weight": 1},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 201, response.content)
        self.assertEqual(response.json()["name"], "New")

    def test_admin_can_partially_update_criterion_without_renaming(self):
        self.client.force_login(self.admin)
        response = self.client.patch(
            f"/api/scoring-criteria/{self.criterion.id}",
            data={"name": self.criterion.name, "weight": 3},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.json()["name"], self.criterion.name)
        self.assertEqual(response.json()["weight"], "3")

    def test_delete_criterion_with_scores_blocked(self):
        # create a score referencing the criterion
        from api.features.scoring.models import ApplicationScore

        scoring = ApplicationScoring.objects.create(
            application=self.application, scorer=self.scorer
        )
        ApplicationScore.objects.create(
            scoring=scoring, criterion=self.criterion, score=5
        )
        self.client.force_login(self.admin)
        response = self.client.delete(f"/api/scoring-criteria/{self.criterion.id}")
        self.assertEqual(response.status_code, 400)

    def test_scoring_session_requires_score_permission(self):
        self.client.force_login(self.owner)
        response = self.client.get(f"/api/applications/{self.application.id}/scorings")
        self.assertEqual(response.status_code, 403)

    def test_scorer_can_upsert_and_submit(self):
        self.client.force_login(self.scorer)
        url = f"/api/applications/{self.application.id}/scorings/me"
        response = self.client.put(
            url,
            data={"scores": [{"criterion_id": self.criterion.id, "score": 8, "comment": "good"}]},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.json()["scores"][0]["score"], "8.00")

        # confirm
        response = self.client.post(
            f"/api/applications/{self.application.id}/scorings/me/confirm"
        )
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.json()["status"], "confirmed")

    def test_submit_missing_required_returns_400(self):
        self.client.force_login(self.scorer)
        # create an empty draft session first
        self.client.put(
            f"/api/applications/{self.application.id}/scorings/me",
            data={"scores": []},
            content_type="application/json",
        )
        response = self.client.post(
            f"/api/applications/{self.application.id}/scorings/me/confirm"
        )
        self.assertEqual(response.status_code, 400)

    def test_score_out_of_range_returns_400(self):
        self.client.force_login(self.scorer)
        url = f"/api/applications/{self.application.id}/scorings/me"
        response = self.client.put(
            url,
            data={"scores": [{"criterion_id": self.criterion.id, "score": 99, "comment": ""}]},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)

    def test_inactive_criterion_cannot_be_scored(self):
        inactive = ScoringCriterion.objects.create(
            name="Inactive", max_score=5, is_active=False
        )
        self.client.force_login(self.scorer)
        url = f"/api/applications/{self.application.id}/scorings/me"
        response = self.client.put(
            url,
            data={"scores": [{"criterion_id": inactive.id, "score": 3, "comment": ""}]},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)

    def test_adjudicator_scores_each_criterion_and_final_score_is_weighted(self):
        from api.features.tasks.models import Task, TaskAssignment

        adjudicator = get_user_model().objects.create_user(username="adjudicator")
        grant_permissions(adjudicator, "adjudicate_application")
        Task.objects.filter(application=self.application).update(
            status=Task.Status.COMPLETED
        )
        task = Task.objects.create(
            application=self.application,
            task_type=Task.Type.ADJUDICATION,
            status=Task.Status.ASSIGNED,
        )
        TaskAssignment.objects.create(
            task=task, employee=adjudicator, is_active=True
        )
        Application.objects.filter(pk=self.application.pk).update(
            state="adjudication"
        )

        self.client.force_login(adjudicator)
        response = self.client.put(
            f"/api/applications/{self.application.id}/adjudication",
            data={
                "scores": [
                    {
                        "criterion_id": self.criterion.id,
                        "score": 7,
                        "comment": "Final category decision",
                    }
                ],
                "comment": "Final adjudication",
            },
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.json()["final_score"], "14.00")
        self.assertEqual(len(response.json()["scores"]), 1)
        self.assertEqual(response.json()["scores"][0]["score"], "7.00")

    def test_duplicate_criterion_in_batch_returns_400(self):
        self.client.force_login(self.scorer)
        url = f"/api/applications/{self.application.id}/scorings/me"
        response = self.client.put(
            url,
            data={"scores": [
                {"criterion_id": self.criterion.id, "score": 5, "comment": ""},
                {"criterion_id": self.criterion.id, "score": 6, "comment": ""},
            ]},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)

    def test_multi_scorer_isolation(self):
        scorer2 = get_user_model().objects.create_user(username="scorer4")
        grant_permissions(scorer2, "score_application")
        # scorer1 submits
        self.client.force_login(self.scorer)
        self.client.put(
            f"/api/applications/{self.application.id}/scorings/me",
            data={"scores": [{"criterion_id": self.criterion.id, "score": 8, "comment": ""}]},
            content_type="application/json",
        )
        # scorer2 lists -> only own (none yet)
        self.client.force_login(scorer2)
        response = self.client.get(f"/api/applications/{self.application.id}/scorings")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 0)

    def test_view_all_scores_required_for_summary(self):
        self.client.force_login(self.owner)
        response = self.client.get(f"/api/applications/{self.application.id}/scoring-summary")
        self.assertEqual(response.status_code, 403)

    def test_summary_with_permission(self):
        self.client.force_login(self.scorer)
        self.client.put(
            f"/api/applications/{self.application.id}/scorings/me",
            data={"scores": [{"criterion_id": self.criterion.id, "score": 8, "comment": ""}]},
            content_type="application/json",
        )
        self.client.post(f"/api/applications/{self.application.id}/scorings/me/confirm")
        self.client.force_login(self.reviewer)
        response = self.client.get(f"/api/applications/{self.application.id}/scoring-summary")
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(len(response.json()["scorers"]), 1)

    def test_submitted_session_immutable_without_finalize(self):
        self.client.force_login(self.scorer)
        self.client.put(
            f"/api/applications/{self.application.id}/scorings/me",
            data={"scores": [{"criterion_id": self.criterion.id, "score": 8, "comment": ""}]},
            content_type="application/json",
        )
        self.client.post(f"/api/applications/{self.application.id}/scorings/me/confirm")
        # try edit via /me PUT
        response = self.client.put(
            f"/api/applications/{self.application.id}/scorings/me",
            data={"scores": [{"criterion_id": self.criterion.id, "score": 1, "comment": ""}]},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)

    def test_finalize_override_allowed(self):
        self.client.force_login(self.scorer)
        self.client.put(
            f"/api/applications/{self.application.id}/scorings/me",
            data={"scores": [{"criterion_id": self.criterion.id, "score": 8, "comment": ""}]},
            content_type="application/json",
        )
        self.client.post(f"/api/applications/{self.application.id}/scorings/me/confirm")
        # get scoring id
        resp = self.client.get(f"/api/applications/{self.application.id}/scorings/me")
        sid = resp.json()["id"]
        finalize_user = get_user_model().objects.create_user(username="finalizer")
        grant_permissions(finalize_user, "finalize_scoring", "view_all_scores")
        self.client.force_login(finalize_user)
        response = self.client.patch(
            f"/api/applications/{self.application.id}/scorings/{sid}",
            data={"scores": [{"criterion_id": self.criterion.id, "score": 2, "comment": "override"}]},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400, response.content)

    def test_delete_own_draft_allowed(self):
        self.client.force_login(self.scorer)
        self.client.put(
            f"/api/applications/{self.application.id}/scorings/me",
            data={"scores": [{"criterion_id": self.criterion.id, "score": 8, "comment": ""}]},
            content_type="application/json",
        )
        resp = self.client.get(f"/api/applications/{self.application.id}/scorings/me")
        sid = resp.json()["id"]
        response = self.client.delete(f"/api/applications/{self.application.id}/scorings/{sid}")
        self.assertEqual(response.status_code, 200)

    def test_delete_submitted_requires_finalize(self):
        self.client.force_login(self.scorer)
        self.client.put(
            f"/api/applications/{self.application.id}/scorings/me",
            data={"scores": [{"criterion_id": self.criterion.id, "score": 8, "comment": ""}]},
            content_type="application/json",
        )
        self.client.post(f"/api/applications/{self.application.id}/scorings/me/confirm")
        resp = self.client.get(f"/api/applications/{self.application.id}/scorings/me")
        sid = resp.json()["id"]
        response = self.client.delete(f"/api/applications/{self.application.id}/scorings/{sid}")
        self.assertEqual(response.status_code, 403)
