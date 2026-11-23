# ============================================================
# 模块：员工管理视图
# 作用：处理员工列表、新增、编辑、删除的HTTP请求
# 重点：数据权限过滤（部门管理员只看本部门，普通员工只看自己）
# ============================================================
from django.shortcuts import render, redirect
from app01 import models
from app01.forms import UserModelForm, UserEditModelForm


# ============================================================
# 视图函数：员工列表
# URL: /user/list/
# ============================================================
def user_list(request):
    """
    用户列表 - 根据权限过滤，按入职时间倒序，支持筛选搜索

    数据权限隔离逻辑：
    - 超级管理员：看到全部21个员工
    - 部门管理员：只看到本部门5个员工
    - 普通员工：只看到自己1个人的档案
    同一个URL，不同人看到不同数据
    """

    # ---- 第1步：基础查询（ORM性能优化）----
    # select_related('depart')：一次性JOIN查出部门名称，避免N+1查询
    # 原来：查21个员工 + 每个员工查一次部门 = 22次SQL
    # 现在：1次JOIN查询就搞定
    queryset = models.UserInfo.objects.select_related('depart').all().order_by('-create_time')
    # order_by('-create_time')：按入职时间倒序（最新入职的排在前面）

    # ---- 第2步：接收筛选条件 ----
    search_name = request.GET.get("name", "")      # 按姓名搜索
    search_depart = request.GET.get("depart", "")  # 按部门筛选
    search_gender = request.GET.get("gender", "")  # 按性别筛选

    # ---- 第3步：应用筛选条件 ----
    if search_name:
        # name__icontains = 姓名模糊匹配（不区分大小写），相当于SQL的 LIKE '%张%'
        queryset = queryset.filter(name__icontains=search_name)

    if search_depart:
        # 按部门ID筛选
        queryset = queryset.filter(depart_id=search_depart)

    if search_gender:
        # 按性别筛选（1男，2女）
        queryset = queryset.filter(gender=search_gender)

    # ---- 第4步：数据权限过滤（核心！）----
    # 中间件已经帮我们判断好了角色，直接用就行
    # request.is_super_admin / is_dept_admin / is_employee 三个布尔值

    # 部门管理员：只能看自己部门的员工
    if hasattr(request, 'is_dept_admin') and request.is_dept_admin:
        if request.admin_object.depart:  # 如果这个管理员关联了部门
            # 只过滤出本部门的员工
            queryset = queryset.filter(depart=request.admin_object.depart)

    # 普通员工：只能看自己的档案
    if hasattr(request, 'is_employee') and request.is_employee:
        if request.admin_object.employee:  # 如果关联了员工档案
            # 只过滤出自己这条记录
            queryset = queryset.filter(id=request.admin_object.employee.id)
        else:
            # 如果没关联员工档案，就返回空查询集
            queryset = queryset.none()

    # ---- 第5步：统计数据（统计卡片用）----
    # 注意：统计数字是基于"权限范围内的全量数据"，不是筛选后的
    # 比如部门管理员看到的是本部门总人数，不是筛选后的人数
    all_emps = models.UserInfo.objects.all()

    # 统计数据也要按权限过滤！
    if hasattr(request, 'is_dept_admin') and request.is_dept_admin:
        if request.admin_object.depart:
            all_emps = all_emps.filter(depart=request.admin_object.depart)

    if hasattr(request, 'is_employee') and request.is_employee:
        if request.admin_object.employee:
            all_emps = all_emps.filter(id=request.admin_object.employee.id)
        else:
            all_emps = all_emps.none()

    # 计算男女数量
    male_count = all_emps.filter(gender=1).count()
    female_count = all_emps.filter(gender=2).count()

    # ---- 第6步：把数据传给模板 ----
    context = {
        "queryset": queryset,          # 员工列表数据（已筛选+已权限过滤）
        "male_count": male_count,       # 男性人数
        "female_count": female_count,  # 女性人数
        "total_count": all_emps.count(),  # 总人数
        "depart_list": models.Department.objects.all(),  # 部门下拉框
        "search_name": search_name,    # 搜索框里保留用户输入的内容
        "search_depart": search_depart,
        "search_gender": search_gender,
    }
    return render(request, "user_list.html", context)


# ============================================================
# 视图函数：新增员工
# URL: /user/add/
# ============================================================
def user_add(request):
    """新建用户（用ModelForm自动生成表单）"""

    # 普通员工不能新增员工
    if hasattr(request, 'is_employee') and request.is_employee:
        return redirect("/notice/list/")

    # GET请求：显示空表单
    if request.method == "GET":
        form = UserModelForm()  # ModelForm自动生成表单HTML
        return render(request, "user_add.html", {"form": form})

    # POST请求：接收用户提交的数据 + 上传的文件（头像）
    # files=request.FILES 是关键！没有这个参数，文件不会被处理
    form = UserModelForm(data=request.POST, files=request.FILES)
    if form.is_valid():  # 自动校验数据格式
        form.save()     # 自动保存到数据库（含头像文件）
        return redirect("/user/list/")
    # 如果校验失败，重新显示表单（带错误信息）
    return render(request, "user_add.html", {"form": form})


# ============================================================
# 视图函数：编辑员工
# URL: /user/<int:nid>/edit/
# ============================================================
def user_edit(request, nid):
    """编辑员工信息"""
    # 先查这条员工记录存不存在
    row_object = models.UserInfo.objects.filter(id=nid).first()
    if not row_object:
        return redirect("/user/list/")

    # 普通员工不能编辑别人
    if hasattr(request, 'is_employee') and request.is_employee:
        return redirect("/user/list/")

    # 部门管理员只能编辑本部门员工
    if hasattr(request, 'is_dept_admin') and request.is_dept_admin:
        if request.admin_object.depart and row_object.depart != request.admin_object.depart:
            # 要编辑的员工不属于本部门，拦截
            return redirect("/user/list/")

    # GET请求：显示编辑表单（带原有数据）
    if request.method == "GET":
        form = UserEditModelForm(instance=row_object)  # instance= 把原有数据填进去
        return render(request, "user_edit.html", {"form": form})

    # POST请求：保存修改（同时接收文件数据）
    form = UserEditModelForm(data=request.POST, files=request.FILES, instance=row_object)
    if form.is_valid():
        form.save()
        return redirect("/user/list/")
    return render(request, "user_edit.html", {"form": form})


# ============================================================
# 视图函数：删除员工
# URL: /user/<int:nid>/delete/
# ============================================================
def user_delete(request, nid):
    """删除员工"""
    # 普通员工不能删除
    if hasattr(request, 'is_employee') and request.is_employee:
        return redirect("/user/list/")

    # 先查这条记录存不存在
    row_object = models.UserInfo.objects.filter(id=nid).first()

    # 部门管理员只能删除本部门员工
    if hasattr(request, 'is_dept_admin') and request.is_dept_admin:
        if row_object and request.admin_object.depart and row_object.depart != request.admin_object.depart:
            return redirect("/user/list/")

    # 执行删除
    models.UserInfo.objects.filter(id=nid).delete()
    return redirect("/user/list/")
