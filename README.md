# mididings_appliance
A mididings appliance running on a minimal Debian install on an AMD Thin Client Hardware.

My use case is to use mididings to initiate and decode Line 6 PODxt Patch Dumps and route selected CCs to a Midi Captain foot
controller running Midi Captain MAX firmware. The Midi Captain LEDs follow the PODxt when the Patch is changed.

The applianceDebug.py file is a very rough working version. It's not tidy at all and has debug bits left in.
It might be a useful framework for other mididings applications.

I plan to add detailed steps for setting up the thin client, installing mididings under uv and details of the hardware.

# I had lots of assistance:

The Line 6 PODxt patch dump decoding came from Arteme (https://github.com/arteme/pod-ui/issues/83)

Stefets helped me get mididings working (https://github.com/mididings/mididings/issues/43)

# Thanks to you both.

Google helped me untangle my rubbish Python code :)


I have a GUI using NiceGUI to control mididings scenes and also switch Midi Captain Pages.


<img width="396" height="769" alt="NiceDings" src="https://github.com/user-attachments/assets/0e8f13d7-4cb5-4345-be66-05d4d342454b" />

