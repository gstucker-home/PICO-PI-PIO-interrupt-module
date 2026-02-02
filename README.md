# PIO Interrupt Module for Raspberry Pi Pico RP2040 and RP2350 (MicroPython)


### Overview


PIO_INTERRUPT is a hardware-accurate, debounced, edge-triggered interrupt system built using the RP2040/ RP2350 PIO subsystem instead of standard GPIO interrupts.

Why use PIO for interrupts?

Compared to Pin.irq():

| Feature	| GPIO IRQ	| PIO_INTERRUPT |
|:-------:|:---------:|:-------------:|
|Timing accuracy|	CPU-dependent|	Cycle-accurate|
|Debounce	|Software only |Hardware-level
|CPU load	|Medium	|Very low|
|One-shot mode|	Manual	|Built-in
|Noise |immunity	Weak	|Excellent
Deterministic	|NO	|YES|

This is ideal for:
- Noisy signals
- Long cable runs
- Industrial sensors
- Opto-couplers
- Encoders
- Limit switches
- Robot safety inputs

---

#### Features
- Rising or falling edge detection
- Hardware debounce / hold-off
- One-shot mode
- Polling or callback-based handling
- Fully restartable one-shot SM
- Clean destroy / resource release
- Dynamic PIO code generation

---

#### How It Works (Conceptual)
1. PIO waits for edge (rising or falling)
2. Hold timer runs in PIO (debounce or enforced Hold period)
3. Pin state is re-checked
4. IRQ is raised only if still valid
5. Optional:
   - Halt forever (one-shot)
   - Wait for release and re-arm
   
All timing is done inside PIO, not Python, realeasing CPU resource

---

#### Module Contents
- make_edge_pio()
  - Dynamically generates a PIO program for:
    - Rising / falling edge
    - One-shot or repeating mode
    - Arbitrary debounce time OR enforced hold period
- PIO_INTERRUPT class
  - High-level interface for Python code.
 
---
#### Installation

Copy the module into your project, e.g.:
```bash
pio_interrupt.py
```
Then import it:
```python
from pio_interrupt import PIO_INTERRUPT
```
---
#### Class: PIO_INTERRUPT
Constructor
```python
PIO_INTERRUPT(
    sm_number: int,
    interrupt_pin: int,
    direction: str = "rising",
    hold_ms: int = 20,
    oneshot: bool = False,
    pull: bool = False,
    freq: int = 4000
)
```
##### Parameters
| Parameter       | Required | Type   | Default    | Description                                                                   |
| --------------- | -------- | ------ | ---------- | ----------------------------------------------------------------------------- |
| `sm_number`     | Yes    | `int`  | —          | PIO StateMachine number (0–7). Must be unique per active SM.                  |
| `interrupt_pin` | Yes    | `int`  | —          | GPIO pin number to monitor for edges.                                         |
| `direction`     | No     | `str`  | `"rising"` | Edge type to detect. `"rising"` or `"falling"`.                               |
| `hold_ms`       | No     | `int`  | `20`       | Debounce / hold-off time in milliseconds. Converted internally to PIO cycles. |
| `oneshot`       | No     | `bool` | `False`    | If `True`, the interrupt fires once and the SM halts until restarted.         |
| `pull`          | No     | `bool` | `False`    | Enables internal pull resistor based on direction.                            |
| `freq`          | No     | `int`  | `4000`     | PIO StateMachine clock frequency in Hz. Controls debounce resolution.         |

Default Behaviour Summary

| Feature        | Default Behaviour   |
| -------------- | ------------------- |
| Edge detection | Rising edge         |
| Debounce       | 20 ms               |
| Trigger mode   | Repeating           |
| Pull resistors | Disabled            |
| SM frequency   | 4 kHz               |
| Callback       | None (polling only) |

Notes on Defaults
```hold_ms ``` and ```freq```
The effective debounce resolution is:
```python
resolution ≈ 1 / freq seconds
```
At the default freq = ```4000 Hz```:
- Resolution ≈ 0.25 ms
- ```hold_ms``` = 20 → ~80 PIO cycles

