# ============================================================
# 模块：RBAC权限中间件
# 作用：所有HTTP请求都要经过这里，统一做登录校验和权限控制
# 设计思路：把权限判断从视图层抽出来，统一在中间件里做，
#          这样每个视图函数就不用重复写权限检查了
# ============================================================
from django.utils.deprecation import MiddlewareMixin         # Django中间件基类
from django.shortcuts import redirect                        # 重定向函数
from app01 import models                                     # 导入数据库模型


# ============================================================
# 类名：AuthMiddleware
# 继承：MiddlewareMixin（Django 4.x的中间件基类）
# 作用：登录校验 + 角色识别 + 权限拦截
# ============================================================
class AuthMiddleware(MiddlewareMixin):
    """
    登录校验 + 权限控制中间件

    工作流程：
    1. 白名单放行（登录页、验证码不需要登录）
    2. 检查Session判断是否已登录
    3. 从数据库加载用户对象和角色
    4. 识别角色类型（超级管理员/部门管理员/普通员工）
    5. 根据角色做权限拦截
    """

    # 白名单：不需要登录就能访问的URL
    # 为什么要白名单？因为登录页本身你还没登录，总不能让你永远进不去
    WHITE_LIST = ["/login/", "/image/code/"]

    # process_request：Django规定的方法名，请求到达视图之前自动执行
    def process_request(self, request):
        """
        request对象：Django封装的HTTP请求对象
        返回值：
          - return（空）= 放行，继续执行后面的视图
          - return redirect(...) = 拦截，重定向到别的页面
        """

        # ====================================================
        # 第0步：白名单放行
        # ====================================================
        # 如果用户访问的是登录页或验证码，直接放行
        if request.path_info in self.WHITE_LIST:
            return  # 空return = 放行

        # ====================================================
        # 第1步：检查是否已登录
        # ====================================================
        # 从Session里取登录信息，登录成功时我们把用户信息存在Session里
        info_dict = request.session.get("info")
        if not info_dict:  # 如果Session里没有登录信息
            return redirect("/login/")  # 跳回登录页

        # ====================================================
        # 第2步：从数据库加载当前用户对象
        # ====================================================
        admin_id = info_dict.get("id")  # 从Session里取用户ID
        admin_object = models.Admin.objects.filter(id=admin_id).first()

        # 如果用户不存在了（比如被删了），清除Session
        if not admin_object:
            request.session.clear()
            return redirect("/login/")

        # 把用户对象挂到request上，后续所有视图都能直接用request.admin_object
        # 这是个技巧：不用每个视图都重新查一次数据库
        request.admin_object = admin_object

        # ====================================================
        # 第3步：预加载用户的角色和权限（ORM性能优化！）
        # ====================================================
        # 为什么要重新查一次？
        # 因为上面只查了Admin表本身，没查关联的角色表和权限表
        # 如果后面循环时再查，会产生N+1查询问题

        # prefetch_related("roles__permissions") 的含义：
        # - 先查Admin表（1次SQL）
        # - 再查这个Admin关联的所有Role（1次SQL）
        # - 再查这些Role关联的所有Permission（1次SQL）
        # 总共3次SQL，而不是N+1次
        admin_object = models.Admin.objects.prefetch_related("roles__permissions").get(id=admin_id)
        request.admin_object = admin_object  # 重新挂回去，替换掉之前的

        # 收集用户所有权限的URL（用set去重）
        permission_urls = set()
        for role in admin_object.roles.all():
            for perm in role.permissions.all():
                if perm.url:
                    permission_urls.add(perm.url)
        request.permission_urls = permission_urls  # 挂到request上，视图里可以用

        # ====================================================
        # 第4步：识别用户角色类型（关键！）
        # ====================================================
        # 拿到用户所有角色的名称列表
        role_names = [role.title for role in admin_object.roles.all()]

        # 用三个布尔值标记角色类型，挂到request上
        # 后续所有视图、所有模板都能直接用这三个变量判断权限
        # 这就是为什么模板里能写 {% if request.is_super_admin %}
        request.is_super_admin = "超级管理员" in role_names  # 是否超级管理员
        request.is_dept_admin = "部门管理员" in role_names  # 是否部门管理员
        request.is_employee = "普通员工" in role_names      # 是否普通员工

        # ====================================================
        # 第5步：根据角色做权限拦截
        # ====================================================

        # 超级管理员：全部放行，什么都能看
        if request.is_super_admin:
            return  # 直接放行

        current_url = request.path_info  # 当前请求的URL路径

        # 部门管理员和普通员工都不能访问管理员管理页面
        # 也就是 /admin/ 开头的所有URL都拦截
        if current_url.startswith("/admin/"):
            return redirect("/notice/list/")  # 跳到公告页

        # 如果是普通员工，只能看，不能改
        if request.is_employee:
            # 普通员工不能访问的写操作URL（新增、修改、删除）
            # 说明：普通员工可进入 AI 助手做通用对话与制度问答；
            #       招聘 JD 生成在中间件层拦截，数据点评在视图层按角色拦截。
            forbidden_prefixes = [
                "/task/ajax",
                "/depart/add",      # 不能新增部门
                "/depart/multi",    # 不能批量导入部门
                "/user/add",        # 不能新增员工
                "/attendance/add",  # 不能录入考勤
                "/salary/add",      # 不能录入薪资
                "/notice/add",      # 不能发布公告
                "/notice/ai_generate",  # 不能使用 AI 生成公告
                "/ai/jd/",          # 不能使用 AI 招聘 JD 生成
            ]

            # 用正则表达式拦截编辑和删除（带数字ID的URL）
            # 比如 /user/5/edit/、/depart/3/delete/ 这种
            import re
            if re.match(r'^/user/\d+/(edit|delete)/', current_url):
                return redirect("/notice/list/")
            if re.match(r'^/depart/\d+/(edit|delete)/', current_url):
                return redirect("/notice/list/")

            # 遍历所有禁止的前缀，匹配到就拦截
            for prefix in forbidden_prefixes:
                if current_url.startswith(prefix):
                    return redirect("/notice/list/")

        # 部门管理员：能看能改，但是只能改本部门的数据（数据层面的过滤在视图里做）
        # 中间件只管"能不能进这个页面"，视图里管"能看到哪些数据"
        return  # 放行
