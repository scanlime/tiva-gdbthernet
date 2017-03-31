#!/bin/bash

while true; do
	sudo killall -9 arm-none-eabi-gdb openocd
	sleep 1
	sudo killall -9 arm-none-eabi-gdb openocd
	sleep 1
	./proxy.sh &
	sleep 5
	while ping -c 8 -i 2 192.168.0.1; do true; done
done


