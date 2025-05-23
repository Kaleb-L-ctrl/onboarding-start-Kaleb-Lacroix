# SPDX-FileCopyrightText: © 2024 Tiny Tapeout
# SPDX-License-Identifier: Apache-2.0

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, Timer, with_timeout, FallingEdge
from cocotb.triggers import ClockCycles
from cocotb.types import Logic
from cocotb.types import LogicArray

async def await_half_sclk(dut):
    """Wait for the SCLK signal to go high or low."""
    start_time = cocotb.utils.get_sim_time(units="ns")
    while True:
        await ClockCycles(dut.clk, 1)
        # Wait for half of the SCLK period (10 us)
        if (start_time + 100*100*0.5) < cocotb.utils.get_sim_time(units="ns"):
            break
    return

def ui_in_logicarray(ncs, bit, sclk):
    """Setup the ui_in value as a LogicArray."""
    return LogicArray(f"00000{ncs}{bit}{sclk}")

async def send_spi_transaction(dut, r_w, address, data):
    """
    Send an SPI transaction with format:
    - 1 bit for Read/Write
    - 7 bits for address
    - 8 bits for data
    
    Parameters:
    - r_w: boolean, True for write, False for read
    - address: int, 7-bit address (0-127)
    - data: LogicArray or int, 8-bit data
    """
    # Convert data to int if it's a LogicArray
    if isinstance(data, LogicArray):
        data_int = int(data)
    else:
        data_int = data
    # Validate inputs
    if address < 0 or address > 127:
        raise ValueError("Address must be 7-bit (0-127)")
    if data_int < 0 or data_int > 255:
        raise ValueError("Data must be 8-bit (0-255)")
    # Combine RW and address into first byte
    first_byte = (int(r_w) << 7) | address
    # Start transaction - pull CS low
    sclk = 0
    ncs = 0
    bit = 0
    # Set initial state with CS low
    dut.ui_in.value = ui_in_logicarray(ncs, bit, sclk)
    await ClockCycles(dut.clk, 1)
    # Send first byte (RW + Address)
    for i in range(8):
        bit = (first_byte >> (7-i)) & 0x1
        # SCLK low, set COPI
        sclk = 0
        dut.ui_in.value = ui_in_logicarray(ncs, bit, sclk)
        await await_half_sclk(dut)
        # SCLK high, keep COPI
        sclk = 1
        dut.ui_in.value = ui_in_logicarray(ncs, bit, sclk)
        await await_half_sclk(dut)
    # Send second byte (Data)
    for i in range(8):
        bit = (data_int >> (7-i)) & 0x1
        # SCLK low, set COPI
        sclk = 0
        dut.ui_in.value = ui_in_logicarray(ncs, bit, sclk)
        await await_half_sclk(dut)
        # SCLK high, keep COPI
        sclk = 1
        dut.ui_in.value = ui_in_logicarray(ncs, bit, sclk)
        await await_half_sclk(dut)
    # End transaction - return CS high
    sclk = 0
    ncs = 1
    bit = 0
    dut.ui_in.value = ui_in_logicarray(ncs, bit, sclk)
    await ClockCycles(dut.clk, 600)
    return ui_in_logicarray(ncs, bit, sclk)

