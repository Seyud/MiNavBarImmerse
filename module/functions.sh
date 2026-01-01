#!/system/bin/sh

# MODDIR 变量由调用脚本定义
CUSTOM_JSON_FILE="${MODDIR}/immerse_rules.json"
TARGET_JSON_FILE="/data/system/cloudFeature_navigation_bar_immersive_rules_list.json"
SYSTEM_JSON_FILE="/system_ext/etc/nbi/navigation_bar_immersive_rules_list.json"
BACKUP_JSON_FILE="${TARGET_JSON_FILE}.bak"

CUSTOM_XML_FILE="${MODDIR}/immerse_rules.xml"
TARGET_XML_FILE="/data/system/cloudFeature_navigation_bar_immersive_rules_list.xml"
SYSTEM_XML_FILE="/system_ext/etc/nbi/navigation_bar_immersive_rules_list.xml"
BACKUP_XML_FILE="${TARGET_XML_FILE}.bak"

# 检查配置文件类型
check_config_file() {
    echo "正在检查配置文件..."

    # 检查系统配置文件类型
    if [ -f "$SYSTEM_JSON_FILE" ]; then
        echo "检测到系统使用JSON格式配置文件"
        CUSTOM_FILE="$CUSTOM_JSON_FILE"
        TARGET_FILE="$TARGET_JSON_FILE"
        BACKUP_FILE="$BACKUP_JSON_FILE"
        CONFIG_TYPE="JSON"
    elif [ -f "$SYSTEM_XML_FILE" ]; then
        echo "检测到系统使用XML格式配置文件"
        CUSTOM_FILE="$CUSTOM_XML_FILE"
        TARGET_FILE="$TARGET_XML_FILE"
        BACKUP_FILE="$BACKUP_XML_FILE"
        CONFIG_TYPE="XML"
    else
        echo "错误: 未找到系统配置文件！"
        echo "检查路径:"
        echo "  $SYSTEM_JSON_FILE"
        echo "  $SYSTEM_XML_FILE"
        return 1
    fi

    echo "使用配置文件: $CUSTOM_FILE"
    echo "目标文件: $TARGET_FILE"
    echo "备份文件: $BACKUP_FILE"
    echo "配置类型: $CONFIG_TYPE"

    return 0
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