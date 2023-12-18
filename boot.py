import bluetooth
import random
import struct
import time
import utime
from machine import I2C, Pin, SPI
from I2C_LCD import I2cLcd
from ble_advertising import advertising_payload
from mfrc522 import MFRC522

from micropython import const

spi = SPI(2, baudrate=10000000, polarity=0, phase=0)
spi.init()

rdr = MFRC522(spi=spi, gpioRst=4, gpioCs=5)

button_steps = Pin(12, Pin.IN,Pin.PULL_UP)
button_notes = Pin(25, Pin.IN,Pin.PULL_UP)

buzzer = Pin(13,Pin.OUT)

display_notes = False
display_steps = True

temp = 0
lines = 0
line_one = ""
notes_LOW = 0
notes_HIGH = 0
steps_LOW = 0
steps_HIGH = 0
yes_HIGH = 0
yes_LOW = 0
no_HIGH = 0
no_LOW = 0
notes_index = 0
steps_index = 0
steps_activity = 0
curr_activity = 0
notes_pos_diff = -1
steps_pos_diff = -1
no_pos_diff = -1
yes_pos_diff = -1
format_date = ""
format_time = ""
view_time = False
activity_init = False
yes_no = False
default_tag = 1
detects_read = 0

nums_list = [0, 0, 0, 0] ### Coffee, Dishwasher, Oatmeal, and Medication Respectively

days = ["Monday", "Tuesday", "Wednesday", "Thursday",
        "Friday", "Saturday", "Sunday"]

months = ["January", "February", "March", "April", "May", "June",
          "July", "August", "September", "October", "November", "December"]

notes_list = [["Notes:         ","               "]] #[1.1, 1.2], [2.1, 2.2,], ...


### LCD Initialization

i2c = I2C(scl=Pin(14), sda=Pin(27), freq=400000)
devices = i2c.scan()

if len(devices) == 0:
     print("No i2c device !")

else:
     for device in devices:
         print("I2C addr: "+hex(device))
         lcd = I2cLcd(i2c, device, 2, 16)
       
       
### Bluetooth Initialization

_IRQ_CENTRAL_CONNECT = const(1)
_IRQ_CENTRAL_DISCONNECT = const(2)
_IRQ_GATTS_WRITE = const(3)

_FLAG_READ = const(0x0002)
_FLAG_WRITE_NO_RESPONSE = const(0x0004)
_FLAG_WRITE = const(0x0008)
_FLAG_NOTIFY = const(0x0010)

_UART_UUID = bluetooth.UUID("6E400001-B5A3-F393-E0A9-E50E24DCCA9E")
_UART_TX = (
    bluetooth.UUID("6E400003-B5A3-F393-E0A9-E50E24DCCA9E"),
    _FLAG_READ | _FLAG_NOTIFY,
)
_UART_RX = (
    bluetooth.UUID("6E400002-B5A3-F393-E0A9-E50E24DCCA9E"),
    _FLAG_WRITE | _FLAG_WRITE_NO_RESPONSE,
)
_UART_SERVICE = (
    _UART_UUID,
    (_UART_TX, _UART_RX),
)


