# PIO Interrupt module
# Author: G Tucker
# Date: 2nd Feb 2026


from machine import Pin
from rp2 import StateMachine
import time
from rp2 import asm_pio

# -------------------------------------------------
# PIO Program Generator
# -------------------------------------------------


def make_edge_pio(rising, oneshot, cycles, debug=False):
    if cycles <= 0:
        raise ValueError("cycles must be > 0")

    if rising:
        wait_edge    = "wait(1, pin, 0)"
        release_edge = "wait(0, pin, 0)"
        final_check  = [
            "jmp(pin, 'irq_label')",
            "jmp('start')",
        ]
    else:
        wait_edge    = "wait(0, pin, 0)"
        release_edge = "wait(1, pin, 0)"
        final_check  = [
            "jmp(pin, 'start')",
            "jmp('irq_label')",
        ]

    after_irq = "jmp('oneshot_halt')" if oneshot else "jmp('pinwait')"

    code_lines = [
        "@asm_pio()",
        "def dynamic_edge():",
        "    pull()",
        "    mov(y, osr)",
        "    label('start')",
        f"    {wait_edge}",
        "    mov(x, y),",
        "    label('hold_loop')",
        "    jmp(x_dec, 'hold_loop')",
    ]

    for line in final_check:
        code_lines.append(f"    {line}")

    code_lines.extend([
        "    label('irq_label')",
        "    irq(rel(0))",
        f"    {after_irq}",
        "    label('oneshot_halt')",
        "    jmp('oneshot_halt')",
        "    label('pinwait')",
        f"    {release_edge}",
        "    jmp('start')",
    ])

    code = "\n".join(code_lines) + "\n"


    print(f"----- Generated PIO program Rising: {rising}, oneshot: {oneshot} -----")
    print(code)
    print("--------------------------------")

    namespace = {}
    exec(code, globals(), namespace)
    return namespace["dynamic_edge"]


# -------------------------------------------------
# PIO_INTERRUPT Class
# -------------------------------------------------
class PIO_INTERRUPT:
    def __init__(self, sm_number:int, interrupt_pin:int, direction:str="rising",
                 hold_ms:int=20, oneshot:bool=False, pull:bool=False, freq:int=4000):
        """
        sm_number      : StateMachine number
        interrupt_pin  : GPIO number
        direction      : 'rising' or 'falling'
        hold_ms        : Hold/debounce period in milliseconds (default 20 ms)
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

        # Convert hold_ms to SM cycles
        self.hold_cycles = max(1, int(hold_ms * freq / 1000))

        # Optional pull-up/down
        if pull:
            if direction == "rising":
                self.pin = Pin(interrupt_pin, Pin.IN, Pin.PULL_DOWN)
            else:
                self.pin = Pin(interrupt_pin, Pin.IN, Pin.PULL_UP)
        else:
            self.pin = Pin(interrupt_pin, Pin.IN)

        # Create PIO program with calculated cycles
        self.sm_program = make_edge_pio(rising=(direction=="rising"),oneshot=oneshot,cycles=self.hold_cycles)

        # Callback placeholder
        self.callback = None
        # Interrupt flag for polling
        self._triggered = False

        # Build the state machine
        self._build_sm()

    # -------------------------------------------------
    # Internal method to build/rebuild the state machine
    # -------------------------------------------------
    def _build_sm(self):
        """Build or rebuild the StateMachine"""
        self.sm = StateMachine(self.sm_number, self.sm_program,
                               freq=self.freq, in_base=self.pin, jmp_pin=self.pin)
        self.sm.put(self.hold_cycles)
        self.sm.irq(self._irq_handler)
        self.sm.active(1)

    # -------------------------------------------------
    # Internal IRQ handler
    # -------------------------------------------------
    def _irq_handler(self, sm):
        # Set internal flag for polling
        self._triggered = True
        # Call callback if registered
        if self.callback:
            self.callback()

    # -------------------------------------------------
    # Register a Python callback for IRQ
    # -------------------------------------------------
    def register_callback(self, func):
        """Register a function to be called when interrupt occurs"""
        self.callback = func

    # -------------------------------------------------
    # Restart one-shot SM
    # -------------------------------------------------
    def restart(self):
        """Restart the state machine after one-shot halting"""
        if not self.oneshot:
            return  # only needed for one-shot
        self.sm.active(0)
        self._build_sm()  # rebuild SM completely

    # -------------------------------------------------
    # Polling method to check if IRQ occurred
    # -------------------------------------------------
    def triggered(self, clear=True):
        """
        Check if an interrupt occurred.
        clear: If True, reset the flag after reading
        """
        val = self._triggered
        if clear:
            self._triggered = False
        return val

    # -------------------------------------------------
    # Destroy / cleanup the state machine
    # -------------------------------------------------
    def destroy(self):
        """
        Completely stop and clean up the state machine.
        Should be called on program exit or exceptions to free resources.
        """
        if hasattr(self, 'sm'):
            self.sm.active(0)    # Stop the SM
            self.sm.irq(None)    # Remove IRQ callback
            del self.sm          # Delete SM object
        self.callback = None     # Remove callback reference

