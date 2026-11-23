# ============================================================
# 数据迁移：初始化公司制度条文（供 AI 制度知识库问答引用）
# 说明：使用 get_or_create，重复执行迁移不会产生重复数据
# ============================================================
from django.db import migrations


# (制度标题, 类别编码, 制度正文)
POLICIES = [
    (
        "考勤管理制度",
        1,
        "公司标准工作时间为 9:00—18:00。9:00 以后到岗记为迟到，18:00 以前离岗记为早退；"
        "当日未打卡且无请假记录记为缺勤；迟到或早退每次扣款 50 元；"
        "经批准的休假在考勤记录中标注为“请假”。",
    ),
    (
        "请假休假制度",
        2,
        "事假须提前 1 个工作日提交申请并经部门负责人审批；病假需提供医院证明；"
        "年假按工龄核定，工作满 1 年享 5 天；病假期间按基本工资的 80% 发放；"
        "未经批准不到岗按缺勤处理。",
    ),
    (
        "薪酬福利制度",
        3,
        "每月 15 日发放上月工资；实发工资 = 基本工资 + 奖金 − 扣款；"
        "7 月至 9 月发放高温补贴，每月 200 元；公司依法缴纳五险一金；"
        "薪资属于个人隐私，不得相互打探或泄露。",
    ),
    (
        "奖惩制度",
        4,
        "年度考核优秀者给予奖金并通报表扬；违纪视情节给予警告、记过处理；"
        "连续缺勤按旷工论处，情节严重者解除劳动关系；任务审批被退回的，须在限期内重做。",
    ),
    (
        "办公规范制度",
        5,
        "上下班须本人打卡，不得代打卡；爱护办公设备，遵守公司保密规定；"
        "着装整洁，工作时间保持在岗；各类会议与培训按通知准时参加。",
    ),
]


def seed_policies(apps, schema_editor):
    Policy = apps.get_model("app01", "Policy")
    for title, category, content in POLICIES:
        Policy.objects.get_or_create(
            title=title,
            defaults={"category": category, "content": content, "is_active": True},
        )


def unseed_policies(apps, schema_editor):
    Policy = apps.get_model("app01", "Policy")
    titles = [item[0] for item in POLICIES]
    Policy.objects.filter(title__in=titles).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("app01", "0011_policy"),
    ]

    operations = [
        migrations.RunPython(seed_policies, unseed_policies),
    ]
