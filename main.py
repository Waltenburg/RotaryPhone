from utime import sleep_ms, sleep, ticks_ms
from picodfplayer import DFPlayer
from machine import Pin
import ujson
import uos

#Constants. Change these if DFPlayer is connected to other pins.
UART_INSTANCE=0
TX_PIN = 16
RX_PIN=17
BUSY_PIN=6
inputPin = Pin(10, Pin.IN, Pin.PULL_DOWN)
altInputPin = Pin(22, Pin.IN, Pin.PULL_UP)

#Create player instance
player=DFPlayer(UART_INSTANCE, TX_PIN, RX_PIN, BUSY_PIN)

MAX_NUMBER_LEN = 16

numbers = []

file_path = "numbers.json"

inputNumbers = [] #De tal der er indtastet
currNumCnt = 0 #If > 0, then the rotary is spinning
numberJustEntered = False #Om der efter ny indtastning skal tjekkes om det er den korrekte sekvens

high = False
low = False
wasHigh = False
wasLow = False
lastHigh = 0
lastLow = 0

altPin = True
altWas = True
altLast = 0
newNumberIndex = 0
lastPush = 0
newNumber = []

requireNewMeasurement = True;
lastMeasurement = 0;
phoneLifted = False;
talking = False;

hangUpTime = 300; #Tid input skal være lavt før røret er lagt på
rotaryEndTime = 100; #Tid input skal være lavt før drejeskive er færdig
rotaryImpulseTime = 10; #Tid der bruges til at tælle impulser fra drejeskive

def saveNumbers():
    global newNumberIndex
    json_string = ujson.dumps(numbers)
    with open(file_path, "w") as file:
        file.write(json_string)
    newNumberIndex = 0
    print("Numbers saved! New numbers are:")
    print(numbers)

def measurement():
    global requireNewMeasurement, lastMeasurement
    if(not requireNewMeasurement):
        return lastMeasurement;
    sum = 0;
    for i in range(50):
        if(inputPin.value()):
            sum += 1;
    lastMeasurement = sum;
    requireNewMeasurement = False;
    return sum;
    
#HIGH input betyder at røret er oppe
def inputHigh():
    return measurement() > 48

#Low betyder at røret er lagt på eller impuls fra drejeskive
def inputLow():
    return measurement() < 2

def checkRørLagtPå():
    global phoneLifted, talking, inputNumbers, inputIndex, newNumberIndex, newNumber
    #if(low):
    if(low and ticks_ms() - lastHigh > hangUpTime):
        print("Lagt på")
        phoneLifted = False
        talking = False
        inputNumbers = []
        inputIndex = 0
        newNumberIndex = 0
        newNumber = []
        player.pause()

#Hvis der er impuls fra drejeskive, lægges der 1 til currNumCnt
def checkDrejeskiveImpuls():
    global currNumCnt
    if(high and ticks_ms() - lastLow < rotaryImpulseTime and ticks_ms() - lastHigh > rotaryImpulseTime):
        currNumCnt += 1

#Kontrollerer om og håndterer at drejeskive er færdig
def checkDrejeskiveFærdig():
    global currNumCnt
    global numberJustEntered
    if(high and ticks_ms() - lastLow > rotaryEndTime):
        inputNumbers.append(currNumCnt)
        print("nr indtastet: " + str(inputNumbers))
        currNumCnt = 0;
        numberJustEntered = True;
        
#Kontroller om den korrekte sekvens er indtastet.
def checkDrejeskiveInput():
    global numberJustEntered, talking, inputNumbers
    for i in range(len(numbers)):
        if(inputNumbers == numbers[i]):
            sleep(2)
            player.playMP3(i + 1 + 1)
            numberJustEntered = False;
            talking = True;
            inputNumbers = {}
            print("Spiller nr. " + str(i + 1))
            break;

def set_value_at_index(numbers, newNumberIndex, inputNumbers):
    # Check if newNumberIndex is within the valid range
    if newNumberIndex > len(numbers):
        # Expand the list to accommodate the new index
        numbers.extend([None] * (newNumberIndex - len(numbers)))
    
    # Assign the input value to the appropriate index
    numbers[newNumberIndex - 1] = inputNumbers

try:
    with open(file_path, "r") as file:
        json_data = file.read()
except:
    numbers = [[5, 4, 5, 10, 1, 10, 1, 5]]
# Convert JSON string back to array
numbers = ujson.loads(json_data)
print(numbers)

player.setVolume(20)

while True:  
    high = inputHigh();
    low = inputLow();
    
    altPin = altInputPin.value()
    if(altPin and not altWas and ticks_ms() - altLast > 4000):
        if(newNumberIndex > 0):
            del numbers[newNumberIndex - 1]
            saveNumbers()
    elif(altPin and not altWas and ticks_ms() - altLast > 1000):
        if(len(inputNumbers) > 1 and newNumberIndex > 0):
            set_value_at_index(numbers, newNumberIndex, inputNumbers)
            #numbers[newNumberIndex - 1] = inputNumbers
            saveNumbers()
    elif(altPin and not altWas and ticks_ms() - lastPush > 50): #Activates on falling edge 
        newNumberIndex += 1
        lastPush = ticks_ms()
        print(newNumberIndex)
    
    elif(talking):
        checkRørLagtPå();

    elif(phoneLifted):
        checkRørLagtPå();
        checkDrejeskiveImpuls();

        if(currNumCnt > 0):
            checkDrejeskiveFærdig();

        if(numberJustEntered and newNumberIndex == 0):
            checkDrejeskiveInput();
        
    else: #phoneLifted == false
        if(high): #Telefonen løftes netop nu
            phoneLifted = True;
            player.playMP3(1) # Dial-up tone
    #Flow control
    if(high):
        lastHigh = ticks_ms();
    if(low):
        lastLow = ticks_ms();
    wasHigh = high;
    wasLow = low;
    requireNewMeasurement = True;
    
    if(altPin):
        altLast = ticks_ms()
    altWas = altPin
    