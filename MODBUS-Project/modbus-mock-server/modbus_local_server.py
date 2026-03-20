import asyncio
import contextlib
import os
import random
import signal
import time
from typing import List

from pymodbus.server import StartAsyncTcpServer
from pymodbus.datastore import ModbusDeviceContext, ModbusServerContext
from pymodbus.datastore import ModbusSequentialDataBlock
from pymodbus.pdu.device import ModbusDeviceIdentification


# Configuration
HOST = os.environ.get("MODBUS_HOST", "0.0.0.0")
PORT = int(os.environ.get("MODBUS_PORT", 1502))
UPDATE_INTERVAL = float(os.environ.get("UPDATE_INTERVAL", 1.0))


def clamp_int(value: int, min_v: int = 0, max_v: int = 0xFFFF) -> int:
    return max(min_v, min(max_v, int(value)))


def to_reg(value: float, scale: float = 1.0, min_v: int = 0, max_v: int = 0xFFFF) -> int:
    return clamp_int(round(value * scale), min_v, max_v)


def build_context() -> ModbusServerContext:
    """Create a Modbus context with initial values and zero-based addressing."""
    # 100 values per table to start
    di = ModbusSequentialDataBlock(0, [0] * 100)  # Discrete Inputs
    co = ModbusSequentialDataBlock(0, [0] * 100)  # Coils
    hr = ModbusSequentialDataBlock(0, [0] * 100)  # Holding Registers
    ir = ModbusSequentialDataBlock(0, [0] * 100)  # Input Registers

    # Initial setpoints / states
    # Holding Registers (RW)
    hr_values = [0] * 100
    hr_values[0] = 50   # valve position
    hr_values[1] = 0    # heater power
    hr_values[2] = 0    # fan speed
    hr_values[3] = 0    # conveyor speed
    hr_values[4] = 0    # production rate setpoint
    hr_values[5] = 0    # system mode (0=MANUAL)
    # commands 6..9 default 0
    hr.setValues(0, hr_values)

    # Coils (RW)
    co_values = [0] * 100
    co_values[0] = 0  # pump_enabled
    co_values[1] = 0  # alarm_active (written by simulation)
    co.setValues(0, co_values)

    # Input Registers (RO sensors) — initialize sensible defaults
    ir_values = [0] * 100
    ir_values[0] = to_reg(25.0, 10)    # temperature x10
    ir_values[1] = to_reg(1013.0, 1)   # pressure
    ir_values[2] = to_reg(0.0, 1)      # flow
    ir_values[3] = to_reg(75.0, 10)    # tank level x10
    ir_values[4] = to_reg(0.3, 100)    # vibration x100
    ir_values[5] = to_reg(7.2, 100)    # pH x100
    ir_values[6] = to_reg(45.0, 10)    # humidity x10
    ir_values[7] = to_reg(0.0, 1)      # motor speed
    ir_values[8] = to_reg(0.0, 1)      # total production (wraps)
    ir.setValues(0, ir_values)

    # Discrete Inputs (RO)
    di_values = [0] * 100
    di_values[0] = 0  # emergency stop
    di_values[1] = 0  # running
    di.setValues(0, di_values)

    device = ModbusDeviceContext(di=di, co=co, hr=hr, ir=ir)
    # In single-device mode pymodbus expects the device context directly, not a dict.
    context = ModbusServerContext(devices=device, single=True)
    return context


