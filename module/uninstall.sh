#!/system/bin/sh

MODDIR=${0%/*}

# 导入函数库
. "$MODDIR/functions.sh"

echo "正在卸载 MiNavBarImmerse..."

# 首先检查配置文件类型并设置正确的文件路径
if check_config_file; then
    echo "检测到配置类型: $CONFIG_TYPE"
    echo "目标文件: $TARGET_FILE"
    echo "备份文件: $BACKUP_FILE"

    # 恢复备份
    restore_backup

    # 还原权限
    restore_permissions
else
    echo "警告: 无法确定配置文件类型，尝试清理两种格式..."

    # 尝试清理JSON格式
    echo "尝试清理JSON格式配置..."
    CUSTOM_FILE="$CUSTOM_JSON_FILE"
    TARGET_FILE="$TARGET_JSON_FILE"
    BACKUP_FILE="$BACKUP_JSON_FILE"
    restore_backup
    restore_permissions

    # 尝试清理XML格式
    echo "尝试清理XML格式配置..."
    CUSTOM_FILE="$CUSTOM_XML_FILE"
    TARGET_FILE="$TARGET_XML_FILE"
    BACKUP_FILE="$BACKUP_XML_FILE"
    restore_backup
    restore_permissions
fi

echo "卸载完成！"