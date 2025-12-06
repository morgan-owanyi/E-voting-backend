from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from django.contrib.auth import get_user_model
from .models import EmailOTP

User = get_user_model()


class AccountsAPITests(APITestCase):
	def setUp(self):
		self.register_url = reverse('account-register')
		self.request_otp_url = reverse('request-otp')
		self.verify_otp_url = reverse('verify-otp')
		self.token_url = reverse('api-token-auth')
		self.user_data = {
			'username': 'testuser',
			'email': 'test@example.com',
			'password': 'strongpassword',
			'role': 'VOTER',
		}

	def test_register_creates_user(self):
		resp = self.client.post(self.register_url, self.user_data, format='json')
		self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
		user = User.objects.filter(username=self.user_data['username']).first()
		self.assertIsNotNone(user)
		self.assertNotEqual(user.password, self.user_data['password'])
		self.assertFalse(user.is_email_verified)

	def test_request_otp_creates_otp_for_existing_and_new_email(self):
		# create a user first
		User.objects.create_user(username='u1', email='exists@example.com', password='pw12345')

		resp1 = self.client.post(self.request_otp_url, {'email': 'exists@example.com'}, format='json')
		self.assertEqual(resp1.status_code, status.HTTP_201_CREATED)
		self.assertTrue(EmailOTP.objects.filter(email='exists@example.com').exists())

		# request for an email that does not yet have a user
		resp2 = self.client.post(self.request_otp_url, {'email': 'new@example.com'}, format='json')
		self.assertEqual(resp2.status_code, status.HTTP_201_CREATED)
		self.assertTrue(EmailOTP.objects.filter(email='new@example.com').exists())

	def test_verify_otp_success_and_mark_user_verified(self):
		user = User.objects.create_user(username='verifyuser', email='verify@example.com', password='pw')
		otp = EmailOTP.create_otp(email=user.email, user=user, length=4, expiry_seconds=300)

		resp = self.client.post(self.verify_otp_url, {'email': user.email, 'code': otp.code}, format='json')
		self.assertEqual(resp.status_code, status.HTTP_200_OK)
		otp.refresh_from_db()
		user.refresh_from_db()
		self.assertTrue(otp.used)
		self.assertTrue(user.is_email_verified)

	def test_verify_otp_invalid_code(self):
		User.objects.create_user(username='u2', email='u2@example.com', password='pw')
		EmailOTP.create_otp(email='u2@example.com', length=4, expiry_seconds=300)

		resp = self.client.post(self.verify_otp_url, {'email': 'u2@example.com', 'code': '9999'}, format='json')
		self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

	def test_token_auth_returns_token(self):
		User.objects.create_user(username='tokenuser', email='token@example.com', password='tokenpass')
		resp = self.client.post(self.token_url, {'username': 'tokenuser', 'password': 'tokenpass'}, format='json')
		self.assertEqual(resp.status_code, status.HTTP_200_OK)
		self.assertIn('token', resp.data)

