from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from appeals.models import Appeal, Status


class ReportsPermissionTest(TestCase):
    def setUp(self):
        Appeal.bootstrap_statuses()
        User = get_user_model()
        self.admin = User.objects.create_user(username='admin', password='admin123', role='admin', is_staff=True)
        self.citizen = User.objects.create_user(username='citizen', password='citizen123', role='citizen')
        self.client = Client()

    def test_citizen_cannot_access_reports(self):
        self.client.login(username='citizen', password='citizen123')
        response = self.client.get(reverse('reports:dashboard'))
        self.assertEqual(response.status_code, 302)

    def test_admin_can_access_reports(self):
        self.client.login(username='admin', password='admin123')
        response = self.client.get(reverse('reports:dashboard'))
        self.assertEqual(response.status_code, 200)


class ReportsExportTest(TestCase):
    def setUp(self):
        Appeal.bootstrap_statuses()
        User = get_user_model()
        self.user = User.objects.create_user(username='manager', password='manager123', role='manager')
        self.status = Status.objects.get(code=Appeal.STATUS_NEW)
        Appeal.objects.create(
            author=self.user, status=self.status, title='Test Appeal',
            description='Test', category='social', contact_email='test@test.com'
        )
        self.client = Client()

    def test_csv_export_generates_file(self):
        self.client.login(username='manager', password='manager123')
        response = self.client.get(reverse('reports:export_csv'))
        self.assertEqual(response.status_code, 200)
        self.assertIn('text/csv', response['Content-Type'])
        self.assertTrue(response.content.startswith(b'\xef\xbb\xbf'))
