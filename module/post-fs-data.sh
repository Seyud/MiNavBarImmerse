#!/system/bin/sh

MODDIR=${0%/*}
CUSTOM_FILE="$MODDIR/immerse_rules.xml"
TARGET_FILE="/data/system/cloudFeature_navigation_bar_immersive_rules_list.xml"
BACKUP_FILE="${TARGET_FILE}.bak"

echo "正在应用 MiNavBarImmerse 配置文件..."

# 检查自定义文件是否存在
if [ ! -f "$CUSTOM_FILE" ]; then
    echo "错误: 自定义规则文件不存在: $CUSTOM_FILE"
    echo "请确保模块正确安装！"
    exit 1
fi

# 检查目标文件是否存在
if [ ! -f "$TARGET_FILE" ]; then
    echo "目标文件不存在: $TARGET_FILE"
    echo "正在检查系统版本..."
    
    # 读取系统版本号
    VERSION_INCREMENTAL=$(getprop ro.build.version.incremental 2>/dev/null)
    
    if [ -z "$VERSION_INCREMENTAL" ]; then
        echo "错误: 无法获取系统版本号！"
        exit 1
    fi
    
    echo "检测到系统版本: $VERSION_INCREMENTAL"
    
    CLEAN_VERSION=$(echo "$VERSION_INCREMENTAL" | sed 's/[^0-9.]*//g')
    VERSION_CORE=$(echo "$CLEAN_VERSION" | cut -d. -f1-3)
    echo "提取结果: $VERSION_CORE"
    
    if [ -z "$VERSION_CORE" ] || [ "$VERSION_CORE" = "$VERSION_INCREMENTAL" ]; then
        echo "错误: 无法解析系统版本号格式！"
        echo "原始版本: $VERSION_INCREMENTAL"
        exit 1
    fi
    
    echo "解析到的版本号: $VERSION_CORE"
    
    MAJOR=$(echo "$VERSION_CORE" | cut -d. -f1)
    PATCH=$(echo "$VERSION_CORE" | cut -d. -f3)
    
    # 检查版本是否符合要求（2.0.200及以上）
    if [ -z "$MAJOR" ] || [ -z "$PATCH" ]; then
        echo "错误: 无法完整解析版本号！"
        exit 1
    elif [ "$MAJOR" -ge 3 ]; then
        echo "系统版本符合要求！"
    elif [ "$MAJOR" -lt 2 ]; then
        echo "错误: 系统版本过低（需要 2.0.200 或更高版本）"
        echo "当前版本: $VERSION_CORE"
        echo "模块不支持当前系统版本！"
        exit 1
    elif [ "$MAJOR" -eq 2 ]; then
        if [ "$PATCH" -lt 200 ]; then
            echo "错误: 系统版本过低（需要 2.0.200 或更高版本）"
            echo "当前版本: $VERSION_CORE"
            echo "模块不支持当前系统版本！"
            exit 1
        else
            echo "系统版本符合要求！"
        fi
    else
        echo "系统版本符合要求！"
    fi
    
    echo "开始创建目标文件..."
else
    # 目标文件存在时的备份逻辑
    if [ ! -f "$BACKUP_FILE" ]; then
        echo "正在备份原配置文件..."
        if cp "$TARGET_FILE" "$BACKUP_FILE"; then
            echo "备份成功创建: $BACKUP_FILE"
            # 设置备份文件权限与原始文件相同
            chmod 600 "$BACKUP_FILE"
            chown system:system "$BACKUP_FILE"
        else
            echo "备份失败，无法创建备份文件！"
            exit 1
        fi
    else
        echo "备份文件已存在，跳过备份步骤！"
    fi
fi

# 应用自定义规则
echo "正在替换配置文件..."
if cp -f "$CUSTOM_FILE" "$TARGET_FILE"; then
    echo "配置文件替换成功！"
else
    echo "配置文件替换失败！"
    exit 1
fi

# 设置正确权限
chmod 600 "$TARGET_FILE"
chown system:system "$TARGET_FILE"

echo "MiNavBarImmerse 配置已成功应用！"
echo "需要重启系统才能使更改生效！"