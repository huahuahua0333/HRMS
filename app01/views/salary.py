# ============================================================
# 导入模块
# ============================================================
from django.shortcuts import render, redirect
from app01 import models
from app01.forms import SalaryModelForm
from app01.utils.pagination import Pagination
from django.db.models import Sum


# ============================================================
# 薪资列表
# URL: /salary/list/
# ============================================================
def salary_list(request):
    """薪资列表：支持按月份/员工筛选，统计薪资总额"""
    # 筛选条件
    search_month = request.GET.get("month", "")
    search_employee = request.GET.get("employee", "")

    # select_related 优化：一次性查出employee及其depart，避免N+1查询
    queryset = models.Salary.objects.select_related('employee__depart').all().order_by('-month', 'employee__name')

    # 部门管理员：只能看本部门员工的薪资
    if hasattr(request, 'is_dept_admin') and request.is_dept_admin:
        if request.admin_object.depart:
            queryset = queryset.filter(employee__depart=request.admin_object.depart)

    # 普通员工：只能看自己的薪资
    if hasattr(request, 'is_employee') and request.is_employee:
        if request.admin_object.employee:
            queryset = queryset.filter(employee_id=request.admin_object.employee.id)
        else:
            queryset = queryset.none()

    if search_month:
        queryset = queryset.filter(month=search_month)
    if search_employee:
        # 普通员工不能筛选别人
        if not hasattr(request, 'is_employee') or not request.is_employee:
            queryset = queryset.filter(employee_id=search_employee)

    # 统计薪资总额
    total_sum = queryset.aggregate(total=Sum('total'))['total'] or 0

    # 员工筛选下拉框：部门管理员只显示本部门员工
    employee_list = models.UserInfo.objects.select_related('depart').all()
    if hasattr(request, 'is_dept_admin') and request.is_dept_admin:
        if request.admin_object.depart:
            employee_list = employee_list.filter(depart=request.admin_object.depart)

    page_object = Pagination(request, queryset)
    context = {
        "queryset": page_object.page_queryset,
        "page_string": page_object.html(),
        "total_sum": total_sum,
        "search_month": search_month,
        "search_employee": search_employee,
        "employee_list": employee_list,
    }
    return render(request, "salary_list.html", context)


# ============================================================
# 新建薪资
# URL: /salary/add/
# ============================================================
def salary_add(request):
    """新建薪资：自动计算实发=基本+奖金-扣款"""
    # 普通员工不能录入薪资
    if hasattr(request, 'is_employee') and request.is_employee:
        return redirect("/salary/list/")

    if request.method == "GET":
        form = SalaryModelForm()
        return render(request, "change.html", {"form": form, "title": "新建薪资"})

    form = SalaryModelForm(data=request.POST)
    if form.is_valid():
        # 自动计算实发工资
        data = form.cleaned_data
        data["total"] = data["base"] + data["bonus"] - data["deduction"]
        form.save()
        return redirect("/salary/list/")
    return render(request, "change.html", {"form": form, "title": "新建薪资"})


# ============================================================
# 编辑薪资
# URL: /salary/<int:nid>/edit/
# ============================================================
def salary_edit(request, nid):
    """编辑薪资记录"""
    # 普通员工不能编辑
    if hasattr(request, 'is_employee') and request.is_employee:
        return redirect("/salary/list/")

    row_object = models.Salary.objects.filter(id=nid).first()
    if not row_object:
        return redirect("/salary/list/")

    if request.method == "GET":
        form = SalaryModelForm(instance=row_object)
        return render(request, "change.html", {"form": form, "title": "编辑薪资"})

    form = SalaryModelForm(data=request.POST, instance=row_object)
    if form.is_valid():
        # 自动重新计算实发工资
        data = form.cleaned_data
        data["total"] = data["base"] + data["bonus"] - data["deduction"]
        form.save()
        return redirect("/salary/list/")
    return render(request, "change.html", {"form": form, "title": "编辑薪资"})


# ============================================================
# 删除薪资
# URL: /salary/<int:nid>/delete/
# ============================================================
def salary_delete(request, nid):
    """删除薪资记录"""
    # 普通员工不能删除
    if hasattr(request, 'is_employee') and request.is_employee:
        return redirect("/salary/list/")

    models.Salary.objects.filter(id=nid).delete()
    return redirect("/salary/list/")
