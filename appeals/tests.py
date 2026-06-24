from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from .models import Appeal, Status, AuditLog


class AppealWorkflowTest(TestCase):
    def setUp(self):
        Appeal.bootstrap_statuses()
        self.User = get_user_model()
        self.citizen = self.User.objects.create_user(username='citizen', password='testpass123', role='citizen')
        self.executor = self.User.objects.create_user(username='executor', password='testpass123', role='executor')
        self.operator = self.User.objects.create_user(username='operator', password='testpass123', role='operator')
        self.client = Client()
        self.status_new = Status.objects.get(code=Appeal.STATUS_NEW)
        self.status_in_progress = Status.objects.get(code=Appeal.STATUS_IN_PROGRESS)
        self.status_on_review = Status.objects.get(code=Appeal.STATUS_ON_REVIEW)
        self.status_approved = Status.objects.get(code=Appeal.STATUS_APPROVED)
        self.status_closed = Status.objects.get(code=Appeal.STATUS_CLOSED)

    def test_reg_number_generation(self):
        appeal = Appeal.objects.create(author=self.citizen, title='Test', description='Test desc', contact_email='test@test.com')
        self.assertEqual(appeal.status, self.status_new)
        self.assertTrue(appeal.reg_number.startswith('ER-'))
        self.assertEqual(len(appeal.reg_number.split('-')[2]), 4)

    def test_allowed_transition_codes_for_executor(self):
        appeal = Appeal.objects.create(
            author=self.citizen,
            executor=self.executor,
            status=self.status_new,
            title='Test',
            description='Test desc',
            contact_email='test2@test.com'
        )
        self.assertEqual(appeal.get_allowed_transition_codes(self.executor), [Appeal.STATUS_IN_PROGRESS, Appeal.STATUS_REJECTED])

    def test_transition_assigns_executor_and_logs_audit(self):
        appeal = Appeal.objects.create(
            author=self.citizen,
            status=self.status_new,
            title='Test',
            description='Test desc',
            contact_email='test3@test.com'
        )
        old_status, new_status = appeal.transition_to(self.status_in_progress, actor=self.executor, comment='Берём в работу')
        appeal.refresh_from_db()
        self.assertEqual(old_status.code, Appeal.STATUS_NEW)
        self.assertEqual(new_status.code, Appeal.STATUS_IN_PROGRESS)
        self.assertEqual(appeal.executor, self.executor)
        self.assertIsNone(appeal.closed_at)
        self.assertTrue(AuditLog.objects.filter(target_id=appeal.id, action='STATUS_CHANGE').exists())

    def test_transition_to_closed_sets_closed_at(self):
        appeal = Appeal.objects.create(
            author=self.citizen,
            executor=self.executor,
            status=self.status_approved,
            title='Test',
            description='Test desc',
            contact_email='test4@test.com'
        )
        appeal.transition_to(self.status_closed, actor=self.executor, comment='Закрыто')
        appeal.refresh_from_db()
        self.assertEqual(appeal.status.code, Appeal.STATUS_CLOSED)
        self.assertIsNotNone(appeal.closed_at)

    def test_create_appeal_view_redirects(self):
        self.client.login(username='citizen', password='testpass123')
        response = self.client.post(reverse('appeals:create'), {
            'title': 'Новое обращение', 'description': 'Тест', 'category': 'other',
            'contact_email': 'test5@test.com', 'contact_phone': '+79991234567'
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Appeal.objects.filter(title='Новое обращение').exists())

    def test_ajax_status_update_returns_json(self):
        appeal = Appeal.objects.create(
            author=self.citizen,
            executor=self.executor,
            status=self.status_new,
            title='Test',
            description='Test desc',
            contact_email='test6@test.com'
        )
        self.client.login(username='executor', password='testpass123')
        response = self.client.post(
            reverse('appeals:update_status', kwargs={'pk': appeal.pk}),
            {'new_status': self.status_in_progress.pk, 'comment': 'ok'},
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
            HTTP_HOST='127.0.0.1'
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['success'], True)
        self.assertEqual(response.json()['status'], Appeal.STATUS_IN_PROGRESS)

    def test_unauthorized_access_blocked(self):
        response = self.client.get(reverse('appeals:list'))
        self.assertEqual(response.status_code, 302)
        self.assertIn('/login/', response.url)
