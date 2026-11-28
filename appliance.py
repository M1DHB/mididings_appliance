import threading
import asyncio
from mididings import *
from mididings.event import CtrlEvent, ProgramEvent, SysExEvent
from mididings import run as mididings_run
import mididings.engine as engine
from nicegui import app, ui, run
import subprocess


# ALSA midi routing
# PODxt via DIN to Pod-UI via rtpmidi
def route_1():
    
    subprocess.run(['aconnect', '-x']) # 1. Disconnect all existing connections
    
    subprocess.run(['aconnect', 'rtpmidid:2', 'H4MIDI-WC:1']) # 2. Connect rtpmidid to PODxt DIN
    
    subprocess.run(['aconnect', 'H4MIDI-WC:1', 'rtpmidid:2']) # 3. Connect PODxt DIN back to rtpmidid


# PODxt and Midi Captain via USB Pod-UI via rtpmidi
def route_2():
    
    subprocess.run(['aconnect', '-x']) # 1. Disconnect all existing connections
            
    subprocess.run(['aconnect', 'rtpmidid:2', 'appliance:0']) # 2. Connect Ui via rtpmidi to mididings
    
    subprocess.run(['aconnect', 'PODxt:0', 'appliance:1']) # 3. Connect PODxt USB to mididings

    subprocess.run(['aconnect', 'Pico:0', 'appliance:2']) # 4. Connect MidiCaptain USB to mididings

    subprocess.run(['aconnect', 'appliance:3', 'rtpmidid:2']) # 5. Connect mididings to UI via rtp
   
    subprocess.run(['aconnect', 'appliance:4', 'PODxt:0'])  # 6. Connect mididings to PODxt USB
    
    subprocess.run(['aconnect', 'appliance:5', 'Pico:0']) # 7. Connect mididings to Midi Captain USB

# PODxt DIN, Midi Captain DIN and Pod-UI via rtpmidi
def route_3():
    
    subprocess.run(['aconnect', '-x'])  # 1. Disconnect all existing connections
    
    subprocess.run(['aconnect', 'rtpmidid:2', 'appliance:0']) # 2. Connect Ui via rtpmidi to mididings

    subprocess.run(['aconnect', 'H4MIDI-WC:1', 'appliance:1']) # 3. Connect Ui PODxt DIN to mididings
            
    subprocess.run(['aconnect', 'H4MIDI-WC:0', 'appliance:2']) # 4. Connect MidiCaptain DIN to mididings
    
    subprocess.run(['aconnect', 'appliance:3', 'rtpmidid:2']) # 5. Connect mididings to UI via rtp
    
    subprocess.run(['aconnect', 'appliance:4', 'H4MIDI-WC:1']) # 6. Connect mididings to PODxt DIN
    
    subprocess.run(['aconnect', 'appliance:5', 'H4MIDI-WC:0']) # 7. Connect mididings to Midi Captain DIN


# MIDI Device Status - Define all the MIDI ports you want to track
#TARGET_PORTS = ["PODxt", "rtpmidi", "Fastlane", "Pico", "H4MIDI-WC"]
TARGET_PORTS = ["rtpmidi", "PODxt",  "Pico", "H4MIDI-WC",]

# State dictionary tracks the status of each individual port
state = {
    "ports_status": {port: False for port in TARGET_PORTS},
    "available_ports": []
}

