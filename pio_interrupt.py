# PIO Interrupt module
# Author: G Tucker
# Date: 15th Feb 2025
from machine import Pin, Timer
from rp2 import PIO, StateMachine, asm_pio
import time


@asm_pio()
def edge_detector_rising():
    wait(1, pin, 0)  # Wait for a rising edge on pin 0
    irq(rel(0))      # Trigger interrupt
    mov(x, x)        # Optional: dummy instruction to slow the loop
    wait(0, pin, 0)  # Wait for pin to go low
    nop() [5]

@asm_pio()
def edge_detector_falling():
    wait(0, pin, 0)  # Wait for a falling edge on pin 0
    irq(rel(0))      # Trigger interrupt
    mov(x, x)        # Optional: dummy instruction to slow the loop
    wait(1, pin, 0)  # Wait for pin to go high
    nop() [5]
    
    
class PIO_INTERRUPT():
    def __init__(self, state_machine, interrupt_pin, direction)
    if direction == "rising":
        self.interrupt_sm = StateMachine(sm_number, edge_detector_rising, freq=4000, in_base=Pin(interrupt_pin))
        self.interrupt_pin = Pin(interruptpin, Pin.IN, Pin.PULL_DOWN)
    
    if direction == "falling":
        self.interrupt_sm = StateMachine(sm_number, edge_detector_falling, freq=4000, in_base=Pin(interrupt_pin))
        self.interrupt_pin = Pin(interrupt_pin, Pin.IN, Pin.PULL_UP)
        
    self.interrupt_sm_handler.irq(self.interrupt_handler)
    self.interrupt_sm(1)
    
    
    def interrupt_handler(self):
        print('Interrupt detected')
        self.interrupt_sm(0) # Disable the statemachine
        # Do "something" here.
        # At the end of the "something", you must enable the Statemachine again with:
        # self.interrupt_sm(1)


if __name__ == "__main__":
    try:
        
        interupt_routine = STEPPER_CONTROLLER(state_machine=0,interrupt_pin = 0, direction = "rising")
                                    
                                    
    except KeyboardInterrupt:
        print('Keyboard interrupt')
