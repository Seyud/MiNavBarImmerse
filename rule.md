# 适配方式

模块通过替换/data/system/cloudFeature_navigation_bar_immersive_rules_list.xml生效，规则位于[immerse_rules.xml](/module/immerse_rules.xml)，模块内的文件是基于源文件修改得来的。  


NBIRules标签内为应用列表，格式为：
`<package name="应用包名" enable="true" activityRule="规则列表" disableVersionCode="818"/>`  
其中disableVersionCode可以不填。   

其中，规则列表格式为：  
`规则1,规则2……`  

规则格式为：  
`Activity ID:适配方式`  
- 特殊地，可以使用`*`指代该应用的全部Activity。  

适配方式用数字表示，规则如下：
- `0`：应用默认样式（大概率是）  
- `1:颜色`：小白条背景为指定颜色（ARGB格式），颜色使用有符号32位整数表示。  
  - `1`：不填写颜色，可能是无效、透明或者黑色？  
  - `1:0`：透明（0x00000000）。  
  - `1:-16777216`：不透明黑色（0xFF000000）。  
  - `1:-1`：不透明白色（0xFFFFFFFF）。  
- `2`：小白条悬浮显示在应用上方，可能会有遮挡。  

