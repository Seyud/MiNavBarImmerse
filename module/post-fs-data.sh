MODDIR=${0%/*}
CUSTOM_FILE="$MODDIR/immerse_rules.xml"
TARGET_FILE="/data/system/cloudFeature_navigation_bar_immersive_rules_list.xml"

if [ ! -f "${TARGET_FILE}.bak" ]; then
    cp "$TARGET_FILE" "${TARGET_FILE}.bak"
fi

cp -f "$CUSTOM_FILE" "$TARGET_FILE"

chmod 600 "$TARGET_FILE"
chown system:system "$TARGET_FILE"
