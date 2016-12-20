PART=TM4C1294NCPDT
DEBUG=1

ROOT=../tiva-c

include ${ROOT}/makedefs

# Debug info that includes preprocessor defs
CFLAGS+=-g3

VPATH=${ROOT}/boards/ek-tm4c1294xl/drivers
VPATH+=${ROOT}/utils

IPATH=.
IPATH+=${ROOT}/boards/ek-tm4c1294xl
IPATH+=${ROOT}
IPATH+=${ROOT}/third_party

all: ${COMPILER}
all: ${COMPILER}/gdbthernet.axf

clean:
	@rm -rf ${COMPILER} ${wildcard *~}

flash: all
	sudo openocd -f openocd.cfg -c 'program ${COMPILER}/gdbthernet.axf verify reset exit'

${COMPILER}:
	@mkdir -p ${COMPILER}

${COMPILER}/gdbthernet.axf: ${COMPILER}/gdbthernet.o
${COMPILER}/gdbthernet.axf: ${COMPILER}/pinout.o
${COMPILER}/gdbthernet.axf: ${COMPILER}/startup_${COMPILER}.o
${COMPILER}/gdbthernet.axf: ${ROOT}/driverlib/${COMPILER}/libdriver.a
${COMPILER}/gdbthernet.axf: tm4c1294xl.ld
SCATTERgcc_gdbthernet=tm4c1294xl.ld
ENTRY_gdbthernet=ResetISR
CFLAGSgcc=-DTARGET_IS_TM4C129_RA0

ifneq (${MAKECMDGOALS},clean)
-include ${wildcard ${COMPILER}/*.d} __dummy__
endif

