#!/system/bin/sh

MODDIR=$MODPATH

# 导入函数库
. "$MODDIR/functions.sh"

echo "正在初始化 MiNavBarImmerse 配置..."

# 检查必要文件
check_files_exist || abort "检查必要文件失败"

if [ ! -f "$TARGET_FILE" ]; then
    # 目标文件不存在时检查系统版本
    check_system_version || abort "系统版本不符"
else
    # 目标文件存在时先备份
    backup_config || abort "备份配置文件失败"
fi

# 应用配置
apply_custom_config || abort "应用配置文件失败"

echo "配置初始化完成"
echo "需要重启系统生效！"