@cocotb.test()
async def test_spi(dut):
    dut._log.info("Start SPI test")

    # Set the clock period to 100 ns (10 MHz)
    clock = Clock(dut.clk, 100, units="ns")
    cocotb.start_soon(clock.start())

    # Reset
    dut._log.info("Reset")
    dut.ena.value = 1
    ncs = 1
    bit = 0
    sclk = 0
    dut.ui_in.value = ui_in_logicarray(ncs, bit, sclk)
    dut.rst_n.value = 0
    await ClockCycles(dut.clk, 5)
    dut.rst_n.value = 1
    await ClockCycles(dut.clk, 5)

    dut._log.info("Test project behavior")
    dut._log.info("Write transaction, address 0x00, data 0xF0")
    ui_in_val = await send_spi_transaction(dut, 1, 0x00, 0xF0)  # Write transaction
    assert dut.uo_out.value == 0xF0, f"Expected 0xF0, got {dut.uo_out.value}"
    await ClockCycles(dut.clk, 1000) 

    dut._log.info("Write transaction, address 0x01, data 0xCC")
    ui_in_val = await send_spi_transaction(dut, 1, 0x01, 0xCC)  # Write transaction
    assert dut.uio_out.value == 0xCC, f"Expected 0xCC, got {dut.uio_out.value}"
    await ClockCycles(dut.clk, 100)

    dut._log.info("Write transaction, address 0x30 (invalid), data 0xAA")
    ui_in_val = await send_spi_transaction(dut, 1, 0x30, 0xAA)
    await ClockCycles(dut.clk, 100)

    dut._log.info("Read transaction (invalid), address 0x00, data 0xBE")
    ui_in_val = await send_spi_transaction(dut, 0, 0x30, 0xBE)
    assert dut.uo_out.value == 0xF0, f"Expected 0xF0, got {dut.uo_out.value}"
    await ClockCycles(dut.clk, 100)
    
    dut._log.info("Read transaction (invalid), address 0x41 (invalid), data 0xEF")
    ui_in_val = await send_spi_transaction(dut, 0, 0x41, 0xEF)
    await ClockCycles(dut.clk, 100)

    dut._log.info("Write transaction, address 0x02, data 0xFF")
    ui_in_val = await send_spi_transaction(dut, 1, 0x02, 0xFF)  # Write transaction
    await ClockCycles(dut.clk, 100)

    dut._log.info("Write transaction, address 0x04, data 0xCF")
    ui_in_val = await send_spi_transaction(dut, 1, 0x04, 0xCF)  # Write transaction
    await ClockCycles(dut.clk, 30000)

    dut._log.info("Write transaction, address 0x04, data 0xFF")
    ui_in_val = await send_spi_transaction(dut, 1, 0x04, 0xFF)  # Write transaction
    await ClockCycles(dut.clk, 30000)

    dut._log.info("Write transaction, address 0x04, data 0x00")
    ui_in_val = await send_spi_transaction(dut, 1, 0x04, 0x00)  # Write transaction
    await ClockCycles(dut.clk, 30000)

    dut._log.info("Write transaction, address 0x04, data 0x01")
    ui_in_val = await send_spi_transaction(dut, 1, 0x04, 0x01)  # Write transaction
    await ClockCycles(dut.clk, 30000)

    dut._log.info("SPI test completed successfully")


def check_range(freq, target_freq, percent_tolerance = 1):      # helper function frequency test Kaleb Lacroix
    tolerance = target_freq * (percent_tolerance/100)

    abs_diff = abs(target_freq - freq)

    return (abs_diff <= tolerance)


async def test_pwm_freq(dut):
    done, low_edge, high_edge = False
    DoNothing = 1
    
    start = cocotb.utils.get_sim_time(units="ns")

    edge_case_time_ns = (1/3000)*10*1000000000#                                         after 10 clock cycles of the expected frequency we call it an edge case
    while(not done):#                                                                   log time until we find a rising edge, when we do, thats the final time
        while (int(dut.uo_out.value) == 0):
            done = true#                                                                beak out of this loop we have founda rising edge
            if ((cocotb.utils.get_sim_time(units="ns") - start) > edge_case_time_ns):
                low_edge = True
                break
        Rise1 = cocotb.utils.get_sim_time(units="ns")
        if (not low_edge) and ((Rise1-start) > edge_case_time_ns):high_edge = True #    signal is stuck high
        if low_edge or high_edge: break
    
    if (not (low_edge or high_edge)):
        while ((int(dut.uo_out.value) == 1)):
            DoNothing += 1
        while(int(dut.uo_out.value) == 0):
            Rise2 = cocotb.utils.get_sim_time(units="ns")
        
        period = Rise2-Rise1
        freq = 1/period
        assert check_range(freq,3000), "frequency not within specified tolerance range"

    dut._log.info("PWM Frequency test completed successfully")



