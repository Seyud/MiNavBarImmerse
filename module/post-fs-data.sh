#!/system/bin/sh

MODDIR=${0%/*}

# 导入函数库
. "$MODDIR/functions.sh"

echo "正在应用 MiNavBarImmerse 配置文件..."

# 检查必要文件
check_files_exist || exit 1

# 应用配置（防止被云控覆盖）
apply_custom_config || exit 1

echo "MiNavBarImmerse 配置已成功应用！"