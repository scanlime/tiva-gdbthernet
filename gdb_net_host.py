import gdb

num_rx = gdb.parse_and_eval('sizeof g_rxBuffer / sizeof g_rxBuffer[0]')
num_tx = gdb.parse_and_eval('sizeof g_txBuffer / sizeof g_txBuffer[0]')
next_rx = 0
next_tx = 0


def transmit(frame):
	global next_tx
	while 0 != gdb.parse_and_eval('g_txBuffer[%d].desc.ui32CtrlStatus & DES0_TX_CTRL_OWN' % next_tx):
		print "Waiting for TX buffer space..."
		gdb.execute('cont')
	gdb.selected_inferior().write_memory(gdb.parse_and_eval('&g_txBuffer[%d].frame' % next_tx), frame)
	gdb.parse_and_eval('g_txBuffer[%d].desc.ui32Count = %d' % (next_tx, len(frame)))
	gdb.parse_and_eval('g_txBuffer[%d].desc.ui32CtrlStatus = DES0_TX_CTRL_LAST_SEG | DES0_TX_CTRL_FIRST_SEG | DES0_TX_CTRL_CHAINED | DES0_TX_CTRL_OWN' % next_tx)
	next_tx = (next_tx + 1) % num_tx


def poll():
	for i in range(num_rx):
		print 'rx%d %08x' % (i, gdb.parse_and_eval('g_rxBuffer[%d].desc.ui32CtrlStatus' % i))
	for i in range(num_tx):
		print 'tx%d %08x' % (i, gdb.parse_and_eval('g_txBuffer[%d].desc.ui32CtrlStatus' % i))
	print 'rx good+bad packets = %d' % gdb.parse_and_eval('(*((volatile uint32_t *)0x400EC180))')
	print 'mac dma status = %08x' % gdb.parse_and_eval('(*((volatile uint32_t *)0x400ECC14))')


def main():
	gdb.execute('set height 0')
	try:
		gdb.execute('run')
		while True:
			#transmit("U" * 1536)
			for i in range(10):
				poll()
				gdb.execute('cont')
	except KeyboardInterrupt:
		gdb.execute('set confirm off')
		gdb.execute('quit')

if __name__ == '__main__':
	main()
