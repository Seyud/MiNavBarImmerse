#!/system/bin/sh

MODDIR=$MODPATH

# 导入函数库
. "$MODDIR/functions.sh"

echo "正在初始化 MiNavBarImmerse 配置..."

# 检查配置文件类型并设置正确的文件路径
check_config_file || abort "检查配置文件失败"

echo "检测到配置类型: $CONFIG_TYPE"
echo "自定义文件: $CUSTOM_FILE"
echo "目标文件: $TARGET_FILE"

# 检查必要文件
check_files_exist || abort "检查必要文件失败"

# 先备份
echo "执行备份..."
backup_config || abort "备份配置文件失败"


# 应用配置
apply_custom_config || abort "应用配置文件失败"

echo "配置初始化完成"
echo "需要重启系统生效！"