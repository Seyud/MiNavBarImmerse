#!/system/bin/sh

MODDIR=${0%/*
CUSTOM_FILE="$MODDIR/immerse_rules.xml"
TARGET_FILE="/data/system/cloudFeature_navigation_bar_immersive_rules_list.xml"

# 检查目标文件是否存在
if [ ! -f "$TARGET_FILE" ]; then
    echo "目标文件不存在: $TARGET_FILE"
    exit 1
fi

# 创建备份（如果不存在）
if [ ! -f "${TARGET_FILE}.bak" ]; then
    cp "$TARGET_FILE" "${TARGET_FILE}.bak" && \
    echo "已创建备份: ${TARGET_FILE}.bak"
fi

# 应用自定义规则
if cp -f "$CUSTOM_FILE" "$TARGET_FILE"; then
    echo "成功应用自定义规则"
    
    # 设置正确权限
    chmod 600 "$TARGET_FILE"
    chown system:system "$TARGET_FILE"
else
    echo "应用规则失败"
    exit 1
fi