async def find_duty(dut):
    done, low_edge, high_edge = False
    DoNothing = 1
    
    start = cocotb.utils.get_sim_time(units="ns")

    edge_case_time_ns = (1/3000)*10*1000000000#                 after 10 clock cycles of the expected frequency we call it an edge case
    while(not done):#                                           log time until we find a rising edge, when we do, thats the final time
        while (int(dut.uo_out.value) == 0):
            done = true#                                        beak out of this loop we have founda rising edge
            if ((cocotb.utils.get_sim_time(units="ns") - start) > edge_case_time_ns):
                return 0x00 #                                   signal is stuck low
        Rise1 = cocotb.utils.get_sim_time(units="ns")
        if  ((Rise1-start) > edge_case_time_ns):return 0xFF #   signal is stuck high

    
    if (not (low_edge or high_edge)):#                          not an edge case
        while ((int(dut.uo_out.value) == 1)):
            Fall = cocotb.utils.get_sim_time(units="ns")
        while(int(dut.uo_out.value) == 0):
            Rise2 = cocotb.utils.get_sim_time(units="ns")
        
        period = Rise2-Rise1
        duty = Fall-Rise1
        duty = int((duty/period)*256)
        return duty
    
async def test_pwm_duty(dut):
    # Reset
    dut._log.info("Start PWM duty test")

    # Set the clock period to 100 ns (10 MHz)
    clock = Clock(dut.clk, 100, units="ns")
    cocotb.start_soon(clock.start())

    # Reset
    dut._log.info("Reset")
    dut.ena.value = 1
    ncs = 1
    bit = 0
    sclk = 0
    dut.ui_in.value = ui_in_logicarray(ncs, bit, sclk)
    dut.rst_n.value = 0
    await ClockCycles(dut.clk, 5)
    dut.rst_n.value = 1
    await ClockCycles(dut.clk, 5)

    prime_registers(dut)


    test_cases = [                                              # establish the test cases we will use for this test
        (0x00,   "0%"),  
        (0x80,  "50%"),
        (0xFF, "100%")
    ]
  
    for Pulse_Width, percent in test_cases:
        ui_in_val = await send_spi_transaction(dut, 1, 0x04, Pulse_Width)   #   Write transaction
        await ClockCycles(dut.clk, 100)                                     #   give time for SPI to fully update
        dut_cyc = await find_duty(dut)                                      #   check the output, making it 
        assert (abs(dut_cyc - Pulse_Width) <= 1 ) , f"expected duty Cycle = {percent} (0x{Pulse_Width:02X}), got 0x{dut_cyc:02X}" 
        await ClockCycles(dut.clk, 100)                                     #   give time for SPI to fully update

    

    dut._log.info("PWM Duty Cycle test completed successfully")


   

