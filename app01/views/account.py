# ============================================================
# 导入模块
# ============================================================
from django.shortcuts import render, redirect               # render渲染模板、redirect重定向
from app01 import models                                     # 导入数据库模型
import hashlib                                              # MD5加密


def md5(pwd):
    """MD5加密密码"""
    obj = hashlib.md5()
    obj.update(pwd.encode("utf-8"))
    return obj.hexdigest()


# ============================================================
# 用户登录
# URL: /login/
# ============================================================
def login(request):
    """用户登录"""
    # GET请求：返回登录页
    if request.method == "GET":
        return render(request, "login.html")

    # POST请求：取表单数据
    username = request.POST.get("username")       # 用户名
    password = request.POST.get("password")       # 明文密码
    user_code = request.POST.get("code")           # 用户输入的验证码

    # ---- 第1步：校验图片验证码 ----
    session_code = request.session.get('image_code', '')
    if user_code.upper() != session_code.upper():
        return render(request, "login.html", {"error": "验证码错误"})

    # ---- 第2步：校验用户名密码 ----
    admin_object = models.Admin.objects.filter(
        username=username,
        password=md5(password)
    ).first()
    if not admin_object:
        return render(request, "login.html", {"error": "用户名或密码错误"})

    # ---- 第3步：登录成功，写入session ----
    request.session["info"] = {
        "id": admin_object.id,
        "name": admin_object.username
    }

    # ---- 第4步：根据角色跳转不同首页 ----
    roles = [r.title for r in admin_object.roles.all()]
    if "超级管理员" in roles:
        return redirect("/depart/list/")
    elif "部门管理员" in roles:
        return redirect("/user/list/")
    else:
        # 普通员工默认进入公告页
        return redirect("/notice/list/")


# ============================================================
# 首页 - 根据角色跳转
# URL: /index/
# ============================================================
def index(request):
    """首页：根据用户角色跳转到对应的默认页面"""
    if hasattr(request, 'is_super_admin') and request.is_super_admin:
        return redirect("/depart/list/")
    elif hasattr(request, 'is_dept_admin') and request.is_dept_admin:
        return redirect("/user/list/")
    else:
        return redirect("/notice/list/")


# ============================================================
# 注销
# URL: /logout/
# ============================================================
def logout(request):
    """注销：清除session，跳回登录页"""
    request.session.clear()
    return redirect("/login/")
