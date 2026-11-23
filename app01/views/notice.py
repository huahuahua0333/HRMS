# ============================================================
# 导入模块
# ============================================================
from django.shortcuts import render, redirect
from app01 import models
from app01.forms import NoticeModelForm
from app01.utils.pagination import Pagination


# ============================================================
# 公告列表
# URL: /notice/list/
# ============================================================
def notice_list(request):
    """公告列表：置顶优先，支持搜索"""
    search_title = request.GET.get("title", "")
    # select_related 优化：一次性查出关联的publisher，避免N+1查询
    queryset = models.Notice.objects.select_related('publisher').all()
    if search_title:
        queryset = queryset.filter(title__icontains=search_title)
    # 置顶的排前面
    queryset = queryset.order_by("-is_top", "-publish_time")

    page_object = Pagination(request, queryset)
    context = {
        "queryset": page_object.page_queryset,
        "page_string": page_object.html(),
        "search_title": search_title,
    }
    return render(request, "notice_list.html", context)


# ============================================================
# 新建公告
# URL: /notice/add/
# ============================================================
def notice_add(request):
    """新建公告"""
    if request.method == "GET":
        form = NoticeModelForm()
        return render(request, "change.html", {"form": form, "title": "发布公告", "ai_enabled": True})

    form = NoticeModelForm(data=request.POST)
    if form.is_valid():
        # 自动设置发布人
        form.instance.publisher_id = request.session["info"]["id"]
        form.save()
        return redirect("/notice/list/")
    return render(request, "change.html", {"form": form, "title": "发布公告", "ai_enabled": True})


# ============================================================
# 切换公告置顶状态
# URL: /notice/<int:nid>/toggle_top/
# ============================================================
def notice_toggle_top(request, nid):
    """切换公告置顶/取消置顶"""
    notice_obj = models.Notice.objects.filter(id=nid).first()
    if notice_obj:
        notice_obj.is_top = not notice_obj.is_top  # 取反
        notice_obj.save()
    return redirect("/notice/list/")
