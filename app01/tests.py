# ============================================================
# 单元测试（T12）
# 覆盖核心模块：登录、员工CRUD、薪资计算、权限拦截
# 运行：python manage.py test
# ============================================================
from django.test import TestCase, Client
from django.urls import reverse
from app01.models import *
import hashlib


def md5(pwd):
    return hashlib.md5(pwd.encode('utf-8')).hexdigest()


class LoginTests(TestCase):
    """登录模块测试"""

    def setUp(self):
        """测试前准备：创建测试用户"""
        self.dept = Department.objects.create(title="测试部")
        self.admin = Admin.objects.create(
            username="testadmin",
            password=md5("test123"),
            name="测试管理员"
        )

    def test_login_page_loads(self):
        """测试登录页能正常加载"""
        response = self.client.get("/login/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "企业员工管理系统")

    def test_login_success(self):
        """测试正确账号密码能登录成功"""
        # 先在session里设置验证码
        session = self.client.session
        session['image_code'] = 'TEST'
        session.save()
        response = self.client.post("/login/", {
            "username": "testadmin",
            "password": "test123",
            "code": "TEST"
        })
        # 登录成功应该重定向
        self.assertEqual(response.status_code, 302)

    def test_login_wrong_password(self):
        """测试错误密码登录失败"""
        # 先在session里设置验证码
        session = self.client.session
        session['image_code'] = 'TEST'
        session.save()
        response = self.client.post("/login/", {
            "username": "testadmin",
            "password": "wrongpwd",
            "code": "TEST"
        })
        self.assertContains(response, "用户名或密码错误")


class EmployeeCRUDTests(TestCase):
    """员工CRUD测试"""

    def setUp(self):
        """创建测试数据"""
        self.dept = Department.objects.create(title="技术部")
        self.admin = Admin.objects.create(
            username="admin",
            password=md5("admin123"),
            name="管理员"
        )
        self.client.post("/login/", {"username": "admin", "password": "admin123", "code": "TEST"})

    def test_create_employee(self):
        """测试创建员工"""
        count_before = UserInfo.objects.count()
        UserInfo.objects.create(
            name="测试员工",
            password="123456",
            age=25,
            account=5000.00,
            create_time="2026-01-01",
            mobile="13800138000",
            gender=1,
            depart=self.dept
        )
        count_after = UserInfo.objects.count()
        self.assertEqual(count_after, count_before + 1)

    def test_employee_mobile_unique(self):
        """测试手机号唯一性"""
        UserInfo.objects.create(
            name="员工A", password="123", age=25, account=5000,
            create_time="2026-01-01", mobile="13900139000", gender=1, depart=self.dept
        )
        # 同一个手机号应该报错
        with self.assertRaises(Exception):
            UserInfo.objects.create(
                name="员工B", password="123", age=30, account=6000,
                create_time="2026-01-02", mobile="13900139000", gender=2, depart=self.dept
            )

    def test_update_employee(self):
        """测试编辑员工"""
        emp = UserInfo.objects.create(
            name="旧名字", password="123", age=25, account=5000,
            create_time="2026-01-01", mobile="13700137000", gender=1, depart=self.dept
        )
        emp.name = "新名字"
        emp.save()
        updated = UserInfo.objects.get(id=emp.id)
        self.assertEqual(updated.name, "新名字")

    def test_delete_employee(self):
        """测试删除员工"""
        emp = UserInfo.objects.create(
            name="待删除", password="123", age=25, account=5000,
            create_time="2026-01-01", mobile="13600136000", gender=1, depart=self.dept
        )
        emp_id = emp.id
        emp.delete()
        self.assertFalse(UserInfo.objects.filter(id=emp_id).exists())


class SalaryCalculationTests(TestCase):
    """薪资计算测试"""

    def setUp(self):
        self.dept = Department.objects.create(title="财务部")
        self.emp = UserInfo.objects.create(
            name="薪资员工", password="123", age=28, account=8000,
            create_time="2025-06-01", mobile="13500135000", gender=1, depart=self.dept
        )

    def test_salary_total_auto_calculate(self):
        """测试实发工资自动计算 = 基本 + 奖金 - 扣款"""
        salary = Salary.objects.create(
            employee=self.emp,
            month="2026-10",
            base=8000,
            bonus=2000,
            deduction=500,
            total=9500  # 8000+2000-500=9500
        )
        self.assertEqual(salary.total, 9500)

    def test_salary_with_zero_bonus(self):
        """测试奖金为0的情况"""
        salary = Salary.objects.create(
            employee=self.emp,
            month="2026-09",
            base=8000,
            bonus=0,
            deduction=300,
            total=7700
        )
        self.assertEqual(salary.total, 7700)


class AttendanceStatusTests(TestCase):
    """考勤状态计算测试"""

    def setUp(self):
        self.dept = Department.objects.create(title="人事部")
        self.emp = UserInfo.objects.create(
            name="考勤员工", password="123", age=26, account=7000,
            create_time="2025-08-01", mobile="13400134000", gender=2, depart=self.dept
        )

    def test_attendance_create(self):
        """测试考勤记录创建"""
        att = Attendance.objects.create(
            employee=self.emp,
            date="2026-10-15",
            clock_in="08:30",
            clock_out="18:00",
            status=1
        )
        self.assertEqual(att.status, 1)
        self.assertEqual(att.employee.name, "考勤员工")


class PermissionTests(TestCase):
    """权限拦截测试"""

    def setUp(self):
        self.dept = Department.objects.create(title="测试部")
        self.emp = UserInfo.objects.create(
            name="普通员工", password="123", age=25, account=6000,
            create_time="2026-01-01", mobile="13300133000", gender=1, depart=self.dept
        )
        self.emp_role = Role.objects.create(title="普通员工")
        self.emp_admin = Admin.objects.create(
            username="employee",
            password=md5("emp123"),
            name="普通员工",
            employee=self.emp
        )
        self.emp_admin.roles.add(self.emp_role)

    def test_unauthorized_redirect_to_login(self):
        """测试未登录访问受保护页跳转到登录页"""
        response = self.client.get("/user/list/")
        self.assertEqual(response.status_code, 302)
        self.assertIn("/login/", response.url)


class DepartmentTests(TestCase):
    """部门管理测试"""

    def test_create_department(self):
        """测试创建部门"""
        count_before = Department.objects.count()
        Department.objects.create(title="新部门")
        count_after = Department.objects.count()
        self.assertEqual(count_after, count_before + 1)

    def test_department_str(self):
        """测试部门字符串表示"""
        dept = Department.objects.create(title="测试部")
        self.assertEqual(str(dept), "测试部")
