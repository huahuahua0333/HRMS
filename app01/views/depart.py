from django.shortcuts import render, redirect
from app01 import models


def depart_list(request):
    """部门列表"""
    # prefetch_related 优化：一次性查出每个部门的员工，避免N+1查询
    queryset = models.Department.objects.prefetch_related('userinfo_set').all()
    total_employees = models.UserInfo.objects.count()
    return render(request, "depart_list.html", {
        "queryset": queryset,
        "total_employees": total_employees,
    })


def depart_add(request):
    """新建部门"""
    if request.method == "GET":
        return render(request, "depart_add.html")

    title = request.POST.get("title")
    if title:
        models.Department.objects.create(title=title)
    return redirect("/depart/list/")


def depart_edit(request, nid):
    """编辑部门"""
    row_object = models.Department.objects.filter(id=nid).first()
    if request.method == "GET":
        return render(request, "depart_edit.html", {"row_object": row_object})

    title = request.POST.get("title")
    models.Department.objects.filter(id=nid).update(title=title)
    return redirect("/depart/list/")


def depart_delete(request, nid):
    """删除部门"""
    models.Department.objects.filter(id=nid).delete()
    return redirect("/depart/list/")

def depart_multi(request):
    """批量导入部门（Excel 文件，第一列为部门名称，从第 2 行开始）"""
    # 仅超级管理员可批量导入部门，其余角色直接返回列表页
    if not getattr(request, "is_super_admin", False):
        return redirect("/depart/list/")

    from openpyxl import load_workbook

    # 1.获取用户上传的文件对象；未选择文件时直接返回
    file_object = request.FILES.get("exc")
    if not file_object:
        return redirect("/depart/list/")

    # 2.对象传递给 openpyxl，由 openpyxl 读取文件内容
    wb = load_workbook(file_object)
    sheet = wb.worksheets[0]

    # 3.逐行读取第一列，去重后入库；跳过空行与空白名称
    for row in sheet.iter_rows(min_row=2):
        text = row[0].value
        if text is None:
            continue
        text = str(text).strip()
        if not text:
            continue
        if not models.Department.objects.filter(title=text).exists():
            models.Department.objects.create(title=text)

    return redirect("/depart/list/")