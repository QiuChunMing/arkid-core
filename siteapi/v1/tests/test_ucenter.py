'''
tests for api about ucenter
'''
# pylint: disable=missing-docstring

from unittest import mock

from django.urls import reverse
from common.django.drf.client import APIClient

from siteapi.v1.tests import TestCase
from oneid_meta.models import (
    User,
    UserPerm,
    DingUser,
    CustomField,
    AccountConfig,
    EmailConfig,
    SMSConfig,
)
from executer.utils.password import verify_password

MAX_APP_ID = 2

VISIABLE_FIELDS = ['name', 'email', 'depts', 'mobile', 'employee_number', 'gender']


class UCenterTestCase(TestCase):
    def setUp(self):
        super().setUp()
        account_config = AccountConfig.get_current()
        account_config.allow_email = True
        account_config.allow_mobile = True
        account_config.allow_register = True
        account_config.save()

        email_config = EmailConfig.get_current()
        email_config.is_valid = True
        email_config.save()

        mobile_config = SMSConfig.get_current()
        mobile_config.is_valid = True
        mobile_config.save()

    @mock.patch('siteapi.v1.serializers.ucenter.ResetPWDSMSClaimSerializer.check_sms_token')
    def test_reset_user_password_by_sms(self, mock_check_sms_code):
        self.user.mobile = 'mobile'
        self.user.save()
        mock_check_sms_code.side_effect = [{'mobile': 'wrong_mobile'}, {'mobile': 'mobile'}]

        data = {'new_password': 'new_password', 'mobile': 'mobile', 'sms_token': 'any'}
        res = self.client.put(reverse('siteapi:set_user_password'), data=data)
        self.assertEqual(res.status_code, 400)
        self.assertEqual(res.json(), {'mobile': ['invalid']})

        data = {'new_password': 'new_password', 'mobile': 'mobile', 'sms_token': 'any'}
        res = self.client.put(reverse('siteapi:set_user_password'), data=data)
        self.assertEqual(res.status_code, 200)

        ciphertext = User.valid_objects.get(username=self.user.username).password
        self.assertTrue(verify_password('new_password', ciphertext))

    def test_reset_user_password_by_op(self):
        data = {'new_password': 'new_password', 'username': 'admin', 'old_password': 'admin'}
        res = self.client.put(reverse('siteapi:set_user_password'), data=data)
        self.assertEqual(res.status_code, 200)
        ciphertext = User.valid_objects.get(username=self.user.username).password
        self.assertTrue(verify_password('new_password', ciphertext))

    @mock.patch('siteapi.v1.serializers.ucenter.ResetPWDEmailClaimSerializer.check_email_token')
    def test_reset_user_password_by_email(self, mock_check_email_code):
        self.user.private_email = 'email'
        self.user.save()
        mock_check_email_code.side_effect = [{'email': 'wrong_email'}, {'email': 'email'}]

        data = {'new_password': 'new_password', 'email': 'email', 'email_token': 'mock'}
        res = self.client.put(reverse('siteapi:set_user_password'), data=data)
        self.assertEqual(res.status_code, 400)
        self.assertEqual(res.json(), {'email': ['invalid']})

    @mock.patch('siteapi.v1.serializers.ucenter.RegisterSMSClaimSerializer.check_sms_token')
    def test_register_by_mobile(self, mock_check_sms_token):
        mock_check_sms_token.side_effect = [{'mobile': '18812341234'}]
        data = {
            'username': 'testregister',
            'password': 'pwd',
            'sms_token': 'mock',
        }
        res = self.client.json_post(reverse('siteapi:user_register'), data=data)
        self.assertEqual(res.status_code, 201)
        self.assertIn('token', res.json())
        user = User.objects.filter(username='testregister').first()
        self.assertIsNotNone(user)
        self.assertTrue(user.check_password('pwd'))
        self.assertEqual(user.origin, 3)    # 手机注册

        res = self.client.json_post(reverse('siteapi:user_register'), data=data)
        self.assertEqual(res.status_code, 400)

    @mock.patch('siteapi.v1.serializers.ucenter.RegisterEmailClaimSerializer.check_email_token')
    def test_register_by_email(self, mock_check_email_token):
        mock_check_email_token.side_effect = [{'email': 'a@b.com'}]
        data = {
            'username': 'testregister',
            'password': 'pwd',
            'email_token': 'mockd',
        }
        res = self.client.json_post(reverse('siteapi:user_register'), data=data)
        self.assertEqual(res.status_code, 201)
        self.assertIn('token', res.json())
        user = User.objects.filter(username='testregister').first()
        self.assertIsNotNone(user)
        self.assertTrue(user.check_password('pwd'))
        self.assertEqual(user.origin, 4)    # 邮箱注册

        res = self.client.json_post(reverse('siteapi:user_register'), data=data)
        self.assertEqual(res.status_code, 400)

    @mock.patch('siteapi.v1.serializers.ucenter.UpdateMobileSMSClaimSerializer.check_sms_token')
    @mock.patch('siteapi.v1.serializers.ucenter.UpdateEmailEmailClaimSerializer.check_email_token')
    def test_update_contact(self, mock_check_email_token, mock_check_sms_token):
        mock_check_email_token.side_effect = [{'email': 'c@d.com', 'name': '', 'username': 'admin'}]
        mock_check_sms_token.side_effect = [{'mobile': '18812341004'}]

        res = self.client.json_patch(reverse('siteapi:update_user_contact'), data={'email_token': 'mock'})
        self.assertEqual(res.status_code, 200)
        self.assertEqual(User.objects.get(username='admin').private_email, 'c@d.com')

        res = self.client.json_patch(reverse('siteapi:update_user_contact'), data={'sms_token': 'mock'})
        self.assertEqual(res.status_code, 200)
        self.assertEqual(User.objects.get(username='admin').mobile, '18812341004')

    def test_token_perm_auth(self):
        res = self.client.get(reverse('siteapi:token_perm_auth'), data={'perm_uid': 'system_oneid_all'}).json()
        self.assertIsNotNone(res.pop('uuid', None))
        expect = {
            'user_id': 1,
            'username': 'admin',
            'private_email': '',
            'position': '',
            'name': '',
            'email': '',
            'mobile': '',
            'employee_number': '',
            'gender': 0,
            'perms': ['system_oneid_all', 'system_ark-meta-server_all'],
            'roles': ['admin'],
            'avatar': '',
            'is_admin': True,
            'is_manager': False,
            'is_settled': True,
            'origin_verbose': '脚本添加',
        }
        self.assertEqual(res, expect)

        res = self.client.get(reverse('siteapi:token_perm_auth'))
        self.assertEqual(res.status_code, 200)

        from oneid_meta.models import ManagerGroup, Group, GroupMember
        group = Group.objects.create(name='group')
        ManagerGroup.objects.create(group=group)
        GroupMember.objects.create(user=self.user, owner=group)
        res = self.client.get(reverse('siteapi:token_perm_auth'), data={'perm_uid': 'system_oneid_all'})
        self.assertEqual(res.json()['roles'], ['admin', 'manager'])

        # TODO
        # res = self.client.get(reverse('siteapi:token_perm_auth'), data={'perm_uid': 'system_none_all'})
        # self.assertEqual(res.status_code, 403)

        user_perm = UserPerm.valid_objects.get(owner=self.user, perm__uid='system_oneid_all')
        user_perm.value = False
        user_perm.save()
        res = self.client.get(reverse('siteapi:token_perm_auth'), data={'perm_uid': 'system_oneid_all'})
        self.assertEqual(res.status_code, 403)

    def test_login(self):
        user = User.create_user(username='test', password='test')
        user.mobile = '18812341234'
        user.private_email = '12@34.com'
        user.save()
        client = APIClient()

        res = client.get(reverse('siteapi:user_self_perm'))
        self.assertEqual(res.status_code, 401)

        res = client.post(reverse('siteapi:user_login'), data={'username': 'test', 'password': 'test'})
        self.assertEqual(res.status_code, 200)
        res = client.post(reverse('siteapi:user_login'), data={'private_email': '12@34.com', 'password': 'test'})
        self.assertEqual(res.status_code, 200)
        res = client.post(reverse('siteapi:user_login'), data={'mobile': '18812341234', 'password': 'test'})
        self.assertEqual(res.status_code, 200)

        client.credentials(HTTP_AUTHORIZATION='Token ' + res.json()['token'])
        res = client.get(reverse('siteapi:user_self_perm'))
        self.assertEqual(res.status_code, 200)

        res = client.post(reverse('siteapi:user_login'), data={'username': 'admin', 'password': 'admin'})
        self.assertEqual(res.json()['perms'], ['system_oneid_all', 'system_ark-meta-server_all'])

        # test login failed because of account_config
        email_config = EmailConfig.get_current()
        email_config.is_valid = False
        email_config.save()
        res = client.post(reverse('siteapi:user_login'), data={'private_email': '12@34.com', 'password': 'test'})
        self.assertEqual(res.status_code, 400)

        mobile_config = SMSConfig.get_current()
        mobile_config.is_valid = True
        mobile_config.save()
        res = client.post(reverse('siteapi:user_login'), data={'mobile': '18812341234', 'password': 'test'})
        self.assertEqual(res.status_code, 200)

    @mock.patch('siteapi.v1.views.ucenter.DingLoginAPIView.auth_code')
    def test_ding_login(self, mock_auth_code):
        mock_auth_code.return_value = "ding_uid"
        client = APIClient()
        res = client.post(reverse('siteapi:ding_login'), data={'code': 'ding_code'})
        expect = {'code': ["this account hasn't registered"]}
        self.assertEqual(res.json(), expect)
        self.assertEqual(res.status_code, 400)

        user = User.create_user(username='user', password='')
        DingUser.valid_objects.create(user=user, uid='ding_uid')
        res = client.post(reverse('siteapi:ding_login'), data={'code': 'ding_code'})
        self.assertEqual(res.status_code, 200)
        self.assertIn('token', res.json())

    def test_update_self(self):
        res = self.client.get(reverse("siteapi:ucenter_profile"))
        expect = {
            'username': 'admin',
            'name': '',
            'email': '',
            'mobile': '',
            'employee_number': '',
            'private_email': '',
            'position': '',
            'gender': 0,
            'avatar': '',
            'visible_fields': VISIABLE_FIELDS,
            'depts': [],
        }
        self.assertEqual(res.json(), expect)

        res = self.client.json_patch(reverse("siteapi:ucenter_profile"), data={'avatar': 'avatar_key'})
        expect = {
            'username': 'admin',
            'name': '',
            'email': '',
            'mobile': '',
            'gender': 0,
            'employee_number': '',
            'private_email': '',
            'position': '',
            'avatar': 'avatar_key',
            'visible_fields': VISIABLE_FIELDS,
            'depts': [],
        }
        self.assertEqual(res.json(), expect)

    @mock.patch("infrastructure.serializers.sms.SMSClaimSerializer.check_sms_token")
    def test_update_self_mobile(self, mock_check_sms_token):
        mock_check_sms_token.side_effect = [
            {
                'mobile': 'mobile_1'
            },
            {
                'mobile': 'mobile_2'
            },
            {
                'mobile': 'mobile_1'
            },
            {
                'mobile': 'mobile_3'
            },
        ]

        employee_1 = User.create_user('employee_1', 'employee_1')
        employee_1.mobile = 'mobile_1'
        employee_1.save()
        client_1 = self.login('employee_1', 'employee_1')

        employee_2 = User.create_user('employee_2', 'employee_2')
        employee_2.mobile = 'mobile_2'
        employee_2.save()

        res = client_1.json_patch(reverse('siteapi:ucenter_mobile'),
                                  data={
                                      'old_mobile_sms_token': 'any',
                                      'new_mobile_sms_token': 'any'
                                  })
        self.assertEqual(res.json(), {'new_mobile': ['has been used']})

        res = client_1.json_patch(reverse('siteapi:ucenter_mobile'),
                                  data={
                                      'old_mobile_sms_token': 'any',
                                      'new_mobile_sms_token': 'any'
                                  })
        expect = {'new_mobile': 'mobile_3'}
        self.assertEqual(res.json(), expect)


