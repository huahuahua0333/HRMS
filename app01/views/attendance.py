# ============================================================
# 导入模块
# ============================================================
from django.shortcuts import render, redirect
from app01 import models
from app01.forms import AttendanceModelForm
from app01.utils.pagination import Pagination
from datetime import datetime


# ============================================================
# 考勤列表
# URL: /attendance/list/
# ============================================================
def attendance_list(request):
    """考勤列表 - 根据权限过滤，按日期倒序，支持按员工和状态筛选"""
    # select_related 优化：一次性查出employee及其depart，避免N+1查询
    queryset = models.Attendance.objects.select_related('employee__depart').all().order_by('-date', '-clock_in')

    # 部门管理员：只能看本部门员工的考勤
    if hasattr(request, 'is_dept_admin') and request.is_dept_admin:
        if request.admin_object.depart:
            queryset = queryset.filter(employee__depart=request.admin_object.depart)

    # 普通员工：只能看自己的考勤
    if hasattr(request, 'is_employee') and request.is_employee:
        if request.admin_object.employee:
            queryset = queryset.filter(employee_id=request.admin_object.employee.id)
        else:
            queryset = queryset.none()

    # ========== 筛选功能 ==========
    # 按员工筛选
    search_emp = request.GET.get("employee", "")
    if search_emp:
        queryset = queryset.filter(employee_id=search_emp)

    # 按状态筛选
    search_status = request.GET.get("status", "")
    if search_status:
        queryset = queryset.filter(status=search_status)

    # 筛选后可选的员工列表（按权限范围）
    emp_qs = models.UserInfo.objects.all()
    if hasattr(request, 'is_dept_admin') and request.is_dept_admin:
        if request.admin_object.depart:
            emp_qs = emp_qs.filter(depart=request.admin_object.depart)
    if hasattr(request, 'is_employee') and request.is_employee:
        if request.admin_object.employee:
            emp_qs = emp_qs.filter(id=request.admin_object.employee.id)

    page_object = Pagination(request, queryset)
    context = {
        "queryset": page_object.page_queryset,
        "page_string": page_object.html(),
        "emp_list": emp_qs,
        "search_emp": search_emp,
        "search_status": search_status,
        "status_choices": {1: "按时", 2: "迟到", 3: "早退", 4: "缺勤", 5: "请假"},
    }
    return render(request, "attendance_list.html", context)


# ============================================================
# 新建考勤
# URL: /attendance/add/
# ============================================================
def attendance_add(request):
    """新建考勤：自动计算考勤状态"""
    # 普通员工不能录入考勤
    if hasattr(request, 'is_employee') and request.is_employee:
        return redirect("/attendance/list/")

    if request.method == "GET":
        form = AttendanceModelForm()
        return render(request, "change.html", {"form": form, "title": "新建考勤"})

    form = AttendanceModelForm(data=request.POST)
    if form.is_valid():
        # 尊重用户手动选择的考勤状态（比如请假），不自动覆盖
        # 用户可以在表单里手动选择：按时/迟到/早退/缺勤/请假
        form.save()
        return redirect("/attendance/list/")
    return render(request, "change.html", {"form": form, "title": "新建考勤"})


# ============================================================
# 编辑考勤
# URL: /attendance/<int:nid>/edit/
# ============================================================
def attendance_edit(request, nid):
    """编辑考勤记录"""
    # 普通员工不能编辑
    if hasattr(request, 'is_employee') and request.is_employee:
        return redirect("/attendance/list/")

    row_object = models.Attendance.objects.filter(id=nid).first()
    if not row_object:
        return redirect("/attendance/list/")

    if request.method == "GET":
        form = AttendanceModelForm(instance=row_object)
        return render(request, "change.html", {"form": form, "title": "编辑考勤"})

    form = AttendanceModelForm(data=request.POST, instance=row_object)
    if form.is_valid():
        form.save()
        return redirect("/attendance/list/")
    return render(request, "change.html", {"form": form, "title": "编辑考勤"})


# ============================================================
# 删除考勤
# URL: /attendance/<int:nid>/delete/
# ============================================================
def attendance_delete(request, nid):
    """删除考勤记录"""
    # 普通员工不能删除
    if hasattr(request, 'is_employee') and request.is_employee:
        return redirect("/attendance/list/")

    models.Attendance.objects.filter(id=nid).delete()
    return redirect("/attendance/list/")
