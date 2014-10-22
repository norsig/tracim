# -*- coding: utf-8 -*-

from tracim import model  as pm

from sprox.tablebase import TableBase
from sprox.formbase import EditableForm, AddRecordForm
from sprox.fillerbase import TableFiller, EditFormFiller
from tw2 import forms as tw2f
import tg
from tg import predicates
from tg import tmpl_context
from tg.i18n import ugettext as _, lazy_ugettext as l_

from sprox.widgets import PropertyMultipleSelectField
from sprox._compat import unicode_text

from formencode import Schema
from formencode.validators import FieldsMatch

from tracim.controllers import TIMRestController
from tracim.lib import CST
from tracim.lib import helpers as h
from tracim.lib.user import UserApi
from tracim.lib.group import GroupApi
from tracim.lib.user import UserStaticApi
from tracim.lib.userworkspace import RoleApi
from tracim.lib.workspace import WorkspaceApi

from tracim.model import DBSession
from tracim.model.auth import Group, User
from tracim.model.serializers import Context, CTX, DictLikeClass

class UserProfileAdminRestController(TIMRestController):
    """
     CRUD Controller allowing to manage groups of a user
    """
    allow_only = predicates.in_any_group(Group.TIM_ADMIN_GROUPNAME)

    allowed_profiles = ['tracim-user', 'tracim-manager', 'tracim-admin']

    def _before(self, *args, **kw):
        """
        Instantiate the current workspace in tg.tmpl_context
        :param args:
        :param kw:
        :return:
        """
        super(self.__class__, self)._before(args, kw)

        api = UserApi(tg.tmpl_context.current_user)
        user_id = tg.request.controller_state.routing_args.get('user_id')
        user = api.get_one(user_id)
        tg.tmpl_context.user_id = user_id
        tg.tmpl_context.user = user

    @tg.expose()
    def switch(self, new_role):
        """
        :param new_role: value should be 'tracim-user', 'tracim-manager' (allowed to create workspaces) or 'tracim-admin' (admin the whole system)
        :return:
        """
        return self.put(new_role)

    @tg.expose()
    def put(self, new_profile):
        # FIXME - Allow only self password or operation for managers
        current_user = tmpl_context.current_user
        user = tmpl_context.user

        group_api = GroupApi(current_user)

        if current_user.user_id==user.user_id:
            tg.flash(_('You can\'t change your own profile'), CST.STATUS_ERROR)
            tg.redirect(self.parent_controller.url())


        redirect_url = self.parent_controller.url(skip_id=True)

        if new_profile not in self.allowed_profiles:
            tg.flash(_('Unknown profile'), CST.STATUS_ERROR)
            tg.redirect(redirect_url)

        pod_user_group = group_api.get_one(Group.TIM_USER)
        pod_manager_group = group_api.get_one(Group.TIM_MANAGER)
        pod_admin_group = group_api.get_one(Group.TIM_ADMIN)

        flash_message = _('User updated.') # this is the default value ; should never appear

        if new_profile=='tracim-user':
            if pod_user_group not in user.groups:
                user.groups.append(pod_user_group)

            try:
                user.groups.remove(pod_manager_group)
            except:
                pass

            try:
                user.groups.remove(pod_admin_group)
            except:
                pass

            flash_message = _('User {} is now a basic user').format(user.get_display_name())

        elif new_profile=='tracim-manager':
            if pod_user_group not in user.groups:
                user.groups.append(pod_user_group)
            if pod_manager_group not in user.groups:
                user.groups.append(pod_manager_group)

            try:
                user.groups.remove(pod_admin_group)
            except:
                pass

            flash_message = _('User {} can now workspaces').format(user.get_display_name())


        elif new_profile=='tracim-admin':
            if pod_user_group not in user.groups:
                user.groups.append(pod_user_group)
            if pod_manager_group not in user.groups:
                user.groups.append(pod_manager_group)
            if pod_admin_group not in user.groups:
                user.groups.append(pod_admin_group)

            flash_message = _('User {} is now an administrator').format(user.get_display_name())

        DBSession.flush()

        tg.flash(flash_message, CST.STATUS_OK)
        tg.redirect(redirect_url)

    def get_edit(self):
        pass

    def get_all(self):
        pass

    def post(self):
        pass



class UserPasswordAdminRestController(TIMRestController):
    """
     CRUD Controller allowing to manage password of a given user
    """

    allow_only = predicates.in_any_group(Group.TIM_MANAGER_GROUPNAME, Group.TIM_ADMIN_GROUPNAME)

    def _before(self, *args, **kw):
        """
        Instantiate the current workspace in tg.tmpl_context
        :param args:
        :param kw:
        :return:
        """
        super(self.__class__, self)._before(args, kw)

        api = UserApi(tg.tmpl_context.current_user)
        user_id = tg.request.controller_state.routing_args.get('user_id')
        user = api.get_one(user_id)
        tg.tmpl_context.user_id = user_id
        tg.tmpl_context.user = user


    @tg.expose('tracim.templates.user_password_edit')
    def edit(self):
        current_user = tmpl_context.current_user
        api = UserApi(current_user)
        dictified_user = Context(CTX.USER).toDict(tmpl_context.user, 'user')
        return DictLikeClass(result = dictified_user)

    @tg.expose()
    def put(self, current_password, new_password1, new_password2):
        # FIXME - Manage
        current_user = tmpl_context.current_user
        user = tmpl_context.user

        redirect_url = tg.lurl('/admin/users/{}'.format(user.user_id))
        if current_user.user_id==user.user_id:
            redirect_url = tg.lurl('/admin/users/me')

        if not current_password or not new_password1 or not new_password2:
            tg.flash(_('Empty password is not allowed.'), CST.STATUS_ERROR)
            tg.redirect(redirect_url)

        if user.validate_password(current_password) is False:
            tg.flash(_('The current password you typed is wrong'))
            tg.redirect(redirect_url)

        if new_password1!=new_password2:
            tg.flash(_('New passwords do not match.'), CST.STATUS_ERROR)
            tg.redirect(redirect_url)

        user.password = new_password1
        pm.DBSession.flush()

        tg.flash(_('Your password has been changed'), CST.STATUS_OK)
        tg.redirect(redirect_url)


