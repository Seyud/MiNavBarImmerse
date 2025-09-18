#!/system/bin/sh

MODDIR=${0%/*}

# 导入函数库
. "$MODDIR/functions.sh"

echo "正在卸载 MiNavBarImmerse..."

# 恢复备份
restore_backup

# 还原权限
restore_permissions

echo "卸载完成！"