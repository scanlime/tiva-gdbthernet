# Start OpenOCD and GDB for debug purposes only

OPENOCD=openocd
OPENOCD_CONFIG=firmware/openocd.cfg
DBG=arm-none-eabi-gdb
ELFFILE=firmware/gcc/gdbthernet.axf
OCD_PIDFILE=$(mktemp -t "openocd_pid.XXXXXXXXXX")

trap "cleanup ${OCD_PIDFILE}" EXIT
trap '' INT
cleanup() {
    OCD_PID="$(cat $OCD_PIDFILE)"
    sudo kill ${OCD_PID}
    sudo rm -f "$OCD_PIDFILE"
    exit 0
}

# OpenOCD needs root for direct GPIO access
sudo setsid sh -c "${OPENOCD} -f '${OPENOCD_CONFIG}' \
        -c 'init; reset halt' \
        & echo \$! > $OCD_PIDFILE" &

export PYTHONPATH=`pwd`:$PYTHONPATH
${DBG} -ex "tar ext :3333" \
    -ex "python from gdb_net_host import *" \
    ${ELFFILE}
