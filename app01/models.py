# ============================================================
# 模块：数据模型层（Models）
# 作用：定义数据库表结构，Django ORM会自动生成对应的SQL建表语句
# 设计思路：每个类对应一张数据库表，每个类属性对应一个字段
# ============================================================
from django.db import models


# ============================================================
# 表名：部门表（Department）
# 作用：存储公司所有部门（技术部、市场部、财务部等）
# 关系：和员工是一对多关系（一个部门有多个员工）
# ============================================================
class Department(models.Model):
    title = models.CharField(max_length=32, verbose_name="部门名称")  # 部门名称，最多32个字符

    def __str__(self):
        """打印对象时显示部门名称，方便调试"""
        return self.title


# ============================================================
# 表名：员工表（UserInfo）
# 作用：存储所有员工的档案信息
# 关系：和部门是多对一关系（多个员工属于一个部门）
# ============================================================
class UserInfo(models.Model):
    # ---- 基本信息字段 ----
    name = models.CharField(max_length=16, verbose_name="姓名")        # 姓名
    password = models.CharField(max_length=64, verbose_name="密码")    # 员工密码（MD5加密后存）
    age = models.IntegerField(verbose_name="年龄")                    # 年龄
    account = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="账户")  # 账户余额
    create_time = models.DateField(verbose_name="入职时间")            # 入职日期
    mobile = models.CharField(max_length=11, verbose_name="手机号", unique=True, default="")  # 手机号（唯一约束）
    avatar = models.ImageField(verbose_name="头像", upload_to="avatar/", default="avatar/default.png")  # 头像

    # ---- 外键字段：关联部门 ----
    # ForeignKey = 多对一关系：多个员工属于一个部门
    # on_delete=models.CASCADE = 部门删除时，该部门下的员工也一起删除
    depart = models.ForeignKey(
        to="Department",        # 关联到Department表
        to_field="id",          # 关联的是Department表的id字段
        on_delete=models.CASCADE,
        verbose_name="所属部门"
    )

    # ---- 性别字段（用数字存，节省空间）----
    # choices = 下拉选择框，数据库里存数字，页面上显示中文
    gender_choices = (
        (1, "男"),   # 数据库存1，显示"男"
        (2, "女"),   # 数据库存2，显示"女"
    )
    gender = models.SmallIntegerField(choices=gender_choices, verbose_name="性别")

    def __str__(self):
        return self.name


# ============================================================
# 表名：管理员表（Admin）
# 作用：存储所有能登录系统的账号（超级管理员、部门管理员、普通员工）
# 关系：
#   - 和Role（角色）是多对多关系（一个账号可以有多个角色）
#   - 和Department（部门）是多对一（部门管理员管辖的部门）
#   - 和UserInfo（员工）是多对一（普通员工账号关联的员工档案）
# ============================================================
class Admin(models.Model):
    # ---- 登录账号信息 ----
    username = models.CharField(max_length=32, verbose_name="用户名")  # 登录用户名
    password = models.CharField(max_length=64, verbose_name="密码")    # 登录密码（MD5加密）
    name = models.CharField(max_length=16, verbose_name="姓名", default="")  # 显示姓名

    # ---- 多对多：一个管理员可以有多个角色 ----
    # blank=True = 表单里可以不选（允许没有角色）
    roles = models.ManyToManyField(to="Role", blank=True, verbose_name="角色")

    # ---- 部门管理员：管辖的部门 ----
    # null=True, blank=True = 超级管理员这个字段是空的（管全部）
    # on_delete=models.SET_NULL = 部门删除时，这个管理员的部门字段置空
    depart = models.ForeignKey(
        to="Department",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="管辖部门"
    )

    # ---- 普通员工账号：关联的员工档案 ----
    # 普通员工登录后，通过这个字段知道自己是谁，只能看自己的数据
    employee = models.ForeignKey(
        to="UserInfo",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="关联员工"
    )

    def __str__(self):
        return self.username


# ============================================================
# 表名：角色表（Role）—— RBAC权限模型的核心
# 作用：定义系统中的角色（超级管理员、部门管理员、普通员工）
# 关系：和Permission（权限）是多对多关系
# ============================================================
class Role(models.Model):
    """
    RBAC（Role-Based Access Control）= 基于角色的访问控制

    设计思路：
    用户 → 角色 → 权限
    不是直接给用户分配权限，而是通过角色作为中间层
    修改角色权限，所有拥有该角色的用户自动生效
    """
    title = models.CharField(max_length=32, verbose_name="角色名称")  # 角色名：超级管理员/部门管理员/普通员工

    # 多对多：一个角色可以有多个权限
    permissions = models.ManyToManyField(to="Permission", blank=True, verbose_name="权限")

    def __str__(self):
        return self.title


# ============================================================
# 表名：权限表（Permission）
# 作用：定义系统中所有的权限点（部门列表、员工列表、薪资录入等）
# ============================================================
class Permission(models.Model):
    title = models.CharField(max_length=32, verbose_name="权限名称")  # 权限名
    url = models.CharField(max_length=128, verbose_name="权限URL", blank=True)  # 对应的URL路径

    def __str__(self):
        return self.title


