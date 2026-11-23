# ============================================================
# 模块：数据可视化仪表盘（ECharts）
# 作用：提供统计图表数据的API接口
# 重点：所有图表数据都按用户权限过滤
# ============================================================
from django.shortcuts import render
from django.http import JsonResponse
from django.db.models import Count, Sum
from app01 import models


# ============================================================
# 辅助函数：根据用户角色过滤数据范围
# 作用：统一的数据权限过滤逻辑，避免每个视图重复写
# ============================================================
def filter_queryset_by_role(request, queryset, model_name):
    """
    根据用户角色过滤查询集

    参数：
        request: HTTP请求对象（包含用户角色信息）
        queryset: 要过滤的查询集
        model_name: 模型名称（employee/attendance/salary）

    返回：过滤后的查询集
    """
    # 部门管理员：只看自己部门的数据
    if hasattr(request, 'is_dept_admin') and request.is_dept_admin:
        if request.admin_object.depart:
            if model_name == 'employee':
                # 员工表直接按部门过滤
                return queryset.filter(depart=request.admin_object.depart)
            elif model_name == 'attendance':
                # 考勤表关联员工，员工再关联部门，所以要 employee__depart
                return queryset.filter(employee__depart=request.admin_object.depart)
            elif model_name == 'salary':
                # 薪资表同理，跨两层关联
                return queryset.filter(employee__depart=request.admin_object.depart)
    # 超级管理员：返回全部数据
    return queryset


# ============================================================
# 视图函数：仪表盘页面
# URL: /dashboard/
# ============================================================
def dashboard(request):
    """数据可视化仪表盘页面"""
    return render(request, "dashboard.html")


# ============================================================
# 视图函数：角色权限演示页面
# URL: /roles_demo/
# ============================================================
def roles_demo(request):
    """角色权限演示页面：展示三级角色的功能对比"""
    return render(request, "roles_demo.html")


# ============================================================
# API接口：顶部统计数字
# URL: /dashboard/overview/
# 返回：JSON格式的统计数据
# ============================================================
def overview(request):
    """
    返回顶部统计卡片数字
    包括：员工总数、部门数量、月度薪资总额、考勤记录数

    数据权限：
    - 超级管理员：全公司数据
    - 部门管理员：本部门数据
    """
    # 员工总数
    emp_count = filter_queryset_by_role(request, models.UserInfo.objects.all(), 'employee').count()

    # 部门数量
    # 超级管理员看全部部门数，部门管理员只算1个
    if hasattr(request, 'is_dept_admin') and request.is_dept_admin:
        dept_count = 1 if request.admin_object.depart else 0
    else:
        dept_count = models.Department.objects.count()

    # 最新月份的薪资总额
    salary_qs = filter_queryset_by_role(request, models.Salary.objects.all(), 'salary')
    latest_month = salary_qs.order_by('-month').first()  # 取最新月份
    salary_total = 0
    if latest_month:
        # 统计最新月份的薪资总和
        salary_total = salary_qs.filter(month=latest_month.month).aggregate(total=Sum('total'))['total'] or 0

    # 考勤记录数
    att_count = filter_queryset_by_role(request, models.Attendance.objects.all(), 'attendance').count()

    # 返回JSON格式数据，前端AJAX调用
    return JsonResponse({
        "status": True,
        "emp_count": emp_count,
        "dept_count": dept_count,
        "salary_total": float(salary_total),
        "att_count": att_count
    })


# ============================================================
# API接口：部门人数分布
# URL: /dashboard/department_data/
# 返回：饼图数据（每个部门的人数）
# ============================================================
def department_data(request):
    """
    返回各部门人数统计，供ECharts饼图使用

    超级管理员：显示所有部门的人数分布
    部门管理员：只显示自己部门的数据
    """
    # 部门管理员只看自己部门
    if hasattr(request, 'is_dept_admin') and request.is_dept_admin:
        if request.admin_object.depart:
            dept = request.admin_object.depart
            count = dept.userinfo_set.count()  # 反向查询部门下的员工数
            return JsonResponse({
                "status": True,
                "data": [{"name": dept.title, "value": count}]
            })

    # 超级管理员：统计所有部门
    # annotate(emp_count=Count('userinfo'))：每个部门统计员工数
    depts = models.Department.objects.annotate(emp_count=Count('userinfo')).values('title', 'emp_count')
    data = [{"name": d['title'], "value": d['emp_count']} for d in depts]
    return JsonResponse({"status": True, "data": data})


# ============================================================
# API接口：各月薪资趋势
# URL: /dashboard/salary_trend/
# 返回：折线图数据（每个月的薪资总额）
# ============================================================
def salary_trend(request):
    """
    返回各月薪资总额趋势，供ECharts折线图使用
    """
    queryset = models.Salary.objects.all()
    # 按权限过滤
    queryset = filter_queryset_by_role(request, queryset, 'salary')

    # 按月份分组，统计每个月的薪资总和
    monthly = queryset.values('month').annotate(
        total=Sum('total')
    ).order_by('month')

    # 整理成两个数组：月份列表和金额列表
    months = []
    totals = []
    for m in monthly:
        months.append(m['month'])
        totals.append(float(m['total']))

    return JsonResponse({
        "status": True,
        "months": months,
        "totals": totals
    })


# ============================================================
# API接口：考勤状态分布
# URL: /dashboard/attendance_stats/
# 返回：饼图数据（按时/迟到/早退/缺勤各多少人）
# ============================================================
def attendance_stats(request):
    """返回考勤状态分布统计"""
    queryset = models.Attendance.objects.all()
    # 按权限过滤
    queryset = filter_queryset_by_role(request, queryset, 'attendance')

    # 按状态分组统计
    stats = queryset.values('status').annotate(count=Count('id'))

    # 状态数字转中文
    status_map = {1: "按时", 2: "迟到", 3: "早退", 4: "缺勤", 5: "请假"}
    data = [{"name": status_map.get(s['status'], "未知"), "value": s['count']} for s in stats]

    return JsonResponse({"status": True, "data": data})
