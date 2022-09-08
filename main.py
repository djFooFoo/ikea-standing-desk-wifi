import struct
from typing import List

import fastapi
from bleak import BleakScanner, BleakClient
from bleak.backends.device import BLEDevice

UUID_DEVICE_NAME = '00002a00-0000-1000-8000-00805f9b34fb'
UUID_HEIGHT_AND_SPEED = '99fa0021-338a-1024-8a49-009c0215f78a'
UUID_COMMAND = "99fa0002-338a-1024-8a49-009c0215f78a"

MIN_HEIGHT_DESK = 620
MAX_HEIGHT_DESK = 1270


async def list_devices():
    devices: List[BLEDevice] = await BleakScanner.discover()
    return devices


async def get_desk():
    devices = await list_devices()
    desk_devices = (device for device in devices if device.name and 'Desk' in device.name)
    desk = next(desk_devices, None)
    return desk


async def calculate_height_in_mm(height):
    return height / 10 + MIN_HEIGHT_DESK


async def read_height_and_speed(client):
    return struct.unpack("<Hh", await client.read_gatt_char(UUID_HEIGHT_AND_SPEED, use_cached=False))


async def move_up(client):
    return await client.write_gatt_char(UUID_COMMAND, bytearray([0x47, 0x00]))


async def move_down(client):
    return await client.write_gatt_char(UUID_COMMAND, bytearray([0x46, 0x00]))


async def stop(client):
    return await client.write_gatt_char(UUID_COMMAND, bytearray([0xFF, 0x00]))


async def move_to_desired_height(client, desired_height_in_mm: int):
    while True:
        height, speed = await read_height_and_speed(client)
        current_height_in_mm = await calculate_height_in_mm(height)
        print(current_height_in_mm)
        print(f'Current height is {current_height_in_mm} mm, speed is {speed / 100} mm/s')
        difference_in_mm = desired_height_in_mm - current_height_in_mm

        if abs(difference_in_mm) < 10:
            print('COMMAND -> desk stop moving')
            await stop(client)
            return current_height_in_mm

        if difference_in_mm >= 0:
            print('COMMAND -> desk move up')
            await move_up(client)
        else:
            print('COMMAND -> desk move down')
            await move_down(client)


async def move_desk_to_height(height_in_mm: int):
    desk = await get_desk()
    if desk is None:
        raise "No desk found nearby!"
    else:
        print(f"{desk.name} was found!")

    print(f"Connecting to bluetooth device on MAC address `{desk.address}`")

    async with BleakClient(address_or_ble_device=desk) as client:
        print(f'Connected `{client.is_connected}`')
        device_name_byte_array = await client.read_gatt_char(UUID_DEVICE_NAME)
        connected_device_name = bytes(device_name_byte_array).decode("utf-8")
        print(f'This Python script is connected with the following device `{connected_device_name}`')
        height_reached_in_mm = await move_to_desired_height(client, height_in_mm)

    return height_reached_in_mm


app = fastapi.FastAPI()


@app.get("/sit")
async def sit():
    height = 850
    height_reached = await move_desk_to_height(height)
    return f"Device has reached height of {int(height_reached / 10)} cm"


@app.get("/stand")
async def stand():
    height = 1200
    height_reached = await move_desk_to_height(height)
    return f"Device has reached height of {int(height_reached / 10)} cm"