#below are old implementations, not sure why they didnt work and frankly i dont want to invest the time to find out so trying simpler methods 
"""
@cocotb.test()
async def test_pwm_freq(dut):
    #kaleb lacroix code begins:

                                                                # first check edge cases (duty cycle = 0% || 100%):
    try:                    # see if theres a rising edge over the timeframe of 3 clock cycles, if not then clearly we are constant low or high (333333 ns is 1 cycle of 3000Hz)
        await with_timeout(RisingEdge(dut.uo_out[0]), timeout_time=333333*3*1000)#x1000 because timout takes ps not ns
        Edge_case = 0
    except cocotb.result.SimTimeoutError:
        Edge_case = 1


    if not Edge_case:                                           # find the frequency and test
        await RisingEdge(dut.uo_out[0])
        first_rise = get_sim_time(units='ns')
        await RisingEdge(dut.uo_out[0])
        second_rise = get_sim_time(units = "ns")

        period = second_rise - first_rise
        freq = 1/(period)

        assert (check_range(freq, 3000)), "Frequency not within tolerance range of 3000Hz +- 1%"
    
    # Kaleb Lacroix code ends.
    dut._log.info("PWM Frequency test completed successfully")

async def prime_registers(dut):
    registers = [
        0x00,  
        0x01,
        0x02,
        0x03
    ]
    for reg in registers:
        dut._log.info(f"Write transaction, address {reg:02X}, data 0xFF")
        ui_in_val = await send_spi_transaction(dut, 1, reg, 0xFF)  # Write transaction
        assert dut.uo_out.value == 0xF0, f"Expected 0xF0, got {dut.uo_out.value}"
        await ClockCycles(dut.clk, 1000) 

async def dutyCycle(dut):       # helper function PWM duty test Kaleb Lacroix


    try:                        # see if theres a rising edge over the timeframe of 3 clock cycles, if not then clearly we are constant low or high (100 ns is 1 cycle of 1MHz)
        await with_timeout(RisingEdge(dut.uo_out), timeout_time=100*1000*1000)#x1000 because timout takes ps not ns
        Edge_case = 0
        dut._log.info("edge_case 0")
    except cocotb.result.SimTimeoutError:
        Edge_case = 1
        dut._log.info("edge_case 1")
    
    if not Edge_case:
        dut._log.info("not edge case")
        await RisingEdge(dut.uo_out)
        T_rise = get_sim_time(units = "ns")
        await FallingEdge(dut.uo_out)
        T_fall = get_sim_time(units = "ns")
        await RisingEdge(dut.uo_out)
        T_rise_2 = get_sim_time(units = "ns")

        T_period = T_rise_2 - T_rise
        T_pulse = T_fall - T_rise
        DC = (T_pulse/T_period)*256
        dut._log.info("returned returned non edge case calculation" )
        return int(DC)

    elif Edge_case:
        dut._log.info("edge_case if statement entered")
        if (dut.uo_out.value == 1):
            dut._log.info("returned 100 duty cycle from edge case" )
            return (0xFF)           # for 100% duty cycle
        else:
            dut._log.info("returned 0 duty cycle from edge case" )
            return (0x00)           # for 0% duty cycle

@cocotb.test()
async def test_pwm_duty(dut):
    #kaleb lacroix code begins:
    # Reset
    dut._log.info("Start PWM duty test")

    # Set the clock period to 100 ns (10 MHz)
    clock = Clock(dut.clk, 100, units="ns")
    cocotb.start_soon(clock.start())

    # Reset
    dut._log.info("Reset")
    dut.ena.value = 1
    ncs = 1
    bit = 0
    sclk = 0
    dut.ui_in.value = ui_in_logicarray(ncs, bit, sclk)
    dut.rst_n.value = 0
    await ClockCycles(dut.clk, 5)
    dut.rst_n.value = 1
    await ClockCycles(dut.clk, 5)

    prime_registers(dut)


    test_cases = [                                              # establish the test cases we will use for this test
        (0x00,   "0%"),  
        (0x80,  "50%"),
        (0xFF, "100%")
    ]
    #dut._log.info("declared test cases")
    for Pulse_Width, percent in test_cases:
        ui_in_val = await send_spi_transaction(dut, 1, 0x04, Pulse_Width)   # Write transaction
        #dut._log.info("first await SPI transaction")
        await ClockCycles(dut.clk, 100)                                     # give time for SPI to fully update
        #dut._log.info("clock cycles await")
        dut_cyc = await dutyCycle(dut)                            # check the output, making it 
        #dut._log.info("duty_cycle function run")
        assert (abs(dut_cyc - Pulse_Width) <= 1 ) , f"expected duty Cycle = {percent} (0x{Pulse_Width:02X}), got 0x{dut_cyc:02X}" 
        await ClockCycles(dut.clk, 100)                                     # give time for SPI to fully update
        #dut._log.info("done code block")
    
    # Kaleb Lacroix code ends.
    dut._log.info("PWM Duty Cycle test completed successfully")
"""