class UserRestController(TIMRestController):
    """
     CRUD Controller allowing to manage Users
    """
    allow_only = predicates.in_any_group(Group.TIM_MANAGER_GROUPNAME, Group.TIM_ADMIN_GROUPNAME)

    password = UserPasswordAdminRestController()
    profile = UserProfileAdminRestController()

    @classmethod
    def current_item_id_key_in_context(cls):
        return 'user_id'


    @tg.require(predicates.in_group(Group.TIM_MANAGER_GROUPNAME))
    @tg.expose('tracim.templates.user_get_all')
    def get_all(self, *args, **kw):
        current_user = tmpl_context.current_user
        api = UserApi(current_user)

        users = api.get_all()

        current_user_content = Context(CTX.CURRENT_USER).toDict(current_user)
        fake_api = Context(CTX.USERS).toDict({'current_user': current_user_content})

        dictified_users = Context(CTX.USERS).toDict(users, 'users', 'user_nb')
        return DictLikeClass(result = dictified_users, fake_api=fake_api)

    @tg.require(predicates.in_group(Group.TIM_MANAGER_GROUPNAME))
    @tg.expose()
    def post(self, name, email, password, is_pod_manager='off', is_pod_admin='off'):
        is_pod_manager = h.on_off_to_boolean(is_pod_manager)
        is_pod_admin = h.on_off_to_boolean(is_pod_admin)
        current_user = tmpl_context.current_user
        current_user = User()
        if current_user.profile.id < Group.TIM_ADMIN:
            # A manager can't give large rights
            is_pod_manager = False
            is_pod_admin = False


        api = UserApi(current_user)

        if api.user_with_email_exists(email):
            tg.flash(_('A user with email address "{}" already exists.').format(email), CST.STATUS_ERROR)
            tg.redirect(self.url())

        user = api.create_user()
        user.email_address = email
        user.display_name = name
        if password:
            user.password = password
        api.save(user)

        # Now add the user to related groups
        group_api = GroupApi(current_user)
        user.groups.append(group_api.get_one(Group.TIM_USER))
        if is_pod_manager:
            user.groups.append(group_api.get_one(Group.TIM_MANAGER))
            if is_pod_admin:
                user.groups.append(group_api.get_one(Group.TIM_ADMIN))

        api.save(user)

        tg.flash(_('User {} created.').format(user.get_display_name()), CST.STATUS_OK)
        tg.redirect(self.url())


    @tg.expose('tracim.templates.user_get_one')
    def get_one(self, user_id):
        current_user = tmpl_context.current_user
        api = UserApi(current_user )
        # role_api = RoleApi(tg.tmpl_context.current_user)
        # user_api = UserApi(tg.tmpl_context.current_user)

        user = api.get_one(user_id) # FIXME

        dictified_user = Context(CTX.USER).toDict(user, 'user')
        current_user_content = Context(CTX.CURRENT_USER).toDict(tmpl_context.current_user)
        fake_api_content = DictLikeClass(current_user=current_user_content)
        fake_api = Context(CTX.WORKSPACE).toDict(fake_api_content)

        return DictLikeClass(result = dictified_user, fake_api=fake_api)


    @tg.expose('tracim.templates.user_edit')
    def edit(self, id):
        current_user = tmpl_context.current_user
        api = UserApi(current_user)

        user = api.get_one(id)

        dictified_user = Context(CTX.USER).toDict(user, 'user')
        return DictLikeClass(result = dictified_user)

    @tg.require(predicates.in_group(Group.TIM_MANAGER_GROUPNAME))
    @tg.expose('tracim.templates.workspace_edit')
    def put(self, user_id, name, email):
        api = UserApi(tmpl_context.current_user)

        user = api.get_one(int(user_id))
        api.update(user, name, email, True)

        tg.flash(_('User {} updated.').format(user.get_display_name()), CST.STATUS_OK)
        tg.redirect(self.url())
        return

    @tg.require(predicates.in_group(Group.TIM_ADMIN_GROUPNAME))
    @tg.expose()
    def enable(self, id):
        current_user = tmpl_context.current_user
        api = UserApi(current_user)

        user = api.get_one(id)
        user.is_active = True
        api.save(user)

        tg.flash(_('User {} activated.').format(user.get_display_name()), CST.STATUS_OK)
        tg.redirect(self.url())

    @tg.require(predicates.in_group(Group.TIM_ADMIN_GROUPNAME))
    @tg.expose()
    def disable(self, id):
        id = int(id)
        current_user = tmpl_context.current_user
        api = UserApi(current_user)

        if current_user.user_id==id:
            tg.flash(_('You can\'t de-activate your own account'), CST.STATUS_ERROR)
        else:
            user = api.get_one(id)
            user.is_active = False
            api.save(user)
            tg.flash(_('User {} desactivated').format(user.get_display_name()), CST.STATUS_OK)

        tg.redirect(self.url())


    @tg.require(predicates.in_group(Group.TIM_USER_GROUPNAME))
    @tg.expose('tracim.templates.user_profile')
    def me(self):
        current_user = tmpl_context.current_user

        current_user_content = Context(CTX.CURRENT_USER).toDict(current_user)
        fake_api = Context(CTX.ADMIN_WORKSPACE).toDict({'current_user': current_user_content})

        return DictLikeClass(fake_api=fake_api)