class UcenterCustomProfileTestCase(TestCase):
    def test_custom_profile(self):
        cf = CustomField.valid_objects.create(name='忌口')    # pylint:disable=invalid-name
        res = self.client.json_patch(reverse('siteapi:ucenter_profile'),
                                     data={'custom_user': {
                                         'data': {
                                             cf.uuid.hex: '无'
                                         }
                                     }})
        expect = {
            'data': {
                cf.uuid.hex: '无'
            },
            'pretty': [{
                'uuid': cf.uuid.hex,
                'name': '忌口',
                'value': '无',
            }]
        }
        self.assertEqual(res.json()['custom_user'], expect)

        res = self.client.get(reverse('siteapi:ucenter_profile'))
        self.assertEqual(res.json()['custom_user'], expect)

        cf.is_visible = False
        cf.save()
        # 不展示
        # 保留数据，不提供渲染结果
        res = self.client.get(reverse('siteapi:ucenter_profile'))
        expect = {'data': {cf.uuid.hex: '无'}, 'pretty': []}
        self.assertEqual(expect, res.json()['custom_user'])

        cf.delete()
        # 删除
        # 保留数据，不提供渲染结果
        expect = {'data': {cf.uuid.hex: '无'}, 'pretty': []}
        res = self.client.get(reverse('siteapi:ucenter_profile'))
        self.assertEqual(expect, res.json()['custom_user'])
