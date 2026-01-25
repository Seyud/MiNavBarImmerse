
def xml_to_dict(path:str):
    import xmltodict
    with open(path, "r",encoding="utf-8") as f:
        xml_data = f.read()
    return xmltodict.parse(xml_data)


def rgba_to_argb_int(rgba_hex: str) -> int:
    """
    将16进制RGBA颜色转换为ARGB格式的32位有符号整数

    参数:
        rgba_hex: RGBA格式的16进制颜色字符串，支持格式:
                  "#RRGGBBAA" (8位带#)
                  "RRGGBBAA"  (8位不带#)
                  "#RRGGBB"   (6位带#，自动添加FF透明度)
                  "RRGGBB"    (6位不带#，自动添加FF透明度)

    返回:
        ARGB格式的32位有符号整数
    """
    # 移除#号
    if rgba_hex.startswith('#'):
        rgba_hex = rgba_hex[1:]

    # 处理6位RGB，添加FF透明度
    if len(rgba_hex) == 6:
        rgba_hex = rgba_hex + 'FF'
    elif len(rgba_hex) != 8:
        raise ValueError(f"无效的颜色格式: {rgba_hex}，应为6位(RGB)或8位(RGBA)16进制")

    # 解析RGBA分量
    r = int(rgba_hex[0:2], 16)
    g = int(rgba_hex[2:4], 16)
    b = int(rgba_hex[4:6], 16)
    a = int(rgba_hex[6:8], 16)

    # 转换为ARGB整数 (A<<24 | R<<16 | G<<8 | B)
    argb_int = (a << 24) | (r << 16) | (g << 8) | b

    # 转换为有符号32位整数
    if argb_int > 0x7FFFFFFF:
        argb_int = argb_int - 0x100000000

    return argb_int


def argb_int_to_rgba(argb_int: int) -> str:
    """
    将ARGB格式的32位有符号整数转换为16进制RGBA字符串

    参数:
        argb_int: ARGB格式的32位有符号整数

    返回:
        RGBA格式的16进制颜色字符串 "#RRGGBBAA"
    """
    # 转换为无符号整数
    if argb_int < 0:
        argb_int = argb_int + 0x100000000

    # 提取ARGB分量
    a = (argb_int >> 24) & 0xFF
    r = (argb_int >> 16) & 0xFF
    g = (argb_int >> 8) & 0xFF
    b = argb_int & 0xFF

    # 格式化为16进制字符串
    return f"#{r:02X}{g:02X}{b:02X}{a:02X}"


def argb_int_to_rgb(argb_int: int) -> str:
    """
    将ARGB格式的32位有符号整数转换为16进制RGB字符串（忽略透明度）

    参数:
        argb_int: ARGB格式的32位有符号整数

    返回:
        RGB格式的16进制颜色字符串 "#RRGGBB"
    """
    rgba_hex = argb_int_to_rgba(argb_int)
    return rgba_hex[0:7]  # 移除最后两位透明度


def rgba_to_rgba_components(rgba_hex: str) -> tuple:
    """
    将16进制RGBA颜色分解为分量

    参数:
        rgba_hex: RGBA格式的16进制颜色字符串

    返回:
        (r, g, b, a) 分量元组，每个值范围0-255
    """
    if rgba_hex.startswith('#'):
        rgba_hex = rgba_hex[1:]

    if len(rgba_hex) == 6:
        rgba_hex = rgba_hex + 'FF'

    r = int(rgba_hex[0:2], 16)
    g = int(rgba_hex[2:4], 16)
    b = int(rgba_hex[4:6], 16)
    a = int(rgba_hex[6:8], 16)

    return r, g, b, a


def argb_int_to_components(argb_int: int) -> tuple:
    """
    将ARGB整数分解为分量

    参数:
        argb_int: ARGB格式的32位有符号整数

    返回:
        (a, r, g, b) 分量元组，每个值范围0-255
    """
    if argb_int < 0:
        argb_int = argb_int + 0x100000000

    a = (argb_int >> 24) & 0xFF
    r = (argb_int >> 16) & 0xFF
    g = (argb_int >> 8) & 0xFF
    b = argb_int & 0xFF

    return a, r, g, b
def is_number(s):
    """判断字符串是否可以转换为数字（整数或浮点数）"""
    try:
        int(s)
        return True
    except ValueError:
        return False