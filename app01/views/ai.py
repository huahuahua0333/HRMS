# ============================================================
# 模块：AI 辅助功能视图
# 能力：
#   1. 公告 AI 生成正文（管理员）
#   2. 智能对话（所有登录角色，通用问答）
#   3. 制度知识库问答（所有登录角色，引用库内制度条文）
#   4. 数据智能点评（管理员，按角色范围注入数据快照）
#   5. 招聘 JD 生成（管理员）
# 数据隔离：超管全公司 / 部门管理员本部门 / 普通员工本人
# ============================================================
import json

from django.shortcuts import render, HttpResponse
from django.db.models import Count, Sum

from app01 import models
from app01.utils import ai_client


# ============================================================
# 权限与上下文辅助
# ============================================================
def _json_response(data):
    """统一返回 JSON 响应。"""
    return HttpResponse(json.dumps(data), content_type="application/json")


def _is_forbidden_employee(request):
    """普通员工判定（用于公告 AI 生成等仅限管理员的功能）。"""
    return hasattr(request, "is_employee") and request.is_employee


def _is_admin_ai(request):
    """招聘 JD 生成、数据智能点评仅管理员（超管 / 部门管理员）可用。"""
    return bool(getattr(request, "is_super_admin", False)
                or getattr(request, "is_dept_admin", False))


def _role_label(request):
    if request.is_super_admin:
        return "超级管理员"
    if request.is_dept_admin:
        return "部门管理员"
    return "普通员工"


def _filtered_qs(request, model_name):
    """
    按角色过滤业务查询集，与各列表页的隔离规则保持一致：
      - 部门管理员：本部门
      - 普通员工：仅本人
      - 超级管理员：全部
    """
    qs_map = {
        "employee": models.UserInfo.objects.all(),
        "attendance": models.Attendance.objects.all(),
        "salary": models.Salary.objects.all(),
        "task": models.Task.objects.all(),
    }
    qs = qs_map[model_name]

    if getattr(request, "is_dept_admin", False) and request.admin_object.depart:
        if model_name == "employee":
            return qs.filter(depart=request.admin_object.depart)
        if model_name == "task":
            # 任务表负责人外键为 owner
            return qs.filter(owner__depart=request.admin_object.depart)
        return qs.filter(employee__depart=request.admin_object.depart)

    if getattr(request, "is_employee", False) and request.admin_object.employee:
        if model_name == "employee":
            # 员工档案表只返回本人记录
            return qs.filter(id=request.admin_object.employee.id)
        if model_name == "task":
            return qs.filter(owner_id=request.admin_object.employee.id)
        return qs.filter(employee_id=request.admin_object.employee.id)

    return qs


# ============================================================
# 制度上下文：读取库内启用的制度条文
# ============================================================
def _policy_context():
    policies = models.Policy.objects.filter(is_active=True).order_by("category", "id")
    if not policies:
        return "（系统暂未录入公司制度条文）"
    category_map = dict(models.Policy.category_choices)
    lines = []
    for policy in policies:
        category = category_map.get(policy.category, "其他")
        lines.append(f"《{policy.title}》（{category}）：{policy.content}")
    return "\n".join(lines)


# ============================================================
# 数据快照：按当前角色可见范围汇总考勤 / 薪资 / 任务
# ============================================================
def _data_snapshot(request):
    role = _role_label(request)

    if request.is_super_admin:
        scope = "全公司"
    elif request.is_dept_admin:
        dept_name = request.admin_object.depart.title if request.admin_object.depart else "未绑定部门"
        scope = f"本部门（{dept_name}）"
    else:
        scope = "本人（仅限当前登录员工的个人数据）"

    lines = [f"当前登录角色：{role}；可查看数据范围：{scope}。"]

    emp_qs = _filtered_qs(request, "employee")
    att_qs = _filtered_qs(request, "attendance")
    sal_qs = _filtered_qs(request, "salary")
    task_qs = _filtered_qs(request, "task")

    lines.append(f"员工人数：{emp_qs.count()} 人。")

    # 部门信息（按角色可见范围：超管看全公司部门，其余看所属部门）
    if request.is_super_admin:
        depts = models.Department.objects.annotate(
            emp_count=Count("userinfo")
        ).order_by("id")
        dept_desc = "、".join(f"{d.title}({d.emp_count}人)" for d in depts)
        lines.append(f"部门数量：{depts.count()} 个；部门分布：{dept_desc}。")
    elif request.is_dept_admin:
        lines.append(f"所属部门：{dept_name}。")
    else:
        emp_obj = request.admin_object.employee
        own_dept = emp_obj.depart.title if emp_obj and emp_obj.depart else "未分配部门"
        lines.append(f"所属部门：{own_dept}。")

    # 考勤状态分布
    status_map = {1: "按时", 2: "迟到", 3: "早退", 4: "缺勤", 5: "请假"}
    att_stats = att_qs.values("status").annotate(c=Count("id"))
    att_desc = "，".join(
        f"{status_map.get(s['status'], '其他')}{s['c']}条" for s in att_stats
    ) or "无考勤记录"
    lines.append(f"考勤分布：{att_desc}。")

    # 近期薪资（最新 3 个月合计）
    sal_months = sal_qs.values("month").annotate(total=Sum("total")).order_by("-month")[:3]
    if sal_months:
        sal_desc = "，".join(
            f"{m['month']} 实发合计 {float(m['total'] or 0):.2f} 元" for m in sal_months
        )
        lines.append(f"近期薪资：{sal_desc}。")
    else:
        lines.append("近期薪资：无记录。")

    # 任务状态分布
    task_map = {1: "待完成", 2: "待审批", 3: "已完成", 4: "已退回", 5: "已归档"}
    task_stats = task_qs.values("status").annotate(c=Count("id"))
    task_desc = "，".join(
        f"{task_map.get(t['status'], '其他')}{t['c']}项" for t in task_stats
    ) or "无任务记录"
    lines.append(f"任务分布：{task_desc}。")

    # 普通员工补充本人近期明细，便于回答个人相关问题
    if request.is_employee:
        recent_att = att_qs.order_by("-date")[:5]
        if recent_att:
            att_detail = "；".join(
                f"{a.date} {status_map.get(a.status, '其他')}" for a in recent_att
            )
            lines.append(f"本人近期考勤：{att_detail}。")
        my_tasks = task_qs.all()[:5]
        if my_tasks:
            task_detail = "；".join(
                f"{t.title}（{task_map.get(t.status, '其他')}）" for t in my_tasks
            )
            lines.append(f"本人任务：{task_detail}。")

    return "\n".join(lines)