def get_alsa_midi_ports():
    """Runs aconnect -l and returns the raw output string."""
    try:
        # Executes the native ALSA command safely, returning the terminal text
        return subprocess.check_output(["aconnect", "-l"], text=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        return ""

async def midi_port_watcher():
    """Background loop that periodically checks for multiple MIDI ports via ALSA's aconnect."""
    while True:
        try:
            # Capture the output from the Linux shell on a worker thread
            raw_output = await run.io_bound(get_alsa_midi_ports)
            state["available_ports"] = [raw_output]  # Stores raw logs for debugging if needed
            
            # Check status for every target port independently against the output string
            for target in TARGET_PORTS:
                found = target.lower() in raw_output.lower()
                
                # Only update if the status changed to prevent UI flicker
                if state["ports_status"][target] != found:
                    state["ports_status"][target] = found
                    
        except Exception as e:
            print(f"Error scanning MIDI ports: {e}")
            # Reset all to False on total failure
            for target in TARGET_PORTS:
                state["ports_status"][target] = False
                
        await asyncio.sleep(2)

# Mididings config
config(
    backend='alsa', 
    client_name = 'appliance',
    initial_scene = 3,
    in_ports=['in1-UI', 'in2pod', 'in3mc' ],
    out_ports = [ 'out1ui', 'out2pod', 'out3mc' ]
)

## PODxt Patch extraction & Decoding from https://github.com/arteme/pod-ui/issues/83
# CC numbers to extract from the patch dump and re-send as CC events
CC_LIST = [
    26, # compressor
    25, # stomp
    50, # mod
    28, # delay
    22, # noise gate
    63, # eq
    36, # reverb
    43, # wah
]

# MIDI channel to use for the emitted CC events to
OUTPUT_CHANNEL = 1

# Header bytes common to all PODxt patch dump messages (everything before
# the device id / 160 data bytes). SysExFilter() accepts a partial prefix
# match as long as it doesn't include the trailing F7.
PODXT_DUMP_HEADER = [0xf0, 0x00, 0x01, 0x0c, 0x03, 0x74]

DATA_OFFSET = 7
ADDR_OFFSET = 32

def extract_ccs(ev):
    """
    Given a PODxt patch-dump SysEx MidiEvent, pull out the byte for each
    CC number in CC_LIST and emit it as a regular CtrlEvent.
    """
    data = ev.sysex  # full sysex message, including leading F0 / trailing F7

    events = []
    for cc in CC_LIST:
        byte_index = DATA_OFFSET + cc + ADDR_OFFSET

        if byte_index >= len(data):
            # Message too short / CC out of range for this data block -
            # skip rather than raising, in case of malformed input.
            continue

        value = data[byte_index] & 0x7f  # keep it a valid 7-bit CC value
        #print(f"CC {cc} = {value}")
        
        events.append(CtrlEvent(ev.port, OUTPUT_CHANNEL, cc, value))
    print('extracting CCs')
    return events


# Give Program Change time work before send a "get edit buffer" sysex message 
def send_delayed_sysex(ev, delay=0.1):
    sysex = SysExEvent(2, [0xf0, 0x00, 0x01, 0x0c, 0x03, 0x75, 0xf7])
    threading.Timer(delay, engine.output_event, args=[sysex]).start()


# Mididings Scene Control Button Colours
buttons = {}

def select_scene(scene_num: int):
    engine.switch_scene(scene_num)
    for num, btn in buttons.items():
        btn.props(f'color={"green" if num == scene_num else "grey"}')

# Scene Names
scene_1_text = 'Scene 1: PODxt-DIN, Pod-UI-rtp' # PODxt and UI only
scene_2_text = 'Scene 2: PODxt-USB, Midi Captain-USB, Pod-UI-rtp' # PODxt & MC via usb Note: PODxt echoes CC & PC messages on USB
scene_3_text = 'Scene 3: PODxt-DIN, Midi Captain-DIN, Pod-UI-rtp' # PODxt & MC via DIN
scene_4_text = 'Scene 4: Restart NiceGUI'


# 1. Define mididings Scenes
scenes_config = {
    1: Scene(scene_1_text, [Init(Call(route_1)), # PODxt DIN and UI only
                           ]
            ),
    2: Scene(scene_2_text, [Init(Call(route_2)), # PODxt & MC via usb Note: PODxt echoes CC & PC messages on USB
                            PortFilter(2) >> [
                                Filter(PROGRAM) >> [
                                (Output(1) // Output(3)),              # 1. Pass the Program Change immediately to PODxt & UI & MC
                                Call(send_delayed_sysex, delay=0.1)    # 2. Send SysEx after 100ms (0.1s) # Send Get Edit Buffer to PODxt
                                ],
                                Filter(CTRL) >> (Output(1) // Output(3)), # Connect PODxt CC to MC & UI
                                Filter(SYSEX) >> Output(1), # Connect PODxt SysEx to UI
                                SysExFilter(PODXT_DUMP_HEADER) >> Process(extract_ccs) >> Output(3)
                                ],
                                PortFilter([1, 3]) >> Filter(PROGRAM|CTRL) >> Output(2), # CC & PC from UI & MC Pass immediately to PODxt
                                PortFilter(1) >> Filter(SYSEX) >> Output(2), # Connect UI SYSEX to PODxt
                            ]
            ),
    3: Scene(scene_3_text, [Init(Call(route_3)), # PODxt & MC via DIN
                            PortFilter([1, 2, 3]) >> Filter(PROGRAM) >> [
                                Output(1) // Output(2) // Output(3),        # 1. Pass the Program Change immediately to PODxt & UI & MC
                                Call(send_delayed_sysex, delay=0.1)         # 2. Send SysEx after 100ms (0.1s) # Send Get Edit Buffer to PODxt
                                ],
                            PortFilter(1) >> Filter(SYSEX) >> Output(2), # Connect UI to PODxt
                            PortFilter(2) >> Filter(SYSEX) >> Output(1), # Connect PODxt to UI
                            PortFilter([1, 2, 3]) >> Filter(CTRL) >>  (Output(1) // Output(2) // Output(3)), # Connect CC to MC & PODxt & UI
                            PortFilter(2) >> [
                                SysExFilter(PODXT_DUMP_HEADER) >> Process(extract_ccs) >> Output(3) # Extracted CC to MC
                                ],
                            ]
            ),
    4: Scene(scene_4_text, Pass(), init_patch=System('echo "new" > restart.py &')),
}

def start_mididings():
    print("🚀 Starting mididings backend thread...")
    # This blocks the background thread it runs in safely
    mididings_run(scenes=scenes_config,
                  )

## 2. Register mididings to only start once the server is ready
## NiceGUI guarantees app.on_startup only runs once in the final active process
#app.on_startup(lambda: threading.Thread(target=start_mididings, daemon=True).start())

# Start the mididings thread and NiceGUI port watcher task on startup
@app.on_startup
def startup_sequence():
    # Run mididings in a separate background thread so it doesn't block the UI
    threading.Thread(target=start_mididings, daemon=True).start()
    # Start the async port watcher loop
    asyncio.create_task(midi_port_watcher())

# 3. Build the NiceGUI Interface
@ui.page('/')
def main_page():
    ui.button.default_props('no-caps')
    ui.label('PODxt Mididings Router').classes('text-lg font-semibold mt-2 mb-1')

    with ui.card():
        ui.label('Midi Device Status:').classes('text-lg font-semibold mt-2 mb-1')
    
        # Generate a visual indicator row for each target port dynamically
        for target in TARGET_PORTS:
            with ui.row().classes('items-center gap-2 mb-2'):
                ui.label(f"{target}:").classes('w-24 font-medium')
            
                # Binds to the specific key inside the ports_status nested dictionary
                ui.label().bind_text_from(
                    state["ports_status"], 
                    target, 
                    backward=lambda found: "🟢 Connected" if found else "🔴 Disconnected"
                ).classes('font-semibold')

    with ui.card():
        ui.label('Mididings Scene Control:').classes('text-lg font-semibold mt-2 mb-1')
        with ui.column():
           
            buttons[1] = ui.button(scene_1_text, color=None, on_click=lambda: select_scene(1))
            buttons[2] = ui.button(scene_2_text, color=None, on_click=lambda: select_scene(2))
            buttons[3] = ui.button(scene_3_text, color=None, on_click=lambda: select_scene(3))
            
            ui.button(scene_4_text, on_click=lambda: engine.switch_scene(4), color='red').props('outline')
            
            # Set initial state ?? double trigger issue Both startup and UI initialization call switch_scene():
            select_scene(engine.current_scene())


    colours = ['red', 'orange', 'yellow', 'green', 'blue', 'magenta', 'grey', 'white']

    with ui.card():
        ui.label('Midi Captain Page Control:').classes('text-lg font-semibold mt-2 mb-1')
        with ui.grid(columns=4):
            # CtrlEvent(port, channel, controller_number, value)
            for i, colour in enumerate(colours):
                ui.button(
                    f'Set {i + 1}',
                    on_click=lambda val=i: engine.output_event(CtrlEvent(3, 1, 120, val)),
                    color=colour
                ).props('text-color=black').classes('!text-black')


# 4. Strict process guard for the UI runner
if __name__ in {"__main__", "__mp_main__"}:
    # reload=True is now safe because mididings is handled inside app.on_startup
    ui.run(port=8080)
