print("本程序没有经过实物测试如果有任何问题请联系qq:1936219518")
print("")
import asyncio
import struct
from bleak import BleakScanner, BleakClient
from bleak.exc import BleakError

# 设备信息
TARGET_NAME = "47L124000"
SERVICE_UUID = "0000180c-0000-1000-8000-00805f9b34fb"
CHAR_WRITE_UUID = "0000150a-0000-1000-8000-00805f9b34fb"   # 写特征
CHAR_NOTIFY_UUID = "0000150b-0000-1000-8000-00805f9b34fb"  # 通知特征

# 重置气压指令 (66 指令，12字节)
RESET_PRESSURE_CMD = bytes.fromhex("660000000000000000000002")

# 开启气压上报指令 (B0 指令，17字节)
START_REPORT_CMD = bytes.fromhex("B001D064" + "00" * 13)   # 指示灯颜色 01，启动上报 D0，固定 64

def parse_pressure(data: bytearray) -> float:
    """解析气压数据，返回气压值（kPa）"""
    if len(data) < 11:
        return None
    # 气压值位于第9、10字节（小端序有符号短整型）
    pressure_bytes = data[9:11]
    raw = struct.unpack("<h", pressure_bytes)[0]
    return raw / 100.0

async def notification_handler(sender, data: bytearray):
    """气压通知回调"""
    pressure = parse_pressure(data)
    if pressure is not None:
        print(f"实时气压: {pressure:.2f} kPa")

async def check_bluetooth_available():
    """检查蓝牙是否可用"""
    try:
        await BleakScanner.discover(timeout=2.0)
    except BleakError as e:
        raise RuntimeError("蓝牙未开启或不可用，请开启蓝牙后重试。") from e
    except Exception as e:
        raise RuntimeError(f"蓝牙检查失败: {e}") from e

async def main():
    # 1. 检查蓝牙状态
    print("正在检查蓝牙状态...")
    try:
        await check_bluetooth_available()
    except RuntimeError as e:
        print(f"错误: {e}")
        return
    print("蓝牙状态正常。")

    # 2. 扫描设备
    print("正在扫描设备...")
    device = await BleakScanner.find_device_by_name(TARGET_NAME, timeout=10.0)
    if device is None:
        print(f"未找到设备 {TARGET_NAME}")
        return

    print(f"找到设备: {device.name} ({device.address})")
    async with BleakClient(device) as client:
        print("已连接")

        # 3. 先重置气压读值
        print("正在重置气压值...")
        await client.write_gatt_char(CHAR_WRITE_UUID, RESET_PRESSURE_CMD, response=False)
        await asyncio.sleep(0.2)  # 稍作等待，确保指令执行

        # 4. 再开启气压上报
        print("正在开启气压上报...")
        await client.write_gatt_char(CHAR_WRITE_UUID, START_REPORT_CMD, response=False)
        await asyncio.sleep(0.2)

        # 5. 启用通知特征
        await client.start_notify(CHAR_NOTIFY_UUID, notification_handler)
        print("已开启气压通知，实时显示数据（按 Ctrl+C 停止）")

        try:
            while True:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            print("\n停止接收。")

if __name__ == "__main__":
    asyncio.run(main())