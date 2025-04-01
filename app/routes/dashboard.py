# app/routes/dashboard.py
from flask import session, flash, redirect, url_for

class DashboardService:
    @staticmethod
    def get_user_info():
        user_photo = session.get('user_photo', 'default.jpg')
        return {'name': session.get('user_name'), 'photo': user_photo}

    @staticmethod
    def is_admin():
        return session.get('user_role') == 'admin'

    @staticmethod
    def is_cliente():
        return session.get('user_role') == 'cliente'

    @staticmethod
    def is_motorizado():
        return session.get('user_role') == 'motorizado'