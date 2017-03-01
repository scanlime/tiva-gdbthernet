# sudo python -m pip install python-pytun

import gdb, select, binascii, pytun, struct, os
import RPi.GPIO as GPIO

VERBOSE = True
TRIGGER = False
TRIGGER_PIN = 21
TRIGGER_HIGH = '(string to match in packet for trigger HIGH state)'
TRIGGER_LOW = '(string to match in packet for trigger LOW state)'

GPIO.setmode(GPIO.BCM)
GPIO.setup(TRIGGER_PIN, GPIO.OUT)

# Parse and eval infrequently, since gdb seems to leak memory sometimes
inf = gdb.selected_inferior()
num_rx = int(gdb.parse_and_eval('sizeof g_rxBuffer / sizeof g_rxBuffer[0]'))
num_tx = int(gdb.parse_and_eval('sizeof g_txBuffer / sizeof g_txBuffer[0]'))
g_phy_bmcr = int(gdb.parse_and_eval('(int)&g_phy.bmcr'))
g_phy_bmsr = int(gdb.parse_and_eval('(int)&g_phy.bmsr'))
g_phy_cfg1 = int(gdb.parse_and_eval('(int)&g_phy.cfg1'))
g_phy_sts = int(gdb.parse_and_eval('(int)&g_phy.sts'))
rx_status = [int(gdb.parse_and_eval('(int)&g_rxBuffer[%d].desc.ui32CtrlStatus' % i)) for i in range(num_rx)]
rx_frame = [int(gdb.parse_and_eval('(int)g_rxBuffer[%d].frame' % i)) for i in range(num_rx)]
tx_status = [int(gdb.parse_and_eval('(int)&g_txBuffer[%d].desc.ui32CtrlStatus' % i)) for i in range(num_tx)]
tx_count = [int(gdb.parse_and_eval('(int)&g_txBuffer[%d].desc.ui32Count' % i)) for i in range(num_tx)]
tx_frame = [int(gdb.parse_and_eval('(int)g_txBuffer[%d].frame' % i)) for i in range(num_tx)]

next_rx = 0
next_tx = 0
tx_buffer_stuck_count = 0
idle_state = False

def poll(tap):
    global idle_state

    if poll_link():
        t = poll_tx(tap)
        r = poll_rx(tap)
        if t or r:
            idle_state = False
        elif not idle_state:
            print('idle now')
            idle_state = True


def update_phy_status():
    gdb.execute('cont')
    if VERBOSE:
        print('phy status, bmcr=%08x bmsr=%08x cfg1=%08x sts=%08x' % (
            struct.unpack('<I', inf.read_memory(g_phy_bmcr, 4))[0],
            struct.unpack('<I', inf.read_memory(g_phy_bmsr, 4))[0],
            struct.unpack('<I', inf.read_memory(g_phy_cfg1, 4))[0],
            struct.unpack('<I', inf.read_memory(g_phy_sts, 4))[0]))

def poll_link():
    bmsr = struct.unpack('<I', inf.read_memory(g_phy_bmsr, 4))[0]
    if (bmsr & 4) == 0:
        print('--- Link is down ---')
        update_phy_status()
        return False
    return True


def rx_poll_demand():
    # Rx Poll Demand (wake up MAC if it's suspended)
    inf.write_memory(0x400ECC08, struct.pack('<I', 0xFFFFFFFF))

def tx_poll_demand():
    # Tx Poll Demand (wake up MAC if it's suspended)
    inf.write_memory(0x400ECC04, struct.pack('<I', 0xFFFFFFFF))


def poll_rx(tap):
    global next_rx

    status = struct.unpack('<I', inf.read_memory(rx_status[next_rx], 4))[0]
    if status & (1 << 31):
        # Hardware still owns this buffer; try later
        return

    if status & (1 << 11):
        print('RX Overflow error')
    elif status & (1 << 12):
        print('RX Length error')
    elif status & (1 << 3):
        print('RX Receive error')
    elif status & (1 << 1):
        print('RX CRC error')
    elif (status & (1 << 8)) and (status & (1 << 9)):
        # Complete frame (first and last parts), strip 4-byte FCS
        length = ((status >> 16) & 0x3FFF) - 4
        frame = inf.read_memory(rx_frame[next_rx], length)
        if VERBOSE:
            print('RX %r' % binascii.b2a_hex(frame))
        tap.write(frame)
    else:
        print('RX unhandled status %08x' % status)

    # Return the buffer to hardware, advance to the next one
    inf.write_memory(rx_status[next_rx], struct.pack('<I', 0x80000000))
    next_rx = (next_rx + 1) % num_rx
    rx_poll_demand()
    return True


def poll_tx(tap):
    global next_tx
    global tx_buffer_stuck_count

    status = struct.unpack('<I', inf.read_memory(tx_status[next_tx], 4))[0]
    if status & (1 << 31):
        print('TX waiting for buffer %d' % next_tx)
        tx_buffer_stuck_count += 1
        if tx_buffer_stuck_count > 5:
            gdb.execute('run')
        update_phy_status()
        tx_poll_demand()
        return

    tx_buffer_stuck_count = 0
    if not select.select([tap.fileno()], [], [], 0)[0]:
        return
    frame = tap.read(4096)

    match_low = TRIGGER and frame.find(TRIGGER_LOW) >= 0
    match_high = TRIGGER and frame.find(TRIGGER_HIGH) >= 0

    if VERBOSE:
        print('TX %r' % binascii.b2a_hex(frame))

    if match_low:
       if VERBOSE:
           print('-' * 60)
       GPIO.output(TRIGGER_PIN, GPIO.LOW)

    inf.write_memory(tx_frame[next_tx], frame)
    inf.write_memory(tx_count[next_tx], struct.pack('<I', len(frame)))
    inf.write_memory(tx_status[next_tx], struct.pack('<I',
        0x80000000 | # DES0_RX_CTRL_OWN
        0x20000000 | # DES0_TX_CTRL_LAST_SEG
        0x10000000 | # DES0_TX_CTRL_FIRST_SEG
        0x00100000)) # DES0_TX_CTRL_CHAINED
    next_tx = (next_tx + 1) % num_tx

    if match_high:
        GPIO.output(TRIGGER_PIN, GPIO.HIGH)
        if VERBOSE:
            print('+' * 60)

    tx_poll_demand()
    return True


def main():
    # TAP interface with no packet info header; raw Ethernet frames
    tap = pytun.TunTapDevice(flags=pytun.IFF_TAP | pytun.IFF_NO_PI)
    gdb.execute('set height 0')
    try:
        gdb.execute('run')
        while True:
            poll(tap)
    except KeyboardInterrupt:
        gdb.execute('set confirm off')
        gdb.execute('quit')


if __name__ == '__main__':
    main()