class BLESimplePeripheral:
    def __init__(self, ble, name="ESP32"):
        self._ble = ble
        self._ble.active(True)
        self._ble.irq(self._irq)
        ((self._handle_tx, self._handle_rx),) = self._ble.gatts_register_services((_UART_SERVICE,))
        self._connections = set()   
        self._write_callback = None
        self._payload = advertising_payload(name=name, services=[_UART_UUID])
        self._advertise()

    def _irq(self, event, data):
        # Track connections so we can send notifications.
        if event == _IRQ_CENTRAL_CONNECT:
            conn_handle, _, _ = data
            print("New connection", conn_handle)
            print("\nThe BLE connection is successful.")
            self._connections.add(conn_handle)
        elif event == _IRQ_CENTRAL_DISCONNECT:
            conn_handle, _, _ = data
            print("Disconnected", conn_handle)
            self._connections.remove(conn_handle)
            # Start advertising again to allow a new connection.
            self._advertise()
        elif event == _IRQ_GATTS_WRITE:
            conn_handle, value_handle = data
            value = self._ble.gatts_read(value_handle)
            if value_handle == self._handle_rx and self._write_callback:
                self._write_callback(value)

    def send(self, data):
        for conn_handle in self._connections:
            self._ble.gatts_notify(conn_handle, self._handle_tx, data)

    def is_connected(self):
        return len(self._connections) > 0

    def _advertise(self, interval_us=500000):
        print("Starting advertising")
        self._ble.gap_advertise(interval_us, adv_data=self._payload)

    def on_write(self, callback):
        self._write_callback = callback
       
### Function to handle RFID/NFC tag reads
def handle_tag_read() -> int:
    global steps_activity
    global detects_read
    
    (stat, tag_type) = rdr.request(rdr.REQIDL)
    if stat == rdr.OK:
        (stat, raw_uid) = rdr.anticoll()
        if stat == rdr.OK:
            card_id = "uid: 0x%02x%02x%02x%02x" % (raw_uid[0], raw_uid[1], raw_uid[2], raw_uid[3])
            if card_id == "uid: 0x8c608033":  # Change UID accordingly
                print("Returning 0")
                detects_read = 1
                return 0  # Perform Coffee-related task
            elif card_id == "uid: 0xac928233":  # Change UID accordingly
                print("Returning 1")
                detects_read = 1
                return 1  # Perform Dishwasher-related task
            elif card_id == "uid: 0x7c607c33":  # Change UID accordingly
                print("Returning 2")
                detects_read = 1
                return 2  # Perform Oatmeal-related task
            elif card_id == "uid: 0x7cbd7b33":  # Change UID accordingly
                print("Returning 3")
                detects_read = 1
                return 3  # Perform Medication-related task
    return steps_activity
       
### Adding Notes Function
def notes_data(data):
    
    global lines
    global line_one
    global notes_list
    global display_notes
    
    print(data)
    print(len(data))
    
    if len(data) <= 15:
        lines += 1
        if lines == 1:
            line_one = data
            lcd.move_to(0, 0)
            lcd.putstr(line_one)
            lcd.putstr(" "*(15-len(line_one)))
            lcd.move_to(0, 1)
            lcd.putstr(" "*15)
        if lines == 2:
            lines = 0
            lcd.move_to(0, 0)
            lcd.putstr(line_one)
            lcd.putstr(" "*(15-len(line_one)))
            lcd.move_to(0, 1)
            lcd.putstr(data)
            lcd.putstr(" "*(15-len(data)))
            
            notes_list.append([line_one, data])
            print("Notes List: ", notes_list)
            
            time.sleep_ms(2000)
            
            print("Sleep done!")
            
            lcd.move_to(0, 0)
            lcd.putstr("Note Added!")
            lcd.putstr(" "*4)
            lcd.move_to(0, 1)
            lcd.putstr(" "*15)
            
            notes_list[0][0] = "Notes:         "
            notes_list[0][1] = "               "
            
            time.sleep_ms(2000)
            display_notes = True
            
    else:
        lcd.move_to(0, 0)
        lcd.putstr("Too Many       ")
        lcd.move_to(0, 1)
        lcd.putstr("Characters     ")

### Existing on_rx Function
def on_rx(rx_data):
    global display_notes
    display_notes = False
    data = rx_data.decode('utf8')
    
    notes_data(data)

