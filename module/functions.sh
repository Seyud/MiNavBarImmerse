#!/system/bin/sh

# MODDIR 变量由调用脚本定义
CUSTOM_FILE="${MODDIR}/immerse_rules.xml"
TARGET_FILE="/data/system/cloudFeature_navigation_bar_immersive_rules_list.xml"
BACKUP_FILE="${TARGET_FILE}.bak"

# 检查系统版本是否符合要求
check_system_version() {
    echo "正在检查系统版本..."
    
    # 读取系统版本号
    VERSION_INCREMENTAL=$(getprop ro.build.version.incremental 2>/dev/null)
    
    if [ -z "$VERSION_INCREMENTAL" ]; then
        echo "错误: 无法获取系统版本号！"
        return 1
    fi
    
    echo "检测到系统版本: $VERSION_INCREMENTAL"
    
    CLEAN_VERSION=$(echo "$VERSION_INCREMENTAL" | sed 's/[^0-9.]*//g')
    VERSION_CORE=$(echo "$CLEAN_VERSION" | cut -d. -f1-3)
    echo "提取结果: $VERSION_CORE"
    
    if [ -z "$VERSION_CORE" ] || [ "$VERSION_CORE" = "$VERSION_INCREMENTAL" ]; then
        echo "错误: 无法解析系统版本号格式！"
        echo "原始版本: $VERSION_INCREMENTAL"
        return 1
    fi
    
    echo "解析到的版本号: $VERSION_CORE"
    
    MAJOR=$(echo "$VERSION_CORE" | cut -d. -f1)
    PATCH=$(echo "$VERSION_CORE" | cut -d. -f3)
    
    # 检查版本是否符合要求（2.0.200及以上）
    if [ -z "$MAJOR" ] || [ -z "$PATCH" ]; then
        echo "错误: 无法完整解析版本号！"
        return 1
    elif [ "$MAJOR" -ge 3 ]; then
        echo "系统版本符合要求！"
        return 0
    elif [ "$MAJOR" -lt 2 ]; then
        echo "错误: 系统版本过低（需要 2.0.200 或更高版本）"
        echo "当前版本: $VERSION_CORE"
        echo "模块不支持当前系统版本！"
        return 1
    elif [ "$MAJOR" -eq 2 ]; then
        if [ "$PATCH" -lt 200 ]; then
            echo "错误: 系统版本过低（需要 2.0.200 或更高版本）"
            echo "当前版本: $VERSION_CORE"
            echo "模块不支持当前系统版本！"
            return 1
        else
            echo "系统版本符合要求！"
            return 0
        fi
    else
        echo "系统版本符合要求！"
        return 0
    fi
}

# 备份原始配置文件
backup_config() {
    if [ ! -f "$BACKUP_FILE" ]; then
        echo "正在备份原配置文件..."
        if cp "$TARGET_FILE" "$BACKUP_FILE"; then
            echo "备份成功创建: $BACKUP_FILE"
            # 设置备份文件权限与原始文件相同
            chmod 600 "$BACKUP_FILE"
            chown system:system "$BACKUP_FILE"
            return 0
        else
            return 1
        fi
    else
        echo "备份文件已存在，跳过备份步骤！"
        return 0
    fi
}

# 应用自定义配置
apply_custom_config() {
    echo "正在替换配置文件..."
    if cp -f "$CUSTOM_FILE" "$TARGET_FILE"; then
        echo "配置文件替换成功！"
        
        # 设置正确权限
        chmod 600 "$TARGET_FILE"
        chown system:system "$TARGET_FILE"
        
        return 0
    else
        echo "配置文件替换失败！"
        return 1
    fi
}

# 检查文件是否存在
check_files_exist() {
    if [ ! -f "$CUSTOM_FILE" ]; then
        echo "错误: 自定义配置文件不存在: $CUSTOM_FILE"
        echo "请确保模块完整！"
        return 1
    fi
    return 0
}

# 恢复备份配置
restore_backup() {
    if [ -f "$BACKUP_FILE" ]; then
        echo "找到备份文件，正在恢复..."
        
        if cp -f "$BACKUP_FILE" "$TARGET_FILE"; then
            echo "已成功恢复原始文件！"
            
            # 删除备份文件
            rm -f "$BACKUP_FILE"
            echo "已删除备份文件！"
        else
            echo "恢复文件失败！"
        fi
    else
        echo "未找到备份文件，跳过恢复！"
    fi
}

# 还原文件权限
restore_permissions() {
    if [ -f "$TARGET_FILE" ]; then
        echo "正在还原目标文件权限..."
        chmod 600 "$TARGET_FILE"
        chown system:system "$TARGET_FILE"
        echo "已还原文件权限！"
    fi
}