# ============================================================
# 表名：考勤表（Attendance）
# 作用：记录每个员工每天的考勤情况
# ============================================================
class Attendance(models.Model):
    """
    考勤记录：员工 + 日期 + 上下班时间 + 状态
    """
    # 外键：哪个员工的考勤
    employee = models.ForeignKey(to="UserInfo", on_delete=models.CASCADE, verbose_name="员工")
    date = models.DateField(verbose_name="日期")  # 考勤日期
    clock_in = models.TimeField(verbose_name="上班时间", null=True, blank=True)  # 上班打卡时间（缺勤时为空）
    clock_out = models.TimeField(verbose_name="下班时间", null=True, blank=True)  # 下班打卡时间

    # 考勤状态：1按时，2迟到，3早退，4缺勤，5请假
    status_choices = (
        (1, "按时"),
        (2, "迟到"),
        (3, "早退"),
        (4, "缺勤"),
        (5, "请假"),
    )
    status = models.SmallIntegerField(choices=status_choices, default=4, verbose_name="考勤状态")

    def __str__(self):
        return f"{self.employee.name} - {self.date}"


# ============================================================
# 表名：薪资表（Salary）
# 作用：记录每个员工每个月的工资
# ============================================================
class Salary(models.Model):
    """
    薪资记录：员工 + 月份 + 基本工资 + 奖金 + 扣款 + 实发
    """
    # 外键：哪个员工的薪资
    employee = models.ForeignKey(to="UserInfo", on_delete=models.CASCADE, verbose_name="员工")
    month = models.CharField(max_length=7, verbose_name="月份", help_text="格式：2026-01")  # 月份（字符串格式，方便排序）

    # 薪资明细：基本工资、奖金、扣款、实发
    base = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="基本工资")
    bonus = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="奖金")
    deduction = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="扣款")
    total = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="实发工资")

    def __str__(self):
        return f"{self.employee.name} - {self.month}"


# ============================================================
# 表名：公告表（Notice）
# 作用：公司发布的通知公告
# ============================================================
class Notice(models.Model):
    title = models.CharField(max_length=64, verbose_name="标题")      # 公告标题
    content = models.TextField(verbose_name="内容")                    # 公告内容（长文本）
    publisher = models.ForeignKey(to="Admin", on_delete=models.CASCADE, verbose_name="发布人")  # 谁发布的
    publish_time = models.DateTimeField(auto_now_add=True, verbose_name="发布时间")  # 自动记录发布时间
    is_top = models.BooleanField(default=False, verbose_name="是否置顶")  # 是否置顶显示

    def __str__(self):
        return self.title


# ============================================================
# 表名：任务表（Task）
# 作用：分配给员工的任务
# ============================================================
class Task(models.Model):
    """
    任务：级别 + 标题 + 详情 + 负责人
    """
    # 任务级别：1紧急，2重要，3普通
    level_choices = (
        (1, "紧急"),
        (2, "重要"),
        (3, "普通"),
    )
    level = models.SmallIntegerField(choices=level_choices, verbose_name="级别")
    title = models.CharField(max_length=64, verbose_name="标题")      # 任务标题
    detail = models.TextField(verbose_name="详细信息")                  # 任务详情
    owner = models.ForeignKey(to="UserInfo", on_delete=models.CASCADE, verbose_name="负责人")  # 谁负责

    # 任务状态：三级工作流
    status_choices = (
        (1, "待完成"),    # 刚创建，员工还没做
        (2, "待审批"),    # 员工点了完成，等部门负责人审批
        (3, "已完成"),    # 部门审批通过，等超管查收
        (4, "已退回"),    # 部门审批不通过，退回重做
        (5, "已归档"),    # 超管查收完成，任务结束
    )
    status = models.SmallIntegerField(choices=status_choices, default=1, verbose_name="状态")

    def __str__(self):
        return self.title


# ============================================================
# 表名：公司制度表（Policy）
# 作用：存储成文的公司规章制度（考勤、请假、薪酬、奖惩、办公规范），
#       供 AI 制度知识库问答时作为上下文引用
# ============================================================
class Policy(models.Model):
    # 制度类别：1考勤管理 2请假休假 3薪酬福利 4奖惩制度 5办公规范
    category_choices = (
        (1, "考勤管理"),
        (2, "请假休假"),
        (3, "薪酬福利"),
        (4, "奖惩制度"),
        (5, "办公规范"),
    )
    title = models.CharField(max_length=64, verbose_name="制度标题")
    category = models.SmallIntegerField(choices=category_choices, verbose_name="制度类别")
    content = models.TextField(verbose_name="制度正文")
    is_active = models.BooleanField(default=True, verbose_name="是否启用")
    create_time = models.DateTimeField(auto_now_add=True, verbose_name="录入时间")

    def __str__(self):
        return self.title