### Main Function
def demo():
    
    global display_steps
    global display_notes
    global temp
    global notes_index
    global steps_index
    global notes_LOW
    global notes_HIGH
    global notes_pos_diff
    global steps_pos_diff
    global notes_list
    global steps_LOW
    global steps_HIGH
    global steps_list
    global days
    global months
    global yes_HIGH
    global yes_LOW
    global no_HIGH
    global no_LOW
    global no_pos_diff
    global yes_pos_diff
    global format_date
    global format_time
    global steps_activity
    global curr_activity
    global view_time
    global activity_init
    global yes_no
    global nums_list
    global default_tag
    global detects_read
    
    num=0
    
    while True:
        
        ### Steps List:
                
        steps_list = [
            [### Coffee
                [format_time,format_date],
                ["Making Coffee? ","Yes [1], No [2]"],
                ["Made Coffee " + str(nums_list[0]),"Times Today    "],
                ["1. Put Filter  ","In Coffee Maker"],
                ["2. Get Coffee  ","Grounds        "],
                ["3. Pour 1 Scoop","Of Grounds     "],
                ["4. Pour 500ml  ","Of Water       "],
                ["5. Close And   ","Turn On Machine"],
                ["6. Pour In A   ","Cup And Serve  "],
                ["Coffee Served? ","Yes [1], No [2]"]
            ],
            [### Dishwasher
                [format_time,format_date],
                ["Load Dishwash? ","Yes [1], No [2]"],
                ["1. Load Dishes ","Into Dishwasher"],
                ["2. Put In Soap ","               "],
                ["3. Close And   ","Set To HIGH    "],
                ["4. Press Start!","               "]
            ],
            [### Oatmeal
                [format_time,format_date],
                ["Make Oatmeal?  ","Yes [1], No [2]"],
                ["Made Oatmeal " + str(nums_list[2]),"Times Today    "],
                ["1. Get Oats,   ","Bowl, And Spoon"],
                ["2. Pour 1/2 Cup","Of Oats In Bowl"],
                ["3. Pour 1/2 Cup","Water In Bowl  "],
                ["4. Stir With   ","Spoon          "],
                ["5. Put In The  ","Microwave      "],
                ["6. Set For 90  ","Seconds        "],
                ["7. Pour 1 Tbsp ","Brown Sugar    "],
                ["8. Stir And    ","Serve!         "],
                ["Oatmeal Served?","Yes [1], No [2]"]
            ],
            [### Medication
                [format_time,format_date],
                ["Taking Meds?   ","Yes [1], No [2]"],
                ["1. Get Glass Of","Water          "],
                ["2. Take 2 Meds ","With Water     "],
                ["Meds Taken?    ","Yes [1], No [2]"]
            ]
        ]
        
        ### Num Counter
        print("Testing",num)
        num += 1
        
        
        
        ### Time:
        curr_time = utime.localtime()
        
        am_pm = "AM" if curr_time[3] < 12 else "PM"
        hours = curr_time[3] if curr_time[3] <= 12 else curr_time[3] - 12
        hours = 12 if hours == 0 else hours

        day = days[curr_time[6]]
        month = months[curr_time[1] - 1]

        formatted_date = "{} {}".format(month, curr_time[2])
        if hours < 10:
            formatted_time = "{:01d}:{:02d}:{:02d} {}".format(hours, curr_time[4], curr_time[5], am_pm)
        else:
            formatted_time = "{:02d}:{:02d}:{:02d} {}".format(hours, curr_time[4], curr_time[5], am_pm)

        format_date = "{}".format(formatted_date)
        format_time = "{}".format(formatted_time)
            
        
        
        ### Detect RFID/NFC Tag Reads
        
        if num % 20 == 0 and steps_index == 0 and display_steps:
            steps_activity = handle_tag_read() ### Returns Int
            
            
        ### Steps and Time
        if yes_no == False:
        
            if not button_steps.value() == False:
                steps_LOW = utime.ticks_ms()

            if not button_steps.value():
                steps_HIGH = utime.ticks_ms()


        ### Notes
            if not button_notes.value() == False:
                notes_LOW = utime.ticks_ms()
                         
            if not button_notes.value():
                notes_HIGH = utime.ticks_ms()
            

        steps_time_diff = steps_HIGH - steps_LOW
        notes_time_diff = notes_HIGH - notes_LOW
        
        ### Notes Button Pressed
        if notes_time_diff > 0:
            notes_pos_diff = notes_time_diff
 
        ### Long Press (Notes) | Write Note
        if notes_time_diff < 0 and notes_pos_diff >= 1000:
            display_steps = False
            display_notes = True
            notes_pos_diff = -1
            
            if temp == 0:
                temp = 1
            
                ble = bluetooth.BLE()
                p = BLESimplePeripheral(ble)
                p.on_write(on_rx)
            steps_index = 0
            
            notes_list[0][0] = "Enter a Note!  "
            notes_list[0][1] = "               "
            
                
        
        ### Short Press (Notes) | Go Through Notes
        elif notes_time_diff < 0 and notes_pos_diff < 1000 and notes_pos_diff > 0:
            print("Short press! (Notes)")
            notes_pos_diff = -1
            steps_index = 0
            
            if display_notes:
                if len(notes_list) == 1:
                    lcd.move_to(0, 0)
                    lcd.putstr("Must Enter Note")
                    lcd.move_to(0, 1)
                    lcd.putstr("(Hold Button)")
                    lcd.putstr(" "*2)
                    time.sleep(2)
                
                if notes_index + 1 == len(notes_list):
                    notes_index = 0
                else:
                    notes_index += 1
            else:
                display_steps = False
                display_notes = True
            
            time.sleep_ms(20)
                    
                    
        ### Detect Switch in NFC Tags:
                
        if (steps_activity != curr_activity or default_tag == 1) and detects_read == 1:
            curr_activity = steps_activity
            default_tag = 0
            detects_read = 0
            button_press = False
            yes_no = True
            
            
            ### Display Y/N
            
            lcd.move_to(0, 0)
            lcd.putstr(steps_list[steps_activity][1][0])
            lcd.move_to(0, 1)
            lcd.putstr(steps_list[steps_activity][1][1])
            
            
            ### While Loop
            
            buzzer_num = 0
            
            while not button_press:
                
                ### Button Detection
                
                print("Buzzer Num", buzzer_num)
                
                buzzer_num += 1
                
                if buzzer_num % 20 == 0:
                    buzzer.value(1)
                
                if buzzer_num % 20 == 4:
                    buzzer.value(0)
                
                if not button_steps.value() == False:
                    yes_LOW = utime.ticks_ms()

                if not button_steps.value():
                    yes_HIGH = utime.ticks_ms()                   

                if not button_notes.value() == False:
                    no_LOW = utime.ticks_ms()
                             
                if not button_notes.value():
                    no_HIGH = utime.ticks_ms()
                    
                    
                yes_time_diff = yes_HIGH - yes_LOW
                no_time_diff = no_HIGH - no_LOW
                    
                    
                ### Press (No)
                if no_time_diff > 0:
                    no_pos_diff = no_time_diff
                
                ### Press (Yes)
                if yes_time_diff > 0:
                    yes_pos_diff = yes_time_diff
                   
                   
                ### Check Buttons
                if yes_time_diff < 0 and yes_pos_diff >= 0: ### Yes [1]
                    yes_pos_diff = -1
                    print("YES")
                    
                    ### Special Case for Medication
                    if steps_activity == 3 and nums_list[3] >= 1:
                        steps_index = 0
                        lcd.move_to(0, 0)
                        lcd.putstr("Medication     ")
                        lcd.move_to(0, 1)
                        lcd.putstr("Already Taken! ")
                        time.sleep(2)
                        buzzer.value(0)
                    else:
                        steps_index = 2
                    button_press = True
                    buzzer.value(0)
                    
                elif no_time_diff < 0 and no_pos_diff >= 0: ### No [2]
                    no_pos_diff = -1
                    print("NO")
                    
                    lcd.move_to(0, 0)
                    lcd.putstr("Activity       ")
                    lcd.move_to(0, 1)
                    lcd.putstr("Cancelled      ")
                    time.sleep(2)
                    
                    ### Go to time
                    steps_index = 0
                    button_press = True
                    buzzer.value(0)
                time.sleep_ms(50)
                    
            
        
        ### Display Steps
                    
        ### Steps Button Pressed
        if steps_time_diff > 0:
            steps_pos_diff = steps_time_diff
        
        ### Long Press (Steps) | Reset Steps (To Time)
        if (steps_time_diff < 0 and steps_pos_diff >= 1000):# or view_time:
            display_steps = True
            display_notes = False
            
            print("Long Press (Steps)")
            steps_pos_diff = -1
            steps_index = 0
                
        
        ### Short Press (Steps) | Go Through Steps
        elif (steps_time_diff < 0 and steps_pos_diff < 1000 and steps_pos_diff > 0):# or activity_init:
            
            steps_pos_diff = -1
            print("Short press! (Steps)")
            
            if display_steps:
                if steps_index + 1 == len(steps_list[curr_activity]):
                    steps_index = 0
                else:
                    steps_index += 1
            else:
                display_steps = True
                display_notes = False
            time.sleep_ms(20)
                
                
        ### Display Steps
                
        if display_steps:
            yes_no = False
            
            if steps_index == 1:
                curr_activity = -1
            else:
                first_line = steps_list[curr_activity][steps_index][0]
                second_line = steps_list[curr_activity][steps_index][1]
                lcd.move_to(0, 0)
                lcd.putstr(first_line)
                lcd.putstr(" "*(15-len(first_line)))
                lcd.move_to(0, 1)
                lcd.putstr(second_line)
                lcd.putstr(" "*(15-len(second_line)))
                time.sleep_ms(20)
            
            
            ### Work on:
            
            
            if steps_list[curr_activity][steps_index] == steps_list[curr_activity][-1] and curr_activity != 1:
                curr_activity = steps_activity
                button_press = False
                yes_no = True
                while not button_press:
                
                    ### Button Detection
                    
                    if not button_steps.value() == False:
                        yes_LOW = utime.ticks_ms()

                    if not button_steps.value():
                        yes_HIGH = utime.ticks_ms()                   

                    if not button_notes.value() == False:
                        no_LOW = utime.ticks_ms()
                                 
                    if not button_notes.value():
                        no_HIGH = utime.ticks_ms()
                        
                        
                    yes_time_diff = yes_HIGH - yes_LOW
                    no_time_diff = no_HIGH - no_LOW
                        
                        
                    ### Press (No)
                    if no_time_diff > 0:
                        no_pos_diff = no_time_diff
                    
                    ### Press (Yes)
                    if yes_time_diff > 0:
                        yes_pos_diff = yes_time_diff
                       
                       
                    ### Check Buttons
                    if yes_time_diff < 0 and yes_pos_diff >= 0: ### Yes [1]
                        yes_pos_diff = -1
                        print("YES")
                        nums_list[curr_activity] += 1

                        steps_index = 0
                        button_press = True
                    elif no_time_diff < 0 and no_pos_diff >= 0: ### No [2]
                        no_pos_diff = -1
                        print("NO")
                        steps_index = 0
                        button_press = True
            
        
        ### Display Notes
        
        if display_notes and yes_no == False:
            first_line = notes_list[notes_index][0]
            second_line = notes_list[notes_index][1]
            lcd.move_to(0, 0)
            lcd.putstr(first_line)
            lcd.putstr(" "*(15-len(first_line)))
            lcd.move_to(0, 1)
            lcd.putstr(second_line)
            lcd.putstr(" "*(15-len(second_line)))
            time.sleep_ms(20)
        
        time.sleep_ms(50)

if __name__ == "__main__":
    demo()