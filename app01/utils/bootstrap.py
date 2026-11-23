# ============================================================
# 导入模块
# ============================================================
from django import forms


class BootStrap:
    """
    公共样式混入类（Mixin）：统一给表单字段加 form-control 样式和 placeholder。

    bootstrap_exclude_fields：需要排除样式的字段名列表（如文件上传框 img/image），
    被排除的字段不会被套上 form-control，保留浏览器原生文件选择框外观。
    """
    bootstrap_exclude_fields = []

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # 循环表单中的所有字段，给每个字段的插件设置样式
        for name, field in self.fields.items():
            # 排除字段（文件上传框等）不套 form-control
            if name in self.bootstrap_exclude_fields:
                continue
            # 字段中有属性，保留原来的属性；没有属性，才增加
            if field.widget.attrs:
                field.widget.attrs["class"] = "form-control"
                field.widget.attrs["placeholder"] = field.label
            else:
                field.widget.attrs = {
                    "class": "form-control",
                    "placeholder": field.label,
                }


class BootStrapForm(BootStrap, forms.Form):
    """普通 Form 基类：复用 Bootstrap 样式混入"""
    pass


class BootStrapModelForm(BootStrap, forms.ModelForm):
    """ModelForm 基类：复用 Bootstrap 样式混入"""
    pass
