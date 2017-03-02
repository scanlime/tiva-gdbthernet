# tiva-gdbthernet

Little ethernet-over-gdb bridge for TI Tiva-C microcontrollers. Runs on a Raspberry Pi 2 or 3, with the Tiva-C Launchpad eval board SWD port attached to the Pi GPIOs.

* Attach the EK-TM4C129XL eval board to your rPI
    * Remove the shorting jumper from JP1 (power select)
    * Remove the 0-ohm resistors R6-R16 to take the onboard JTAG debugger out of the circuit
    * Solder headers to X1 (JTAG) and a ground such as TP15
    * Now you just need four jumper wires:
        * Ground: rPI Pin 6 – TP15 test point
        * +5V: rPI Pin 4 - JP1, any of the three pins on the side closest to U4
        * SWD Clock: rPI Pin 22 (GPIO25) – X1, TCK row, next to R8 
        * SWD Data: rPI Pin 18 (GPIO24) – X1, TMS row, next to R10

* Compile your own OpenOCD, be sure to enable bcm2835gpio
	* [Nice guide here on the Adafruits](https://learn.adafruit.com/programming-microcontrollers-using-openocd-on-raspberry-pi/overview)

* Update submodules
	* `git submodule update --init`

* Compile and load firmware
	* `cd firmware; make flash` 

* Now you can launch the proxy (OpenOCD, GDB, and embedded Python)
	* `./proxy.sh`
	* `ifconfig` and admire your new tap0