##### Pull Logic

| Direction | Pull Enabled |
| --------- | ------------ |
| Rising    | Pull-down    |
| Falling   | Pull-up      |

Note:
On RP2350 devices, internal pull-downs may be unreliable due to a known silicon erratum (RP2350-E9). For reliable inputs, use external pull resistors (~8 kΩ) if necessary.


---
#### Minimum Creation Example (Defaults Only)

```python
from pio_interrupt import PIO_INTERRUPT

irq = PIO_INTERRUPT(
    sm_number=0,
    interrupt_pin=15
)
```
What This Creates (Explicitly)
Even though not specified, this is exactly what gets configured:
| Setting        | Value               |
| -------------- | ------------------- |
| Edge direction | `"rising"`          |
| Debounce time  | `20 ms`             |
| Trigger mode   | Repeating           |
| Internal pull  | Disabled            |
| PIO frequency  | `4000 Hz`           |
| Callback       | None (polling mode) |


---

#### Basic Example — Polling Mode
```python
from pio_interrupt import PIO_INTERRUPT
import time

rising_int = PIO_INTERRUPT(
    sm_number=0,
    interrupt_pin=15,
    direction="rising",
    hold_ms=20
)

while True:
    if rising_int.triggered():
        print("Interrupt detected!")
    time.sleep_ms(10)
```
- No callbacks
- Safe inside main loop
- Deterministic debounce

---

#### Callback Example — Event Driven
```python
from pio_interrupt import PIO_INTERRUPT
import time

def on_irq():
    print("PIO IRQ fired!")

rising_int = PIO_INTERRUPT(
    sm_number=1,
    interrupt_pin=16,
    direction="falling",
    hold_ms=10
)

rising_int.register_callback(on_irq)

while True:
    time.sleep(1)
```
Note:
Callbacks run in IRQ context — keep them short:
- Set flags
- Increment counters
- Avoid allocations
- Avoid blocking calls

---

#### One-Shot Mode Example

Triggers once, then halts permanently until restarted.

```python
from pio_interrupt import PIO_INTERRUPT
import time

rising_int = PIO_INTERRUPT(
    sm_number=2,
    interrupt_pin=17,
    direction="rising",
    hold_ms=50,
    oneshot=True
)

while True:
    if rising_int.triggered():
        print("One-shot interrupt fired!")
        time.sleep(8)
        # Do somthing else here where the interupt must not be triggered
        print("Restart Statemachine")
        rising_int.restart()
        
```
Internally this:
```python
rising_int.restart()
```
- Stops the SM
- Rebuilds it
- Reloads debounce cycles
- Reactivates cleanly

---

#### Combining Callback + Polling

This is often the safest pattern:
```python
flag = False

def irq_cb():
    global flag
    flag = True

rising_int = PIO_INTERRUPT(
    sm_number=2,
    interrupt_pin=17,
    direction="rising",
    hold_ms=50,
    oneshot=False
)
rising_int.register_callback(irq_cb)

while True:
    if flag:
        flag = False
        print("Handled interrupt in main loop")
```
- IRQ stays minimal
- Main logic stays safe

---

#### Cleanup / Destroy (IMPORTANT)

Always destroy the SM on shutdown or exceptions:
```python

try:
    while True:
        pass
finally:
    rising_int.destroy()
```
What destroy() does
- Stops the StateMachine
- Removes IRQ handler
- Releases PIO resources
- Prevents ghost IRQs

---

StateMachine Resource Notes
- RP2040 has 8 StateMachines total, RP2350 has 12
- Always reuse SM numbers carefully
- destroy() frees the SM slot

---

Debug Mode (PIO Code Printout)
make_edge_pio() as the commented lines:
```python
    # print(f"----- Generated PIO program Rising: {rising}, oneshot: {oneshot} -----")
    # print(code)
    # print("--------------------------------")
```
Uncomment these lines to view the resultant PIO Program that is generated
This is useful for:
- Verifying logic
- Learning PIO
- Timing analysis

---

