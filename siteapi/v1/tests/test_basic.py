'''
tests for models
'''
# pylint: disable=missing-docstring

from django import db
from rest_framework.exceptions import ValidationError
from oneid_meta.models import (
    User,
    Group,
    GroupMember,
    Dept,
    DeptMember,
    Perm,
)

from siteapi.v1.tests import TestCase


class ModelTestCase(TestCase):
    def test_group_union_unique(self):
        user = User.create_user('user', 'user')
        group = Group.valid_objects.create(uid='group')

        GroupMember.valid_objects.create(owner=group, user=user)

        with self.assertRaises(db.utils.IntegrityError):
            GroupMember.valid_objects.create(owner=group, user=user)

    def test_dept_union_unique(self):
        user = User.create_user('user', 'user')
        dept = Dept.valid_objects.create(uid='dept')

        DeptMember.valid_objects.create(owner=dept, user=user)

        with self.assertRaises(db.utils.IntegrityError):
            DeptMember.valid_objects.create(owner=dept, user=user)

    def test_valid_username_unique(self):
        user = User.create_user('user', 'user')
        with self.assertRaises(ValidationError):
            User.create_user('user', 'user')
        user.name = 'name'
        user.save()
        user.delete()
        User.create_user('user', 'user')

    def test_valid_group_uid_unique(self):
        group = Group.valid_objects.create(uid='group')
        with self.assertRaises(db.utils.IntegrityError):
            group = Group.valid_objects.create(uid='group')

        group.name = 'name'
        group.save()

        group.delete()
        Group.valid_objects.create(uid='group')

        self.assertEqual(Group.objects.filter(uid='group').count(), 2)

    def test_trigger_perm_unique(self):
        Perm.valid_objects.create(uid='perm')
        with self.assertRaises(db.utils.IntegrityError):
            Perm.valid_objects.create(uid='perm')

    def test_miss_perm_unique(self):    # pylint: disable=no-self-use
        perm = Perm.valid_objects.create(uid='perm')
        perm.kill()
        Perm.valid_objects.create(uid='perm')
