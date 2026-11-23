# ============================================================
# 导入模块
# ============================================================
from django.shortcuts import render, redirect               # render渲染模板、redirect重定向
from app01 import models                                     # 导入数据库模型
from app01.forms import AdminModelForm, AdminEditModelForm, AdminResetPwdForm  # 管理员表单类
from app01.utils.pagination import Pagination                # 通用分页组件


# ============================================================
# 权限检查装饰器：只有超级管理员才能访问
# ============================================================
def super_admin_required(view_func):
    """装饰器：校验是否为超级管理员"""
    def wrapper(request, *args, **kwargs):
        if not getattr(request, 'is_super_admin', False):
            return redirect("/notice/list/")
        return view_func(request, *args, **kwargs)
    return wrapper


# ============================================================
# 管理员列表
# URL: /admin/list/
# ============================================================
@super_admin_required
def admin_list(request):
    """管理员列表页"""
    queryset = models.Admin.objects.all().prefetch_related('roles')
    page_object = Pagination(request, queryset)
    context = {
        "queryset": page_object.page_queryset,
        "page_string": page_object.html(),
    }
    return render(request, "admin_list.html", context)


# ============================================================
# 新建管理员
# URL: /admin/add/
# ============================================================
@super_admin_required
def admin_add(request):
    """新建管理员"""
    if request.method == "GET":
        form = AdminModelForm()
        return render(request, "change.html", {"form": form, "title": "新建管理员"})

    form = AdminModelForm(data=request.POST)
    if form.is_valid():
        form.save()
        return redirect("/admin/list/")
    return render(request, "change.html", {"form": form, "title": "新建管理员"})


# ============================================================
# 编辑管理员
# URL: /admin/<int:nid>/edit/
# ============================================================
@super_admin_required
def admin_edit(request, nid):
    """编辑管理员 - 只能编辑普通账号，不能修改其他超级管理员"""
    row_object = models.Admin.objects.filter(id=nid).first()
    if not row_object:
        return redirect("/admin/list/")

    # 不能编辑自己的账号（避免误操作）
    if row_object.id == request.admin_object.id:
        return redirect("/admin/list/")

    # 不能编辑其他超级管理员
    row_roles = [r.title for r in row_object.roles.all()]
    if "超级管理员" in row_roles:
        return redirect("/admin/list/")

    if request.method == "GET":
        form = AdminEditModelForm(instance=row_object)
        return render(request, "change.html", {"form": form, "title": "编辑管理员"})

    form = AdminEditModelForm(data=request.POST, instance=row_object)
    if form.is_valid():
        form.save()
        return redirect("/admin/list/")
    return render(request, "change.html", {"form": form, "title": "编辑管理员"})


# ============================================================
# 删除管理员
# URL: /admin/<int:nid>/delete/
# ============================================================
@super_admin_required
def admin_delete(request, nid):
    """删除管理员 - 不能删除超级管理员账号"""
    row_object = models.Admin.objects.filter(id=nid).first()
    if not row_object:
        return redirect("/admin/list/")

    # 不能删除自己
    if row_object.id == request.admin_object.id:
        return redirect("/admin/list/")

    # 不能删除其他超级管理员
    row_roles = [r.title for r in row_object.roles.all()]
    if "超级管理员" in row_roles:
        return redirect("/admin/list/")

    models.Admin.objects.filter(id=nid).delete()
    return redirect("/admin/list/")


# ============================================================
# 重置密码
# URL: /admin/<int:nid>/reset/pwd/
# ============================================================
@super_admin_required
def admin_reset_pwd(request, nid):
    """重置管理员密码 - 不能重置超级管理员密码"""
    row_object = models.Admin.objects.filter(id=nid).first()
    if not row_object:
        return redirect("/admin/list/")

    # 不能重置自己的密码
    if row_object.id == request.admin_object.id:
        return redirect("/admin/list/")

    # 不能重置其他超级管理员的密码
    row_roles = [r.title for r in row_object.roles.all()]
    if "超级管理员" in row_roles:
        return redirect("/admin/list/")

    if request.method == "GET":
        form = AdminResetPwdForm(instance=row_object)
        return render(request, "change.html", {"form": form, "title": f"重置密码 - {row_object.username}"})

    form = AdminResetPwdForm(data=request.POST, instance=row_object)
    if form.is_valid():
        row_object.password = form.cleaned_data["password"]
        row_object.save()
        return redirect("/admin/list/")
    return render(request, "change.html", {"form": form, "title": f"重置密码 - {row_object.username}"})
