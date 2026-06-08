print("本程序没有经过实物测试如果有任何问题请联系qq:1936219518")
print("")
import asyncio
import sys
from bleak import BleakScanner, BleakClient, BleakError

# 设备名称（根据文档）
DEVICE_NAME = "47L124000"
# 服务与特征 UUID（基于文档提供的基础 UUID）
SERVICE_UUID = "0000180c-0000-1000-8000-00805f9b34fb"
CHAR_WRITE_UUID = "0000150a-0000-1000-8000-00805f9b34fb"  # 写入指令
CHAR_NOTIFY_UUID = "0000150b-0000-1000-8000-00805f9b34fb"  # 接收数据

# B0 指令：开启气压主动上报
# 格式: 0xB0 + 0x01(指示灯颜色) + 0xD0(启动上报) + 0x64(固定) + 13 字节 0x00
B0_CMD = bytes([0xB0, 0x01, 0xD0, 0x64] + [0x00] * 13)


def parse_pressure(data: bytes) -> float | None:
    """
    从 17 字节的 D0 消息中提取气压值。
    文档示例中气压字段位于消息的第 9、10 字节（索引 8、9，substring(18,22)）。
    小端序 int16，除以 100 得到 kPa。
    """
    if len(data) >= 11 and data[0] == 0xD0:
        # 取索引 9,10 两个字节
        pressure_bytes = data[9:11]
        value = int.from_bytes(pressure_bytes, byteorder="little", signed=True) / 100.0
        return value
    return None


def notification_handler(sender, data: bytes):
    """处理来自 0x150B 的通知数据"""
    pressure = parse_pressure(data)
    if pressure is not None:
        print(f"气压值: {pressure:.2f} kPa")


async def main():
    # 1. 扫描设备，若蓝牙未开启会抛出异常
    print("正在扫描蓝牙设备……")
    try:
        device = await BleakScanner.find_device_by_name(DEVICE_NAME, timeout=10.0)
    except BleakError as e:
        print(f"蓝牙错误: {e}")
        print("请确认蓝牙适配器已开启，并且系统蓝牙功能正常。")
        return
    except Exception as e:
        # 某些系统可能抛出 OSError 等，也按蓝牙未开启处理
        if "bluetooth" in str(e).lower() or "adapter" in str(e).lower():
            print("蓝牙适配器未开启，请先打开蓝牙。")
        else:
            print(f"扫描时发生错误: {e}")
        return

    if device is None:
        print(f"未找到设备 '{DEVICE_NAME}'。请检查：")
        print("  - 设备是否已开机；")
        print("  - 蓝牙图标是否为黄色（连按 5 次开机键可进入可被发现状态）；")
        print("  - 设备是否在有效范围内。")
        return

    print(f"发现设备: {device.name} ({device.address})")

    # 2. 连接设备并订阅通知、发送指令
    try:
        async with BleakClient(device) as client:
            print("已连接，正在监听气压数据……")

            # 订阅 0x150B 通知（必须先监听再发指令）
            await client.start_notify(CHAR_NOTIFY_UUID, notification_handler)
            print("已开启通知监听。")

            # 发送 B0 指令，启动气压上报（写 0x150A 特征）
            # 文档未明确是否需要 response，此处先尝试无响应写入
            await client.write_gatt_char(CHAR_WRITE_UUID, B0_CMD, response=False)
            print("已发送 B0 启动指令，等待气压数据……")

            # 持续运行，直到用户按下 Ctrl+C
            try:
                while True:
                    await asyncio.sleep(1)
            except KeyboardInterrupt:
                print("\n用户中断，正在退出……")

    except BleakError as e:
        print(f"连接或通信错误: {e}")
    except Exception as e:
        print(f"未知错误: {e}")


if __name__ == "__main__":
    # Windows 下需要设置事件循环策略（Python 3.8+）
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    try:
        asyncio.run(main())
    except Exception as e:
        print(f"\n程序发生未预期的错误: {e}")
    finally:
        # 保留窗口，等待用户按键后退出
        input("\n按回车键退出...")