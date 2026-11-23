# ============================================================
# 导入模块
# ============================================================
import random                                                  # 随机数
from PIL import Image, ImageDraw, ImageFont, ImageFilter       # Pillow图片处理库
from django.shortcuts import HttpResponse                       # 返回图片响应


# ============================================================
# 生成图片验证码
# URL: /image/code/
# ============================================================
def check_code(request):
    """生成图片验证码：随机字母+干扰点/线，存session"""
    width = 120        # 图片宽度
    height = 30        # 图片高度
    char_length = 5    # 验证码字符个数

    # ---- 辅助函数：随机颜色（RGB） ----
    def rndColor():
        return (random.randint(0, 255), random.randint(10, 255), random.randint(64, 255))

    # ---- 辅助函数：随机大写字母（A-Z） ----
    def rndChar():
        return chr(random.randint(65, 90))

    # ---- 第1步：创建白色画布 ----
    img = Image.new(mode='RGB', size=(width, height), color=(255, 255, 255))
    draw = ImageDraw.Draw(img, mode='RGB')

    # ---- 第2步：写5个随机字母 ----
    font = ImageFont.truetype('C:/Windows/Fonts/arial.ttf', 20)
    code = []
    for i in range(char_length):
        char = rndChar()
        code.append(char)                                        # 记录验证码字符串
        h = random.randint(0, 4)                                  # 每个字符随机上下偏移
        draw.text([i * width / char_length, h], char, font=font, fill=rndColor())

    # ---- 第3步：画干扰点（40个随机点） ----
    for i in range(40):
        draw.point([random.randint(0, width), random.randint(0, height)], fill=rndColor())

    # ---- 第4步：画干扰小圆圈（40个） ----
    for i in range(40):
        draw.point([random.randint(0, width), random.randint(0, height)], fill=rndColor())
        x = random.randint(0, width)
        y = random.randint(0, height)
        draw.arc((x, y, x + 4, y + 4), 0, 90, fill=rndColor())

    # ---- 第5步：画干扰线（5条随机直线） ----
    for i in range(5):
        x1 = random.randint(0, width)
        y1 = random.randint(0, height)
        x2 = random.randint(0, width)
        y2 = random.randint(0, height)
        draw.line((x1, y1, x2, y2), fill=rndColor())

    # 增强图片边缘
    img = img.filter(ImageFilter.EDGE_ENHANCE_MORE)

    # ---- 第6步：验证码字符串存到session，登录时比对 ----
    request.session['image_code'] = ''.join(code)

    # ---- 第7步：返回图片，加不缓存头（防止浏览器缓存旧验证码） ----
    import io
    f = io.BytesIO()
    img.save(f, format='png')
    response = HttpResponse(f.getvalue(), content_type='image/png')
    response['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    response['Pragma'] = 'no-cache'
    response['Expires'] = '0'
    return response