async def simulation_loop(context: ModbusServerContext) -> None:
    """Background loop to update sensor values and process commands."""
    unit_id = 0x00  # 'single=True' context ignores unit, but 0x00 is conventional
    total_production_acc = 0.0

    while True:
        try:
            # Read controls / setpoints
            # Coils
            pump_enabled = bool(context[unit_id].getValues(1, 0, count=1)[0])

            # Holding registers
            vals_hr: List[int] = context[unit_id].getValues(3, 0, count=10)
            valve_pos = clamp_int(vals_hr[0], 0, 100)
            heater_power = clamp_int(vals_hr[1], 0, 100)
            fan_speed = clamp_int(vals_hr[2], 0, 100)
            conveyor_speed = clamp_int(vals_hr[3], 0, 100)
            prod_rate_sp = clamp_int(vals_hr[4], 0, 1000)
            system_mode = clamp_int(vals_hr[5], 0, 2)  # 0=MANUAL,1=AUTO,2=MAINT
            cmd_start = vals_hr[6] > 0
            cmd_stop = vals_hr[7] > 0
            cmd_e_stop = vals_hr[8] > 0
            cmd_reset = vals_hr[9] > 0

            # Process commands
            if cmd_start:
                system_mode = 1  # AUTO
                pump_enabled = True
                conveyor_speed = max(conveyor_speed, min(prod_rate_sp * 2, 100))
                # clear command
                context[unit_id].setValues(3, 6, [0])
            if cmd_stop:
                system_mode = 0  # MANUAL
                pump_enabled = False
                conveyor_speed = 0
                context[unit_id].setValues(3, 7, [0])
            if cmd_e_stop:
                system_mode = 2  # MAINT
                pump_enabled = False
                conveyor_speed = 0
                # set alarm and e-stop below
                context[unit_id].setValues(3, 8, [0])
            if cmd_reset:
                system_mode = 0  # MANUAL
                # clear alarm and e-stop below
                total_production_acc = 0.0
                context[unit_id].setValues(3, 9, [0])

            # Apply possibly updated controls back to stores
            context[unit_id].setValues(1, 0, [1 if pump_enabled else 0])  # coil 0
            context[unit_id].setValues(3, 3, [conveyor_speed])
            context[unit_id].setValues(3, 5, [system_mode])

            # Discrete Inputs (status)
            di_vals = context[unit_id].getValues(2, 0, count=2)
            emergency_stop = di_vals[0] == 1 or (system_mode == 2)
            running = (system_mode == 1) and not emergency_stop and (prod_rate_sp > 0)

            # Simulate process
            # Temperature influenced by heater power
            base_temp = 25.0 + (heater_power * 0.5)
            temperature = base_temp + random.uniform(-2.0, 2.0)

            # Pressure influenced by pump and valve
            base_pressure = 1013.0
            if pump_enabled:
                base_pressure += 50.0
            base_pressure -= (valve_pos - 50.0) * 0.5
            pressure = base_pressure + random.uniform(-5.0, 5.0)

            # Flow rate influenced by pump and valve
            if pump_enabled:
                base_flow = 150.0 * (valve_pos / 100.0)
            else:
                base_flow = 0.0
            flow_rate = max(0.0, base_flow + random.uniform(-10.0, 10.0))

            # Tank level dynamics
            tank_level_reg = context[unit_id].getValues(4, 3, count=1)[0]
            tank_level = tank_level_reg / 10.0
            level_change = (flow_rate - prod_rate_sp) * 0.01
            tank_level = max(0.0, min(100.0, tank_level + level_change + random.uniform(-0.5, 0.5)))

            # Vibration influenced by motor + conveyor
            base_vibration = (conveyor_speed / 100.0) * 0.2 + (prod_rate_sp / 100.0) * 0.2
            vibration = base_vibration + random.uniform(-0.1, 0.1)

            # pH with slow drift
            ph_level_reg = context[unit_id].getValues(4, 5, count=1)[0]
            ph_level = ph_level_reg / 100.0
            ph_level += random.uniform(-0.05, 0.05)
            ph_level = max(6.0, min(8.0, ph_level))

            # Humidity influenced by temperature
            base_humidity = 45.0 - (temperature - 25.0) * 2.0
            humidity = max(20.0, min(80.0, base_humidity + random.uniform(-3.0, 3.0)))

            # Motor speed influenced by production
            motor_speed = 0.0
            if running:
                motor_speed = 1500.0 + (prod_rate_sp * 10.0) + random.uniform(-50.0, 50.0)

            # Production accumulation
            if running and not emergency_stop:
                total_production_acc += prod_rate_sp / 3600.0

            # Alarms
            alarm_active = (
                temperature > 80.0 or
                pressure > 1200.0 or
                tank_level < 10.0 or
                vibration > 2.0
            )

            if temperature > 100.0 or pressure > 1300.0:
                emergency_stop = True
                running = False
                system_mode = 2  # MAINT
                pump_enabled = False
                conveyor_speed = 0

            # Write updated status back to context
            context[unit_id].setValues(2, 0, [1 if emergency_stop else 0])  # DI0
            context[unit_id].setValues(2, 1, [1 if running else 0])        # DI1
            context[unit_id].setValues(1, 1, [1 if alarm_active else 0])   # CO1 alarm

            # Input registers (sensors)
            context[unit_id].setValues(4, 0, [to_reg(temperature, 10)])
            context[unit_id].setValues(4, 1, [to_reg(pressure, 1)])
            context[unit_id].setValues(4, 2, [to_reg(flow_rate, 1)])
            context[unit_id].setValues(4, 3, [to_reg(tank_level, 10)])
            context[unit_id].setValues(4, 4, [to_reg(vibration, 100)])
            context[unit_id].setValues(4, 5, [to_reg(ph_level, 100)])
            context[unit_id].setValues(4, 6, [to_reg(humidity, 10)])
            context[unit_id].setValues(4, 7, [to_reg(motor_speed, 1)])
            context[unit_id].setValues(4, 8, [to_reg(total_production_acc, 1) % 65536])

            await asyncio.sleep(UPDATE_INTERVAL)
        except asyncio.CancelledError:
            break
        except Exception:
            # Avoid crashing the loop on simulation errors
            await asyncio.sleep(UPDATE_INTERVAL)


async def run_server() -> None:
    context = build_context()

    # Identity (optional)
    identity = ModbusDeviceIdentification()
    identity.VendorName = "Mock ICS"
    identity.ProductCode = "MODBUS-MOCK"
    identity.VendorUrl = "https://example.com"
    identity.ProductName = "Modbus Mock Server"
    identity.ModelName = "ModbusSim v0.1"
    identity.MajorMinorRevision = "0.1"

    # Start the simulation loop alongside the server
    sim_task = asyncio.create_task(simulation_loop(context))
    try:
        await StartAsyncTcpServer(
            context=context,
            identity=identity,
            address=(HOST, PORT),
        )
    finally:
        sim_task.cancel()
        with contextlib.suppress(Exception):  # type: ignore
            await sim_task


def main() -> None:
    print(f"Starting Modbus Mock Server on {HOST}:{PORT} ...")
    try:
        asyncio.run(run_server())
    except KeyboardInterrupt:
        print("\nServer stopped by user.")


if __name__ == "__main__":
    main()
