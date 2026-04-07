# ESP32-P4 芯片版本 v3.2 ⼯程批送样说明

乐鑫科技推出的⾼性能 MCU AIoT SoC 芯⽚ ESP32-P4 芯片版本 v3.2 已经进⼊新⼀轮⼯程批送样阶段。我们⾮常感谢您对乐鑫及其产品的信任，也很荣幸能为您提供基于最新版本的⼯程样品，助⼒您的基础功能测试与固件开发⼯作。

v3.2 版本芯片修复了 v3.1 版本 Secure Download 功能缺陷，和 v3.1, v3.0 软件和硬件完全兼容。需要再次说明的是，v3.x 版本 (v3.0, v3.1, v3.2) 与 v1.x 版本（v1.0, v1.1, v1.2, v1.3）芯片软硬件均不兼容，芯片丝印从 "NRW16 或 NRW32" 变更为 "NRW16X 或 NRW32X" （详见附录 C）。为了确保您的开发顺利进行，我们特别梳理了以下关键注意事项，请您及工程团队务必知悉。

**A. v3.2 芯片版本，存在以下已知问题：**

1. esptool 不兼容：旧版本 esptool 需要升级到最新版本 (esptool commit：3f6cb598) 且配置 menuconfig > Serial flasher config > Disable download stub (default value) 禁用 stub ，以支持 ESP32-P4 v3.2 芯片版本烧录固件。该问题将在下一个 esptool 版本中修复，请关注 esptool 更新。更新 esptool，请在 ESP-IDF 环境中使用指令：

    `pip install git+https://github.com/espressif/esptool.git`

2. RTC_WDT 复位问题：若芯片未外接 32.768 kHz 晶振，请勿在软件中使能该晶振（默认软件未使能），否则可能因校准超时而触发 RTC 看门狗复位。该问题已在最新的 IDF 版本中修复，commit id：fa9f68c ，后续将在 ESP-IDF v5.5.5，v6.0.1 包含该修复。

**B. 从 v1.x 芯片版本升级到 v3.2 芯片版本的用户，请注意如下事项：**

1. 软件不兼容：v3.2 版本包含 50+ 项硬件及其寄存器变更（涵盖 ISP、CPU、L2MEM、MSPI、安全模块等），v1.x 旧版固件无法运行，请参阅第二页 附录 A 更新 ESP-IDF 和对应编译工具链，对工程进行重新编译。

2. 管脚变更 (Pin 54) ：Pin 54 定义已从 NC（未连接）变更为 VDD_HP 电源引脚。具体影响及设计建议请参阅 附录B。

3. DCDC 反馈分压电阻：对于 VDD_HP 电源外部所连接的 DCDC 电源芯片，请务必确认其外围的两颗 499 kΩ 反馈分压电阻和 22 pF 前馈电容上件。具体影响及设计建议请参阅 附录 B。

4. CPU 频率提升：CPU 频率限制已解除，当前样品支持 400 MHz 运行频率。

**C. 从 v3.1 升级到 v3.2 芯片版本的用户，请知悉：**

1. 安全功能修复：v3.2 芯片版本 Secure Download 问题已修复。

2. v3.2 芯片版本和 v3.0, v3.1 芯片版本，除以上 RTC_WDT 注意事项外，软件兼容，管脚无变化。

3. 送样说明在线版本可以通过扫描如下二维码访问或点击[链接](https://www.espressif.com.cn/sites/default/files/ae/ESP32-P4%20(Revision%20V3.2)%20Engineering%20Sample%20Notes_EN.pdf) 获取。

    ![QR 二维码](../static/esp32p4-chip-revision-v3.2-engineering-sample-notes_cn.png)

# 附录 A：ESP32-P4 开发说明  { .pdf-break-before }

目前 ESP-IDF 的 release/v5.5, release/v6.0 分支 (https://github.com/espressif/esp-idf) 已经支持 ESP32-P4 v3.2 芯片版本的大部分功能，我们建议您经常更新 ESP-IDF 分支以获取最新的功能支持和 bug 修复。

|  ESP-IDF 版本/分支    | 支持版本   |
|  ----  | ----  |
| release/v5.5   | v5.5.4 及以上  |
| release/v6.0   | v6.0 及以上  |

如果这是您初次使用 ESP-IDF, 建议您从 ESP32-P4 的软件开发环境和文档开始入手：

<https://docs.espressif.com/projects/esp-idf/en/latest/esp32p4/index.html>

**Notice:**

1. 请通过如下命令设定 ESP32-P4 开发项目：

    `idf.py set-target esp32p4`

2. 注意在使用当前的 ESP32-P4 v3.2 芯片版本前，请务必升级至以上 ESP-IDF 版本/分支。

3. 如遇到烧录问题，请在 ESP-IDF 环境中更新 esptool，使用指令：

    `pip install git+https://github.com/espressif/esptool.git`

# 附录 B：ESP32-P4 芯片管脚变更说明 { .pdf-break-before }

ESP32-P4 v3.x 芯片版本在管脚设计上与 v1.x 及之前版本存在差异：Pin 54 由原先的 NC（未连接）改为 VDD_HP 电源引脚。


- 对于尚未开始设计 PCB 的新项目：

    - 使用 v3.2 芯片版本时，请将新增的电源引脚 (Pin 54) 外部连接至 VDD_HP 电源，以获得最佳性能。

- 对于仍在使用基于 P4 v1.x 芯片版本设计的 PCB：

    - 该新增电源引脚 (Pin 54) 即使未外接 VDD_HP 电源，也不影响 v3.x 芯片版本的正常功能。但建议在后续 PCB 版本中补充该电源连接，以获得最佳性能。

    - 器件贴装调整：对于 VDD_HP 电源外部所连接的 DCDC 电源芯片，确保其外围的两颗 499 kΩ 反馈分压电阻必须上件，否则有芯片损坏风险。

    - 前馈电容：请见 C53 对应的前馈电容上件 22 pF。

![反馈分压电阻](../static/feedback-voltage-divider-resistors.png)

<div class="pdf-page-block" markdown="1">

**ESP32-P4 芯片管脚变更说明**

![ESP32-P4 Pin Change](../static/esp32p4-pin-change.jpeg)

</div>

# 附录 C：ESP32-P4 芯片丝印变更说明  { .pdf-break-before }

ESP32-P4 v3.x 芯片版本后，产品规格标识从 "NRW16 或 NRW32" 改为 "NRW16X 或 NRW32X"，增加了代表芯片升级的后缀字母 "X"。

![ESP32-P4 Chip Revision v3.x](../static/esp32p4-chip-revision-v3.x.jpeg)

![ESP32-P4 Chip Revision v1.x](../static/esp32p4-chip-revision-v1.x.png)
