# ============================================================
# 导入模块
# ============================================================
import json
from django.shortcuts import render, HttpResponse, redirect
from django.views.decorators.csrf import csrf_exempt
from app01 import models
from app01.forms import TaskModelForm
from app01.utils.pagination import Pagination


# ============================================================
# 任务列表页面
# URL: /task/list/
# ============================================================
def task_list(request):
    """任务列表页 - 按权限过滤"""
    # order_by('-id')：按主键倒序，最新创建的任务排在最前
    queryset = models.Task.objects.select_related('owner__depart').all().order_by('-id')

    # 普通员工：只看自己负责的任务
    if hasattr(request, 'is_employee') and request.is_employee:
        queryset = queryset.filter(owner=request.admin_object.employee)

    # 部门管理员：只看本部门员工的任务
    elif hasattr(request, 'is_dept_admin') and request.is_dept_admin:
        queryset = queryset.filter(owner__depart=request.admin_object.depart)

    # 超级管理员：看全部任务

    # 分页：QuerySet 切片自动翻译成 SQL 的 LIMIT/OFFSET，只取当前页数据
    page_object = Pagination(request, queryset)

    context = {
        "queryset": page_object.page_queryset,  # 分完页的数据
        "page_string": page_object.html(),      # 生成页码 HTML
        "owner_list": models.UserInfo.objects.select_related('depart').all(),
    }
    return render(request, "task_list.html", context)


# ============================================================
# 任务AJAX接口
# URL: /task/ajax/
# ============================================================
@csrf_exempt
def task_ajax(request):
    """处理任务AJAX提交，返回JSON"""
    if request.method == "GET":
        data_dict = {"status": True, 'data': [11, 22, 33, 44]}
        return HttpResponse(json.dumps(data_dict))

    # POST：提交任务
    form = TaskModelForm(data=request.POST)
    if form.is_valid():
        form.save()
        return HttpResponse(json.dumps({"status": True, "msg": "任务添加成功"}))
    else:
        return HttpResponse(json.dumps({"status": False, "msg": form.errors}))


# ============================================================
# 员工完成任务
# URL: /task/<int:nid>/complete/
# ============================================================
def task_complete(request, nid):
    """员工点击完成任务"""
    task_obj = models.Task.objects.filter(id=nid).first()
    if not task_obj:
        return redirect("/task/list/")

    # 只能完成自己的任务
    if request.is_employee:
        if task_obj.owner != request.admin_object.employee:
            return redirect("/task/list/")

    # 状态从"待完成"或"已退回" → "待审批"
    if task_obj.status in [1, 4]:
        task_obj.status = 2  # 待审批
        task_obj.save()

    return redirect("/task/list/")


# ============================================================
# 部门负责人审批任务
# URL: /task/<int:nid>/approve/
# ============================================================
def task_approve(request, nid):
    """部门负责人审批任务：通过或退回"""
    task_obj = models.Task.objects.filter(id=nid).first()
    if not task_obj:
        return redirect("/task/list/")

    action = request.GET.get('action', 'approve')  # approve=通过，reject=退回

    # 部门管理员只能审批本部门员工的任务
    if request.is_dept_admin:
        if task_obj.owner.depart != request.admin_object.depart:
            return redirect("/task/list/")

    # 状态从"待审批" → "已完成"或"已退回"
    if task_obj.status == 2:
        if action == 'approve':
            task_obj.status = 3  # 已完成
        else:
            task_obj.status = 4  # 已退回
        task_obj.save()

    return redirect("/task/list/")


# ============================================================
# 超级管理员查收任务
# URL: /task/<int:nid>/archive/
# ============================================================
def task_archive(request, nid):
    """超级管理员查收任务，归档"""
    task_obj = models.Task.objects.filter(id=nid).first()
    if not task_obj:
        return redirect("/task/list/")

    # 状态从"已完成" → "已归档"
    if task_obj.status == 3:
        task_obj.status = 5  # 已归档
        task_obj.save()

    return redirect("/task/list/")