# ============================================================
# 公告 AI 生成正文（AJAX 接口）
# URL: /notice/ai_generate/
# ============================================================
def ai_notice_generate(request):
    """接收公告标题，调用 AI 生成正文，返回 JSON。"""
    if _is_forbidden_employee(request):
        return _json_response({"status": False, "msg": "无权限使用 AI 生成"})

    if request.method != "POST":
        return _json_response({"status": False, "msg": "请求方式错误"})

    title = request.POST.get("title", "").strip()
    points = request.POST.get("points", "").strip()

    if not title:
        return _json_response({"status": False, "msg": "请先填写公告标题"})

    ok, content = ai_client.generate_notice(title, points)
    if ok:
        return _json_response({"status": True, "content": content})
    return _json_response({"status": False, "msg": content})


# ============================================================
# AI 助手页面
# URL: /ai/assistant/
# ============================================================
def ai_assistant(request):
    """渲染 AI 助手对话页面，传管理员标记与制度清单控制标签显隐。"""
    policies = models.Policy.objects.filter(is_active=True).order_by("category", "id")
    return render(request, "ai_assistant.html", {
        "can_admin_ai": _is_admin_ai(request),
        "policies": policies,
    })


# ============================================================
# AI 统一对话（AJAX 接口）
# URL: /ai/assistant/chat/
# mode: chat 通用对话 / policy 制度问答 / review 数据点评
# ============================================================
def ai_assistant_chat(request):
    """接收问题与模式，按角色组装上下文后调用大模型，返回 JSON。"""
    if request.method != "POST":
        return _json_response({"status": False, "msg": "请求方式错误"})

    mode = request.POST.get("mode", "chat").strip()
    question = request.POST.get("question", "").strip()
    if not question:
        return _json_response({"status": False, "msg": "请输入问题"})

    # 数据智能点评仅管理员可用
    if mode == "review" and not _is_admin_ai(request):
        return _json_response({"status": False, "msg": "当前角色无权使用数据点评"})

    if mode == "policy":
        system_prompt = (
            "你是 HRMS 公司制度助手。只能依据下面提供的制度条文回答；"
            "条文未明确说明的内容，请如实告知“制度未作规定”，不要编造条款。\n"
            "【制度条文】\n" + _policy_context()
        )
    elif mode == "review":
        system_prompt = (
            "你是 HRMS 数据分析师。只能依据下面提供的数据快照作答，"
            "不要引用快照之外的人数、金额或考勤结论；请指出现象、可能原因与改进建议。\n"
            "【数据快照】\n" + _data_snapshot(request)
        )
    else:
        system_prompt = (
            "你是企业员工管理系统的内置助手。请用简洁中文回答与人事、考勤、薪资、公告、任务相关的问题；"
            "可依据下面【数据快照】回答当前登录角色可见范围内的数据问题，"
            "快照中没有的数字不要编造，也不要推测其他部门或他人的隐私数据。\n"
            "【数据快照】\n" + _data_snapshot(request)
        )

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": question},
    ]
    ok, answer = ai_client.chat(messages, temperature=0.7, max_tokens=800)
    if ok:
        return _json_response({"status": True, "answer": answer})
    return _json_response({"status": False, "msg": answer})


# ============================================================
# 招聘 JD 生成（AJAX 接口，仅管理员）
# URL: /ai/jd/
# ============================================================
def ai_jd_generate(request):
    """根据岗位名称生成招聘 JD，返回 JSON。"""
    if not _is_admin_ai(request):
        return _json_response({"status": False, "msg": "当前角色无权生成招聘 JD"})

    if request.method != "POST":
        return _json_response({"status": False, "msg": "请求方式错误"})

    role_name = request.POST.get("role", "").strip()
    if not role_name:
        return _json_response({"status": False, "msg": "请先填写岗位名称"})

    ok, content = ai_client.generate_jd(role_name)
    if ok:
        return _json_response({"status": True, "content": content})
    return _json_response({"status": False, "msg": content})
