# PIO Interrupt Module - Final Production Version with destroy()
# Author: G Tucker
# Date: 31st Jan 2026

from machine import Pin
from rp2 import StateMachine, asm_pio


# -------------------------------------------------
# STATIC PIO PROGRAM (UNCHANGED)
# -------------------------------------------------

@asm_pio()
def edge_xy():
    pull()                 # 1st pull: one-shot flag
    mov(y, osr)

    pull()                 # 2nd pull: debounce / hold cycles
    mov(isr, osr)

    pull()                 # 3rd pull: edge direction
                           # 0 = falling, 1 = rising

    label("start")
    mov(x, osr)
    jmp(not_x, 'falling')

    # --- Rising edge wait ---
    wait(1, pin, 0)
    jmp('delay')

    # --- Falling edge wait ---
    label('falling')
    wait(0, pin, 0)

    # --- Debounce delay ---
    label('delay')
    mov(x, isr)
    label('hold')
    jmp(x_dec, 'hold')

    # --- Validation ---
    mov(x, osr)
    jmp(not_x, 'fallingcheck')

    # Rising validation
    jmp(pin, 'irq')
    jmp('start')

    # Falling validation
    label('fallingcheck')
    jmp(pin, 'start')

    # --- IRQ ---
    label('irq')
    irq(rel(0))

    # --- Release wait ---
    jmp(not_x, 'falling_reverse')
    wait(0, pin, 0)
    label('falling_reverse')
    wait(1, pin, 0)

    # --- One-shot control ---
    jmp(not_y, 'start')
    jmp('halt')

    label('halt')
    jmp('halt')


# -------------------------------------------------
# PIO_INTERRUPT Class (API UNCHANGED)
# -------------------------------------------------

class PIO_INTERRUPT:
    def __init__(self, sm_number:int, interrupt_pin:int, direction:str="rising",
                 hold_ms:int=20, oneshot:bool=False, pull:bool=False, freq:int=4000):
        """
        sm_number      : StateMachine number
        interrupt_pin  : GPIO number
        direction      : 'rising' or 'falling'
        hold_ms        : Hold/debounce period in milliseconds
        oneshot        : True for one-shot mode
        pull           : True to enable pull_up/down automatically
        freq           : StateMachine frequency in Hz
        """

        self.sm_number = sm_number
        self.interrupt_pin = interrupt_pin
        self.direction = direction
        self.oneshot = oneshot
        self.pull = pull
        self.freq = freq

        # Convert hold_ms → PIO cycles
        self.hold_cycles = max(1, int(hold_ms * freq / 1000))

        # Configure GPIO
        if pull:
            if direction == "rising":
                self.pin = Pin(interrupt_pin, Pin.IN, Pin.PULL_DOWN)
            else:
                self.pin = Pin(interrupt_pin, Pin.IN, Pin.PULL_UP)
        else:
            self.pin = Pin(interrupt_pin, Pin.IN)

        # Callback + polling flag
        self.callback = None
        self._triggered = False

        # Build the state machine
        self._build_sm()


    # -------------------------------------------------
    # Build / rebuild SM
    # -------------------------------------------------

    def _build_sm(self):
        self.sm = StateMachine(
            self.sm_number,
            edge_xy,
            freq=self.freq,
            in_base=self.pin,
            jmp_pin=self.pin
        )

        # FIFO configuration (ORDER IS CRITICAL)
        self.sm.put(1 if self.oneshot else 0)                 # pull #1 → Y
        self.sm.put(self.hold_cycles)                         # pull #2 → ISR
        self.sm.put(1 if self.direction == "rising" else 0)  # pull #3 → OSR

        self.sm.irq(self._irq_handler)
        self.sm.active(1)


    # -------------------------------------------------
    # IRQ handler
    # -------------------------------------------------

    def _irq_handler(self, sm):
        self._triggered = True
        if self.callback:
            self.callback()


    # -------------------------------------------------
    # Register callback
    # -------------------------------------------------

    def register_callback(self, func):
        self.callback = func


    # -------------------------------------------------
    # Restart one-shot SM
    # -------------------------------------------------

    def restart(self):
        if not self.oneshot:
            return
        self.sm.active(0)
        self._build_sm()


    # -------------------------------------------------
    # Polling interface
    # -------------------------------------------------

    def triggered(self, clear=True):
        val = self._triggered
        if clear:
            self._triggered = False
        return val


    # -------------------------------------------------
    # Destroy / cleanup
    # -------------------------------------------------

    def destroy(self):
        if hasattr(self, 'sm'):
            self.sm.active(0)
            self.sm.irq(None)
            del self.sm
        self.callback = None

