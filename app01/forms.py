# ============================================================
# 导入模块
# ============================================================
import hashlib
from django import forms
from django.core.validators import RegexValidator
from django.core.exceptions import ValidationError
from app01 import models
from app01.utils.bootstrap import BootStrapModelForm


# ============================================================
# 用户管理的ModelForm
# ============================================================
class UserModelForm(BootStrapModelForm):
    """新建用户ModelForm：手机号正则校验"""

    mobile = forms.CharField(
        label="手机号",
        validators=[RegexValidator(r'^1[3-9]\d{9}$', '手机号格式错误')],
    )

    class Meta:
        model = models.UserInfo
        fields = ["name", "password", "age", "account", "create_time", "mobile", "avatar", "gender", "depart"]
        widgets = {
            "create_time": forms.DateInput(attrs={"type": "text", "id": "dt"}),
        }


class UserEditModelForm(BootStrapModelForm):
    """编辑用户ModelForm"""

    mobile = forms.CharField(
        label="手机号",
        validators=[RegexValidator(r'^1[3-9]\d{9}$', '手机号格式错误')],
    )

    class Meta:
        model = models.UserInfo
        fields = ["name", "password", "age", "account", "create_time", "mobile", "avatar", "gender", "depart"]
        widgets = {
            "create_time": forms.DateInput(attrs={"type": "text", "id": "dt"}),
        }


# ============================================================
# 管理员相关表单
# ============================================================
def md5(pwd):
    """MD5加密密码，数据库不存明文"""
    obj = hashlib.md5()
    obj.update(pwd.encode("utf-8"))
    return obj.hexdigest()


# ============================================================
# 新建管理员表单：用户名 + 密码 + 确认密码
# ============================================================
class AdminModelForm(BootStrapModelForm):
    """新建管理员：用户名 + 密码 + 确认密码"""

    # 额外字段：确认密码（数据库里没有，只用于二次确认）
    confirm_password = forms.CharField(
        label="确认密码",
        widget=forms.PasswordInput,       # 输入时显示圆点
    )

    class Meta:
        model = models.Admin
        fields = ["username", "password"]
        widgets = {
            "password": forms.PasswordInput,   # 密码框也显示圆点
        }

    def clean_password(self):
        """钩子方法：密码字段校验后MD5加密"""
        pwd = self.cleaned_data["password"]
        return md5(pwd)                    # 返回加密后的密码存入数据库

    def clean(self):
        """整体校验：两次密码是否一致"""
        pwd = self.cleaned_data.get("password")            # MD5后的密码
        confirm_pwd = self.cleaned_data.get("confirm_password")  # 明文确认密码
        # 密码框本身校验失败时，不重复报不一致
        if pwd and confirm_pwd and pwd != md5(confirm_pwd):
            self.add_error("confirm_password", "两次密码不一致")
        return self.cleaned_data


# ============================================================
# 编辑管理员表单：只允许改用户名，不允许改密码
# ============================================================
class AdminEditModelForm(BootStrapModelForm):
    """编辑管理员：只允许编辑用户名"""
    class Meta:
        model = models.Admin
        fields = ["username"]              # 只显示用户名字段


# ============================================================
# 重置密码表单：新密码 + 确认密码
# ============================================================
class AdminResetPwdForm(BootStrapModelForm):
    """重置密码：新密码 + 确认密码"""

    confirm_password = forms.CharField(
        label="确认密码",
        widget=forms.PasswordInput,
    )

    class Meta:
        model = models.Admin
        fields = ["password"]
        widgets = {
            "password": forms.PasswordInput,
        }

    def clean_password(self):
        """钩子方法：校验新密码不能和原密码相同，然后MD5加密"""
        pwd = self.cleaned_data["password"]
        # self.instance = 当前正在编辑的管理员记录
        # self.instance.password = 原密码的MD5值
        if md5(pwd) == self.instance.password:
            raise ValidationError("新密码不能和原密码相同")
        return md5(pwd)

    def clean(self):
        """整体校验：两次密码是否一致"""
        pwd = self.cleaned_data.get("password")
        confirm_pwd = self.cleaned_data.get("confirm_password")
        if pwd and confirm_pwd and pwd != md5(confirm_pwd):
            self.add_error("confirm_password", "两次密码不一致")
        return self.cleaned_data


# ============================================================
# 考勤表单
# ============================================================
class AttendanceModelForm(BootStrapModelForm):
    """考勤记录表单"""
    class Meta:
        model = models.Attendance
        fields = ["employee", "date", "clock_in", "clock_out", "status"]
        widgets = {
            "date": forms.DateInput(attrs={"type": "text", "id": "dt"}),
            "clock_in": forms.TimeInput(attrs={"type": "time"}),
            "clock_out": forms.TimeInput(attrs={"type": "time"}),
        }


# ============================================================
# 薪资表单
# ============================================================
class SalaryModelForm(BootStrapModelForm):
    """薪资记录表单"""
    class Meta:
        model = models.Salary
        fields = ["employee", "month", "base", "bonus", "deduction"]


# ============================================================
# 公告表单
# ============================================================
class NoticeModelForm(BootStrapModelForm):
    """公告表单"""
    class Meta:
        model = models.Notice
        fields = ["title", "content", "is_top"]


# ============================================================
# 任务表单
# ============================================================
class TaskModelForm(BootStrapModelForm):
    """任务表单"""
    class Meta:
        model = models.Task
        fields = ["level", "title", "detail", "owner"]
