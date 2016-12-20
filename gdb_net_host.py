# sudo python -m pip install python-pytun

import gdb, select, binascii, pytun

num_rx = gdb.parse_and_eval('sizeof g_rxBuffer / sizeof g_rxBuffer[0]')
num_tx = gdb.parse_and_eval('sizeof g_txBuffer / sizeof g_txBuffer[0]')
next_rx = 0
next_tx = 0
saved_mac_addr = None


def poll(tap):
    if poll_link():
        while poll_rx(tap):
            pass
        while poll_tx(tap):
            pass


def poll_link():
    status = gdb.parse_and_eval('g_phyStatus')
    if (status & 5) != 5:
        print 'phy status = %08x, still waiting for full-duplex link...' % status
        return False
    return True


def poll_rx(tap):
    global next_rx

    status = gdb.parse_and_eval('g_rxBuffer[%d].desc.ui32CtrlStatus' % next_rx)
    if status & (1 << 31):
        # Hardware still owns this buffer; try later
        return

    if status & (1 << 11):
        print "RX Overflow error"
    elif status & (1 << 12):
        print "RX Length error"
    elif status & (1 << 3):
        print "RX Receive error"
    elif status & (1 << 1):
        print "RX CRC error"
    elif (status & (1 << 8)) and (status & (1 << 9)):
        # Complete frame (first and last parts)
        length = (status >> 16) & 0x3FFF
        ptr = gdb.parse_and_eval('g_rxBuffer[%d].frame' % next_rx)
        frame = gdb.selected_inferior().read_memory(ptr, length)
        print 'RX %r' % binascii.b2a_hex(frame)
        tap.write(frame)
    else:
        print "RX unhandled status %08x" % status

    # Return the buffer to hardware, advance to the next one
    gdb.parse_and_eval('g_rxBuffer[%d].desc.ui32CtrlStatus = DES0_RX_CTRL_OWN' % next_rx)
    next_rx = (next_rx + 1) % num_rx

    # Rx Poll Demand (wake up MAC if it's suspended)
    gdb.parse_and_eval('*(volatile uint32_t*) 0x400ECC08 = -1')
    return True


def poll_tx(tap):
    global next_tx
    global saved_mac_addr

    if not select.select([tap.fileno()], [], [], 0)[0]:
        return
    frame = tap.read(4096)
    print 'TX %r' % binascii.b2a_hex(frame)

    while gdb.parse_and_eval('g_rxBuffer[%d].desc.ui32CtrlStatus' % next_tx) & (1<< 31):
        print "TX waiting for buffer"
        gdb.execute('cont')

    # Lazily set up MAC address here; the hardware insists on replacing it in outgoing frames
    source_mac = frame[6:12]
    if saved_mac_addr != source_mac:
        saved_mac_addr = source_mac
        gdb.parse_and_eval('*(volatile uint32_t*) 0x400EC040 = 0x%x' % (ord(source_mac[4]) | (ord(source_mac[5]) << 8)))
        gdb.parse_and_eval('*(volatile uint32_t*) 0x400EC048 = 0x%x' % (ord(source_mac[0]) | (ord(source_mac[1]) << 8) |
                                                                       (ord(source_mac[2]) << 16) | (ord(source_mac[3]) << 24)))
    ptr = gdb.parse_and_eval('g_rxBuffer[%d].frame' % next_tx)
    gdb.selected_inferior().write_memory(ptr, frame)
    gdb.parse_and_eval('g_txBuffer[%d].desc.ui32Count = %d' % (next_tx, len(frame)))
    gdb.parse_and_eval('g_txBuffer[%d].desc.ui32CtrlStatus = DES0_TX_CTRL_LAST_SEG | DES0_TX_CTRL_FIRST_SEG | DES0_TX_CTRL_CHAINED | DES0_TX_CTRL_OWN' % next_tx)
    next_tx = (next_tx + 1) % num_tx

    # Tx Poll Demand (wake up MAC if it's suspended)
    gdb.parse_and_eval('*(volatile uint32_t*) 0x400ECC04 = -1')
    return True


def main():
    with OpenOcd() as ocd:
        ocd.send("halt")
        eth = Ethernet(ocd)
        while True:
            proxy(eth, tap)

def main():
    # TAP interface with no packet info header; raw Ethernet frames
    tap = pytun.TunTapDevice(flags=pytun.IFF_TAP | pytun.IFF_NO_PI)
    gdb.execute('set height 0')
    try:
        gdb.execute('run')
        while True:
            #transmit("U" * 1536)
            for i in range(10):
                poll(tap)
                gdb.execute('cont')
    except KeyboardInterrupt:
        gdb.execute('set confirm off')
        gdb.execute('quit')

if __name__ == '__main__':
    main()
